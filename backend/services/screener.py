"""
股票筛选服务
根据市盈率连续三年小于 30 且市值小于 60 亿进行筛选
"""
from typing import List
from sqlalchemy.orm import Session
from datetime import date

from market_models import Stock, StockFinancial
from schemas import ScreenerCriteria, ScreenerResult
import price_db


def screen_stocks(db: Session, criteria: ScreenerCriteria) -> List[ScreenerResult]:
    """筛选股票"""
    # 动态当前年份（不再硬编码）
    current_year = date.today().year

    stocks = db.query(Stock).all()
    results = []

    for stock in stocks:
        financials = db.query(StockFinancial).filter(
            StockFinancial.stock_id == stock.id,
            StockFinancial.report_date >= date(current_year - criteria.pe_years + 1, 1, 1)
        ).order_by(StockFinancial.report_date.desc()).all()

        if len(financials) < criteria.pe_years:
            continue

        pe_values = [f.pe_ratio for f in financials[:criteria.pe_years]]

        if any(pe is None for pe in pe_values):
            continue
        if not all(criteria.max_pe > pe > criteria.min_pe for pe in pe_values):
            continue

        latest = financials[0]
        if latest.market_cap is None or latest.market_cap >= criteria.max_market_cap:
            continue

        results.append(ScreenerResult(
            code=stock.code,
            name=stock.name,
            sector=stock.sector,
            pe_current=pe_values[0] if len(pe_values) > 0 else None,
            pe_year1  =pe_values[1] if len(pe_values) > 1 else None,
            pe_year2  =pe_values[2] if len(pe_values) > 2 else None,
            pb_ratio  =latest.pb_ratio,
            ps_ratio  =latest.ps_ratio,
            market_cap=latest.market_cap,
            sharpe_ratio=latest.sharpe_ratio,
            data_source =latest.data_source,
        ))

    results.sort(key=lambda x: x.market_cap if x.market_cap else float('inf'))
    return results


def get_stock_financials(db: Session, stock_code: str) -> List[dict]:
    """获取股票财务数据"""
    stock = db.query(Stock).filter(Stock.code == stock_code).first()
    if not stock:
        return []

    financials = db.query(StockFinancial).filter(
        StockFinancial.stock_id == stock.id
    ).order_by(StockFinancial.report_date.desc()).all()

    return [
        {
            "report_date": f.report_date.isoformat(),
            "pe_ratio":    f.pe_ratio,
            "market_cap":  f.market_cap,
        }
        for f in financials
    ]


def get_stock_prices(db: Session, stock_code: str) -> List[dict]:
    """获取股票价格数据（直接读 MySQL）"""
    stock = db.query(Stock).filter(Stock.code == stock_code).first()
    if not stock:
        return []

    exchange = stock.exchange or "SZSE"
    df = price_db.get_stock_prices(stock_code, exchange)

    if df.empty:
        return []

    return [
        {
            "date":   str(row["date"]),
            "open":   row["open"],
            "high":   row["high"],
            "low":    row["low"],
            "close":  row["close"],
            "volume": row["volume"],
        }
        for _, row in df.iterrows()
    ]
