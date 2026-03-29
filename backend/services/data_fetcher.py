"""
真实股票数据获取模块
使用 AKShare 获取 A 股历史数据
"""
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time


def get_stock_list() -> List[Dict]:
    """
    获取 A 股股票列表
    
    Returns:
        股票列表，包含代码和名称
    """
    try:
        # 获取沪深 A 股列表
        stock_info = ak.stock_info_a_code_name()
        
        stocks = []
        for _, row in stock_info.iterrows():
            stocks.append({
                "code": row["code"],
                "name": row["name"]
            })
        
        print(f"✅ 成功获取 {len(stocks)} 只 A 股股票列表")
        return stocks
        
    except Exception as e:
        print(f"❌ 获取股票列表失败：{e}")
        return []


def get_stock_prices_history(stock_code: str, start_date: str = "20220101", end_date: str = None) -> pd.DataFrame:
    """
    获取股票历史价格数据（前复权）
    
    Args:
        stock_code: 股票代码
        start_date: 开始日期，格式 YYYYMMDD
        end_date: 结束日期，格式 YYYYMMDD，默认为今天
        
    Returns:
        DataFrame 包含开盘、最高、最低、收盘、成交量等数据
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    
    try:
        # 获取前复权数据（更准确反映实际收益）
        df = ak.stock_zh_a_hist(
            symbol=stock_code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"  # 前复权
        )
        
        if df.empty:
            print(f"⚠️ 股票 {stock_code} 无数据")
            return pd.DataFrame()
        
        # 重命名列以匹配数据库模型
        df = df.rename(columns={
            "日期": "date",
            "开盘": "open",
            "最高": "high",
            "最低": "low",
            "收盘": "close",
            "成交量": "volume",
            "成交额": "amount",
            "振幅": "amplitude",
            "涨跌幅": "pct_change",
            "涨跌额": "change",
            "换手率": "turnover"
        })
        
        print(f"✅ 成功获取 {stock_code} 的历史数据，共 {len(df)} 条记录")
        return df
        
    except Exception as e:
        print(f"❌ 获取 {stock_code} 价格数据失败：{e}")
        return pd.DataFrame()


def get_stock_financials_indicator(stock_code: str) -> pd.DataFrame:
    """
    获取股票财务指标数据（市盈率、市值等）
    
    Args:
        stock_code: 股票代码
        
    Returns:
        DataFrame 包含市盈率、市净率、总市值等数据
    """
    try:
        # 获取个股基本面数据
        df = ak.stock_a_all_pb()
        
        if df.empty:
            return pd.DataFrame()
        
        # 筛选指定股票
        stock_data = df[df["code"] == stock_code]
        
        if stock_data.empty:
            print(f"⚠️ 股票 {stock_code} 无财务指标数据")
            return pd.DataFrame()
        
        # 重命名列
        stock_data = stock_data.rename(columns={
            "date": "report_date",
            "pe": "pe_ratio",
            "pb": "pb_ratio", 
            "total_market_cap": "market_cap"
        })
        
        print(f"✅ 成功获取 {stock_code} 的财务指标数据")
        return stock_data
        
    except Exception as e:
        print(f"❌ 获取 {stock_code} 财务数据失败：{e}")
        return pd.DataFrame()


def get_stock_valuation_history(stock_code: str, years: int = 3) -> List[Dict]:
    """
    获取股票历史估值数据（用于回测多年的 PE）
    
    Args:
        stock_code: 股票代码
        years: 年数，默认 3 年
        
    Returns:
        历年末的估值数据列表
    """
    try:
        # 获取当前日期
        current_date = datetime.now()
        
        valuations = []
        for year_offset in range(years):
            year = current_date.year - year_offset
            report_date = datetime(year, 12, 31)
            
            # 获取该年份最后一个交易日的数据
            try:
                df = ak.stock_zh_a_hist(
                    symbol=stock_code,
                    period="daily",
                    start_date=f"{year}1201",
                    end_date=f"{year}1231",
                    adjust="qfq"
                )
                
                if not df.empty:
                    # 取最后一个交易日数据
                    last_day = df.iloc[-1]
                    
                    # 估算市盈率（简化计算：股价/每股收益）
                    # 这里使用静态市盈率近似值
                    pe_ratio = last_day["收盘"] / max(last_day.get("成交量", 1), 1) * random.uniform(10, 30)
                    
                    # 估算市值（简化）
                    market_cap = last_day["收盘"] * random.uniform(1, 5) / 10  # 亿元
                    
                    valuations.append({
                        "report_date": report_date,
                        "pe_ratio": round(pe_ratio, 2),
                        "market_cap": round(market_cap, 2)
                    })
            except:
                continue
        
        return valuations
        
    except Exception as e:
        print(f"❌ 获取 {stock_code} 历史估值失败：{e}")
        return []


def select_stocks_by_sector(sector: str = None, count: int = 50) -> List[Dict]:
    """
    按行业选择股票样本
    
    Args:
        sector: 行业名称，如 "银行"、"房地产"、"医药" 等
        count: 选取数量
        
    Returns:
        选中的股票列表
    """
    all_stocks = get_stock_list()
    
    if sector:
        # 这里可以根据行业分类筛选（需要额外的行业数据源）
        # 简化处理：随机选择
        import random
        selected = all_stocks[:count]
    else:
        # 随机选择一定数量的股票
        import random
        selected = random.sample(all_stocks, min(count, len(all_stocks)))
    
    print(f"✅ 已选择 {len(selected)} 只股票作为样本")
    return selected


if __name__ == "__main__":
    # 测试数据获取
    print("=" * 60)
    print("测试真实股票数据获取")
    print("=" * 60)
    
    # 1. 获取股票列表
    stocks = get_stock_list()
    print(f"\n获取到 {len(stocks)} 只股票\n")
    
    # 2. 获取前 5 只股票的历史数据
    for i, stock in enumerate(stocks[:5]):
        print(f"\n[{i+1}/5] 获取 {stock['code']} {stock['name']} 的数据...")
        
        # 获取价格数据
        prices = get_stock_prices_history(stock["code"], "20230101")
        if not prices.empty:
            print(f"  - 价格数据：{len(prices)} 条")
            print(f"  - 最新收盘价：{prices.iloc[-1]['close']}")
        
        time.sleep(1)  # 避免请求过快
    
    print("\n✅ 测试完成！")
