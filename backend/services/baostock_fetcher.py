"""
Baostock 股票数据获取模块
支持获取：
  - 股票名称/行业信息（query_stock_basic）
  - 真实 PE(TTM)、PB(MRQ)、PS(TTM)（query_history_k_data_plus 带估値字段）
  - 夏普率（Sharpe Ratio）基于历史价格序列计算
"""
import time
import math
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple

import baostock as bs
import pandas as pd
import numpy as np


# ── 全局登录状态 ────────────────────────────────────────────────────────────────
_logged_in = False


def bs_login() -> bool:
    """登录 baostock，已登录则跳过"""
    global _logged_in
    if _logged_in:
        return True
    for _ in range(3):
        lg = bs.login()
        if lg.error_code == "0":
            _logged_in = True
            print("[OK] baostock login success")
            return True
        time.sleep(2)
    print("[ERR] baostock login failed")
    return False


def bs_logout():
    """退出 baostock"""
    global _logged_in
    bs.logout()
    _logged_in = False
    print("[OK] baostock logout")


# ── 股票基本信息 ─────────────────────────────────────────────────────────────────

def _get_industry_map() -> dict:
    """
    获取所有 A 股行业分类映射（内部辅助函数）
    使用 baostock.query_stock_industry() 获取证券代码到行业名称的映射。

    Returns:
        {"sh.600519": "食品饮料", ...}
    """
    rs = bs.query_stock_industry()
    if rs.error_code != "0":
        return {}

    industry_map = {}
    while rs.next():
        row = rs.get_row_data()
        # fields: updateDate, code, code_name, industry, industryClassification
        if len(row) >= 4:
            bs_code  = row[1]   # sh.600519
            industry = row[3]   # 食品饮料
            industry_map[bs_code] = industry
    return industry_map

def get_stock_basic_list() -> List[Dict]:
    """
    获取 A 股股票列表

    使用 baostock.query_stock_basic() 获取：
      - 股票代码（如 sh.600519 → 600519）
      - 股票名称（code_name）
      - 行业（industry）
      - 交易所（SSE/SZSE）

    Returns:
        [{"code": "600519", "name": "贵州茅台", "sector": "食品饮料", "exchange": "SSE"}, ...]
    """
    if not bs_login():
        return []

    # 先获取行业映射（query_stock_industry 耗时较长，之后需重新登录防 session 过期）
    industry_map = _get_industry_map()

    # 重新登录刷新 session（需先退出再登录）
    bs.logout()
    global _logged_in
    _logged_in = False
    if not bs_login():
        return []

    rs = bs.query_stock_basic()
    if rs.error_code != "0":
        print(f"[ERR] query_stock_basic failed: {rs.error_msg}")
        return []

    stocks = []
    while rs.next():
        row = rs.get_row_data()
        # fields: code, code_name, ipoDate, outDate, type, status, industry, industryClassification
        if len(row) < 6:
            continue
        bs_code   = row[0]   # sh.600519
        code_name = row[1]   # 贵州茅台
        ipo_date  = row[2]
        out_date  = row[3]
        stype     = row[4]   # 1=股票 2=指数 3=其他
        status    = row[5]   # 1=上市 0=退市
        # 行业信息从 industry_map 获取（query_stock_basic 不返回行业字段）

        # 只保留上市状态的普通股票（type=1）
        if stype != "1" or status != "1":
            continue

        try:
            market, code = bs_code.split(".")
        except ValueError:
            continue

        # 排除 B 股（代码以 9 或 2 开头在深市）
        if code.startswith("9") or code.startswith("2"):
            continue

        exchange = "SSE" if market == "sh" else "SZSE"
        sector   = industry_map.get(bs_code, "")

        stocks.append({
            "code":     code,
            "name":     code_name,
            "sector":   sector,
            "exchange": exchange,
            "bs_code":  bs_code,   # 供后续查询使用
        })

    print(f"[OK] baostock got {len(stocks)} A-share stocks")
    return stocks


# ── PE/PB/PS 估值数据 ──────────────────────────────────────────────────────────

def _get_total_shares_wan(bs_code: str) -> Optional[float]:
    """
    从 baostock query_profit_data 获取最近一期总股本（万股）
    query_profit_data fields:
      code, pubDate, statDate, roeAvg, npMargin, gpMargin,
      netProfit, epsTTM, MBRevenue, totalShare, liqaShare
    totalShare 单位: 万股
    """
    if not bs_login():
        return None
    today = date.today()
    # 依次尝试当年 Q4→Q3→Q2→Q1，再尝试去年 Q4
    attempts = [
        (today.year,     4),
        (today.year,     3),
        (today.year,     2),
        (today.year,     1),
        (today.year - 1, 4),
    ]
    for year, quarter in attempts:
        rs = bs.query_profit_data(code=bs_code, year=str(year), quarter=str(quarter))
        if rs.error_code != "0":
            print(f"[SHARES] {bs_code} query_profit_data {year}Q{quarter} error: {rs.error_msg}")
            continue
        while rs.next():
            row = rs.get_row_data()
            try:
                total_share = float(row[9])   # totalShare 列
                if total_share > 0:
                    print(f"[SHARES] {bs_code} totalShare={total_share:.0f}万股 ({year}Q{quarter})")
                    return total_share
            except (ValueError, IndexError):
                pass
    print(f"[SHARES] {bs_code} 未能获取总股本")
    return None

def get_valuation_latest(bs_code: str) -> Dict:
    """
    获取指定股票最新的 PE(TTM)、PB(MRQ)、PS(TTM) 及总市值

    从 query_history_k_data_plus 中取最近 30 个交易日的最后一条有效数据。

    Returns:
        {"pe_ratio": float, "pb_ratio": float, "ps_ratio": float, "market_cap": float}
        若无数据则返回空 dict
    """
    if not bs_login():
        return {}

    end_date   = date.today().strftime("%Y-%m-%d")
    start_date = (date.today() - timedelta(days=60)).strftime("%Y-%m-%d")

    rs = bs.query_history_k_data_plus(
        bs_code,
        "date,close,peTTM,pbMRQ,psTTM",
        start_date=start_date,
        end_date=end_date,
        frequency="d",
        adjustflag="3",   # 不复权，估值字段不受复权影响
    )
    if rs.error_code != "0":
        return {}

    rows = []
    while rs.next():
        rows.append(rs.get_row_data())

    if not rows:
        return {}

    # 从最后往前找第一条完整有效的数据
    for row in reversed(rows):
        try:
            date_str, close, pe_ttm, pb_mrq, ps_ttm = row
            pe   = float(pe_ttm)   if pe_ttm   and pe_ttm   != "" else None
            pb   = float(pb_mrq)   if pb_mrq   and pb_mrq   != "" else None
            ps   = float(ps_ttm)   if ps_ttm   and ps_ttm   != "" else None
            cl   = float(close)    if close    and close    != "" else None
            # pe 不为 None 即可（包括负 PE 情况，如亏损股）
            if pe is not None:
                # 用真实总股本计算市值，避免用成交量估算导致大盘股严重失准
                total_shares_wan = _get_total_shares_wan(bs_code)
                if total_shares_wan and cl:
                    market_cap = round(cl * total_shares_wan / 10000, 2)  # 亿元
                    print(f"[VAL] {bs_code} latest: close={cl} shares={total_shares_wan:.0f}万 mktcap={market_cap}亿 PE={pe}")
                else:
                    market_cap = None
                    print(f"[VAL] {bs_code} latest: close={cl} shares=None → mktcap=None PE={pe}")
                return {
                    "pe_ratio":   round(pe, 2),
                    "pb_ratio":   round(pb, 2) if pb is not None else None,
                    "ps_ratio":   round(ps, 2) if ps is not None else None,
                    "market_cap": market_cap,
                }
        except (ValueError, TypeError):
            continue

    print(f"[VAL] {bs_code} latest: 无有效市盈率数据")
    return {}


def get_valuation_by_year(bs_code: str, year: int) -> Dict:
    """
    获取指定股票某年末的 PE/PB/PS/市值（用于多年筛选）

    取该年最后一个交易日的估值数据。

    Returns:
        {"pe_ratio": ..., "pb_ratio": ..., "ps_ratio": ..., "market_cap": ...}
    """
    if not bs_login():
        return {}

    start_date = f"{year}-12-01"
    end_date   = f"{year}-12-31"

    rs = bs.query_history_k_data_plus(
        bs_code,
        "date,close,peTTM,pbMRQ,psTTM",
        start_date=start_date,
        end_date=end_date,
        frequency="d",
        adjustflag="3",
    )
    if rs.error_code != "0":
        return {}

    rows = []
    while rs.next():
        rows.append(rs.get_row_data())

    if not rows:
        return {}

    for row in reversed(rows):
        try:
            date_str, close, pe_ttm, pb_mrq, ps_ttm = row
            pe   = float(pe_ttm)   if pe_ttm   and pe_ttm   != "" else None
            pb   = float(pb_mrq)   if pb_mrq   and pb_mrq   != "" else None
            ps   = float(ps_ttm)   if ps_ttm   and ps_ttm   != "" else None
            cl   = float(close)    if close    and close    != "" else None
            if pe is not None:
                # 用真实总股本计算市值
                total_shares_wan = _get_total_shares_wan(bs_code)
                if total_shares_wan and cl:
                    market_cap = round(cl * total_shares_wan / 10000, 2)
                    print(f"[VAL] {bs_code} {year}年末: close={cl} shares={total_shares_wan:.0f}万 mktcap={market_cap}亿 PE={pe}")
                else:
                    market_cap = None
                    print(f"[VAL] {bs_code} {year}年末: close={cl} shares=None → mktcap=None PE={pe}")
                return {
                    "pe_ratio":   round(pe, 2),
                    "pb_ratio":   round(pb, 2) if pb is not None else None,
                    "ps_ratio":   round(ps, 2) if ps is not None else None,
                    "market_cap": market_cap,
                }
        except (ValueError, TypeError):
            continue

    print(f"[VAL] {bs_code} {year}年末: 无有效市盈率数据")
    return {}


# ── 夏普率计算 ─────────────────────────────────────────────────────────────────

def calculate_sharpe_ratio(
    bs_code: str,
    risk_free_annual: float = 0.03,
    lookback_days: int = 365,
) -> Optional[float]:
    """
    基于历史日线收益率计算年化夏普率

    Sharpe = (mean_daily_return - rf_daily) / std_daily * sqrt(252)

    Args:
        bs_code:          baostock 格式代码，如 "sh.600519"
        risk_free_annual: 年化无风险利率，默认 3%
        lookback_days:    回溯天数，默认 365 天

    Returns:
        年化夏普率（float），数据不足时返回 None
    """
    if not bs_login():
        return None

    end_date   = date.today().strftime("%Y-%m-%d")
    start_date = (date.today() - timedelta(days=lookback_days + 30)).strftime("%Y-%m-%d")

    rs = bs.query_history_k_data_plus(
        bs_code,
        "date,close",
        start_date=start_date,
        end_date=end_date,
        frequency="d",
        adjustflag="2",  # 后复权，用于收益率计算更准确
    )
    if rs.error_code != "0":
        return None

    closes = []
    while rs.next():
        row = rs.get_row_data()
        try:
            closes.append(float(row[1]))
        except (ValueError, IndexError):
            continue

    if len(closes) < 20:
        return None

    closes_arr = np.array(closes)
    returns    = np.diff(closes_arr) / closes_arr[:-1]   # 日收益率

    rf_daily   = risk_free_annual / 252
    excess     = returns - rf_daily
    mean_exc   = np.mean(excess)
    std_exc    = np.std(excess, ddof=1)

    if std_exc == 0:
        return None

    sharpe = mean_exc / std_exc * math.sqrt(252)
    return round(sharpe, 4)


# ── 批量同步入口 ────────────────────────────────────────────────────────────────

def sync_all_stock_info(
    db_session,
    years: int = 3,
    delay: float = 0.3,
    max_stocks: int = 0,
) -> Dict:
    """
    全量同步股票基本信息 + 估值数据 + 夏普率到 SQLite

    流程：
      1. 从 baostock 获取 A 股股票列表（含名称、行业）
      2. 对每只股票，取当年及前 N 年末的 PE/PB/PS/市值，写入 stock_financials
      3. 计算近1年夏普率，写到最新一条 financial 记录上
      4. 更新 Stock 表的 name/sector/exchange

    Args:
        db_session: SQLAlchemy Session
        years:      历史年份数量，默认 3
        delay:      每只股票请求间隔（秒），避免限速
        max_stocks: 调试用，0 = 处理全部

    Returns:
        {"total": int, "success": int, "failed": int}
    """
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from market_models import Stock, StockFinancial
    from datetime import date as dt_date

    if not bs_login():
        return {"total": 0, "success": 0, "failed": 0}

    stocks_info = get_stock_basic_list()
    if not stocks_info:
        return {"total": 0, "success": 0, "failed": 0}

    if max_stocks > 0:
        stocks_info = stocks_info[:max_stocks]

    current_year = dt_date.today().year
    total   = len(stocks_info)
    success = 0
    failed  = 0

    print(f"\n开始同步 {total} 只股票的基本信息 + 估值数据...")

    for i, info in enumerate(stocks_info, 1):
        code     = info["code"]
        name     = info["name"]
        sector   = info["sector"]
        exchange = info["exchange"]
        bs_code  = info["bs_code"]

        try:
            # ── 更新 Stock 基础信息 ──────────────────────────────────────────
            stock = db_session.query(Stock).filter(Stock.code == code).first()
            if stock is None:
                stock = Stock(code=code, name=name, sector=sector, exchange=exchange)
                db_session.add(stock)
                db_session.flush()   # 获取 stock.id
            else:
                stock.name     = name
                stock.sector   = sector
                stock.exchange = exchange

            # ── 获取各年末估值 ───────────────────────────────────────────────
            year_valuations = []
            for year_offset in range(years):
                target_year = current_year - year_offset
                if year_offset == 0:
                    val = get_valuation_latest(bs_code)
                    report_dt = dt_date(current_year, 12, 31)
                else:
                    val = get_valuation_by_year(bs_code, target_year)
                    report_dt = dt_date(target_year, 12, 31)
                time.sleep(delay)

                if val:
                    if not val.get("market_cap"):
                        # baostock 未能提供市值，回退到成交量估算（精度较低）
                        try:
                            import price_db
                            est = price_db.estimate_financials(code, exchange)
                            val["market_cap"] = est.get("market_cap")
                            print(f"[VAL] {code} {report_dt} 回退到成交量估算市值={val['market_cap']}亿")
                        except Exception as e:
                            print(f"[VAL] {code} {report_dt} 市值估算失败: {e}")
                    year_valuations.append((report_dt, val))

            # ── 计算夏普率（只算一次，基于近1年） ──────────────────────────
            sharpe = calculate_sharpe_ratio(bs_code)
            time.sleep(delay)

            # ── 写入 stock_financials ──────────────────────────────────────
            for idx, (report_dt, val) in enumerate(year_valuations):
                existing = db_session.query(StockFinancial).filter(
                    StockFinancial.stock_id == stock.id,
                    StockFinancial.report_date == report_dt,
                ).first()

                if existing is None:
                    fin = StockFinancial(
                        stock_id    = stock.id,
                        report_date = report_dt,
                        pe_ratio    = val.get("pe_ratio"),
                        pb_ratio    = val.get("pb_ratio"),
                        ps_ratio    = val.get("ps_ratio"),
                        market_cap  = val.get("market_cap"),
                        sharpe_ratio= sharpe if idx == 0 else None,
                        data_source = "baostock",
                    )
                    db_session.add(fin)
                else:
                    existing.pe_ratio    = val.get("pe_ratio")
                    existing.pb_ratio    = val.get("pb_ratio")
                    existing.ps_ratio    = val.get("ps_ratio")
                    existing.market_cap  = val.get("market_cap")
                    if idx == 0:
                        existing.sharpe_ratio = sharpe
                    existing.data_source = "baostock"

            db_session.commit()
            success += 1

            # 每只都打，方便追踪进度和市值写入情况
            latest_val = year_valuations[0][1] if year_valuations else {}
            mktcap_str = f"{latest_val.get('market_cap')}亿" if latest_val.get('market_cap') else "mktcap=None"
            pe_str     = str(latest_val.get('pe_ratio', '-'))
            print(f"  [INFO] [{i}/{total}] {code} {name} | PE={pe_str} {mktcap_str} | sharpe={sharpe}")

        except Exception as e:
            db_session.rollback()
            failed += 1
            print(f"  [ERR] [{i}/{total}] {code} {name} failed: {e}")

    bs_logout()
    print(f"\n[OK] sync done | success:{success} | failed:{failed} | total:{total}")
    return {"total": total, "success": success, "failed": failed}


# ── 单只股票快速更新 ────────────────────────────────────────────────

def fetch_stock_prices_incremental(
    code: str,
    exchange: str,
    start_date: str,
    today_str: str,
) -> Tuple[int, str]:
    """
    增量获取单只股票 [start_date, today_str] 的日线数据并写入 MySQL dbbardata

    Args:
        code:       股票代码，如 "000001"
        exchange:   交易所，"SSE" 或 "SZSE"
        start_date: 拉取起始日期 YYYY-MM-DD
        today_str:  结束日期 YYYY-MM-DD

    Returns:
        (added_count, error_msg)  error_msg 为空表示成功
    """
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import price_db
    from sqlalchemy import text as sa_text

    if not bs_login():
        return 0, "baostock not logged in"

    bs_market = "sh" if exchange == "SSE" else "sz"
    bs_code   = f"{bs_market}.{code}"

    try:
        print(f"[SYNC] {code} ({exchange}) start={start_date} end={today_str}")
        rs = bs.query_history_k_data_plus(
            bs_code,
            "date,open,high,low,close,volume",
            start_date=start_date,
            end_date=today_str,
            frequency="d",
            adjustflag="2",   # 后复权
        )
        if rs.error_code != "0":
            print(f"[SYNC ERR] {code} baostock error: {rs.error_msg}")
            return 0, rs.error_msg

        rows_to_insert = []
        while rs.next():
            row_data = rs.get_row_data()
            try:
                date_str, open_, high_, low_, close_, vol = row_data
                if not date_str or not close_ or close_ == "":
                    continue
                rows_to_insert.append({
                    "symbol":      code,
                    "exchange":    exchange,
                    "interval":    "d",
                    "datetime":    date_str + " 00:00:00",
                    "open_price":  float(open_)  if open_  else 0.0,
                    "high_price":  float(high_)  if high_  else 0.0,
                    "low_price":   float(low_)   if low_   else 0.0,
                    "close_price": float(close_) if close_ else 0.0,
                    "volume":      float(vol)     if vol    else 0.0,
                })
            except (ValueError, TypeError):
                continue

        print(f"[SYNC] {code} baostock returned {len(rows_to_insert)} rows")

        if not rows_to_insert:
            return 0, ""

        engine = price_db.get_engine()
        with engine.connect() as conn:
            result = conn.execute(sa_text("""
                INSERT IGNORE INTO dbbardata
                    (symbol, exchange, `interval`, datetime,
                     open_price, high_price, low_price, close_price, volume,
                     turnover, open_interest)
                VALUES
                    (:symbol, :exchange, :interval, :datetime,
                     :open_price, :high_price, :low_price, :close_price, :volume,
                     0, 0)
            """), rows_to_insert)
            conn.commit()
            inserted = result.rowcount
        print(f"[SYNC] {code} inserted={inserted} (prepared={len(rows_to_insert)})")
        return inserted, ""

    except Exception as e:
        print(f"[SYNC ERR] {code} exception: {e}")
        return 0, str(e)


# ── 单只股票快速更新 ────────────────────────────────────────────────────────────

def refresh_single_stock(db_session, code: str) -> bool:
    """
    刷新单只股票的估值数据（快速接口，给前端按需调用）

    Args:
        db_session: SQLAlchemy Session
        code:       股票代码，如 "600519"

    Returns:
        成功返回 True
    """
    from market_models import Stock, StockFinancial
    from datetime import date as dt_date

    if not bs_login():
        return False

    stock = db_session.query(Stock).filter(Stock.code == code).first()
    if stock is None:
        return False

    exchange = stock.exchange or "SZSE"
    market   = "sh" if exchange == "SSE" else "sz"
    bs_code  = f"{market}.{code}"

    try:
        val    = get_valuation_latest(bs_code)
        sharpe = calculate_sharpe_ratio(bs_code)

        if not val:
            return False

        # 市值补充
        if not val.get("market_cap"):
            try:
                import price_db
                est = price_db.estimate_financials(code, exchange)
                val["market_cap"] = est.get("market_cap")
            except Exception:
                pass

        report_dt = dt_date.today().replace(month=12, day=31)
        existing  = db_session.query(StockFinancial).filter(
            StockFinancial.stock_id   == stock.id,
            StockFinancial.report_date == report_dt,
        ).first()

        if existing is None:
            db_session.add(StockFinancial(
                stock_id     = stock.id,
                report_date  = report_dt,
                pe_ratio     = val.get("pe_ratio"),
                pb_ratio     = val.get("pb_ratio"),
                ps_ratio     = val.get("ps_ratio"),
                market_cap   = val.get("market_cap"),
                sharpe_ratio = sharpe,
                data_source  = "baostock",
            ))
        else:
            existing.pe_ratio    = val.get("pe_ratio")
            existing.pb_ratio    = val.get("pb_ratio")
            existing.ps_ratio    = val.get("ps_ratio")
            existing.market_cap  = val.get("market_cap")
            existing.sharpe_ratio = sharpe
            existing.data_source = "baostock"

        db_session.commit()
        return True

    except Exception as e:
        db_session.rollback()
        print(f"[ERR] refresh_single_stock {code} failed: {e}")
        return False


# ── 测试入口 ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("测试 baostock 数据获取")
    print("=" * 60)

    if not bs_login():
        exit(1)

    # 1. 股票列表
    stocks = get_stock_basic_list()
    print(f"\n获取到 {len(stocks)} 只股票")
    print("前5条:", stocks[:5])

    if stocks:
        test   = stocks[0]
        bs_code = test["bs_code"]
        print(f"\n测试 {test['code']} {test['name']} ({bs_code})")

        # 2. 最新估值
        val = get_valuation_latest(bs_code)
        print(f"最新估值: {val}")

        # 3. 夏普率
        sharpe = calculate_sharpe_ratio(bs_code)
        print(f"近1年夏普率: {sharpe}")

    bs_logout()
