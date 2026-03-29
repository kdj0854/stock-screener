"""
策略回测服务
实现跌买点策略回测：
- 跌买点：股价从过去半年的最高点下跌超过阈值（如 30%）时买入
- 赢利点：买入后盈利超过目标（如 10%）时卖出
"""
from typing import List, Optional
from datetime import date, timedelta
from sqlalchemy.orm import Session
import pandas as pd

from market_models import Stock
from schemas import BacktestConfig, TradeRecord, BacktestSummary, BacktestResponse
import price_db


def run_backtest(
    db: Session,
    stock_codes: List[str],
    config: BacktestConfig
) -> BacktestResponse:
    """运行回测（价格数据直接读 MySQL）"""
    all_trades = []

    for stock_code in stock_codes:
        trades = backtest_single_stock(db, stock_code, config)
        all_trades.extend(trades)

    summary = calculate_summary(all_trades)

    return BacktestResponse(
        config=config,
        summary=summary,
        trades=all_trades
    )


def backtest_single_stock(
    db: Session,
    stock_code: str,
    config: BacktestConfig
) -> List[TradeRecord]:
    """对单只股票进行回测（价格数据来自 MySQL dbbardata）"""

    # 获取股票元信息（需要 exchange 字段）
    stock = db.query(Stock).filter(Stock.code == stock_code).first()
    if not stock:
        return []

    exchange = stock.exchange or "SZSE"

    # 直接从 MySQL 读取日线价格
    price_df = price_db.get_stock_prices(stock_code, exchange)

    if price_df.empty or len(price_df) < config.lookback_period + 10:
        return []

    # 确保 date 列为 date 类型
    price_df["date"] = pd.to_datetime(price_df["date"]).dt.date

    # 计算过去 N 天的滚动最高价
    price_df["rolling_high"] = price_df["high"].rolling(
        window=config.lookback_period,
        min_periods=config.lookback_period
    ).max()

    # 计算跌幅
    price_df["drawdown"] = (
        (price_df["close"] - price_df["rolling_high"]) / price_df["rolling_high"]
    )

    trades = []
    holding = None

    for i in range(config.lookback_period, len(price_df)):
        row          = price_df.iloc[i]
        current_date = row["date"]
        current_price = row["close"]
        drawdown      = row["drawdown"]

        if holding is None:
            # 无持仓：检查跌买信号
            if drawdown <= -config.dip_threshold:
                holding = {
                    "buy_date":   current_date,
                    "buy_price":  current_price,
                    "stock_code": stock_code,
                    "stock_name": stock.name,
                }
        else:
            # 持仓中：检查赢利点 或 超过半年强制平仓
            profit_rate = (current_price - holding["buy_price"]) / holding["buy_price"]
            holding_days = (current_date - holding["buy_date"]).days
            force_close = holding_days > 180  # 超过半年强制平仓

            if profit_rate >= config.profit_target or force_close:
                buy_idx = price_df[price_df["date"] == holding["buy_date"]].index[0]
                post_buy = price_df.iloc[buy_idx:i + 1]
                lowest_after_buy  = post_buy["low"].min()
                highest_after_buy = post_buy["high"].max()

                entry_inefficiency = (holding["buy_price"] - lowest_after_buy) / lowest_after_buy
                exit_inefficiency  = (highest_after_buy - current_price) / highest_after_buy

                trades.append(TradeRecord(
                    stock_code=holding["stock_code"],
                    stock_name=holding["stock_name"],
                    buy_date=holding["buy_date"],
                    buy_price=holding["buy_price"],
                    sell_date=current_date,
                    sell_price=current_price,
                    profit_rate=profit_rate,
                    lowest_after_buy=lowest_after_buy,
                    highest_after_buy=highest_after_buy,
                    entry_inefficiency=entry_inefficiency,
                    exit_inefficiency=exit_inefficiency,
                    close_reason="timeout" if force_close else "profit",
                ))
                holding = None

    # 循环结束后仍持仓：记录为未平仓交易
    if holding is not None:
        buy_idx = price_df[price_df["date"] == holding["buy_date"]].index[0]
        post_buy = price_df.iloc[buy_idx:]
        last_price        = price_df.iloc[-1]["close"]
        lowest_after_buy  = post_buy["low"].min()
        highest_after_buy = post_buy["high"].max()
        profit_rate = (last_price - holding["buy_price"]) / holding["buy_price"]

        entry_inefficiency = (holding["buy_price"] - lowest_after_buy) / lowest_after_buy
        exit_inefficiency  = (highest_after_buy - last_price) / highest_after_buy

        trades.append(TradeRecord(
            stock_code=holding["stock_code"],
            stock_name=holding["stock_name"],
            buy_date=holding["buy_date"],
            buy_price=holding["buy_price"],
            sell_date=None,
            sell_price=None,
            profit_rate=profit_rate,
            lowest_after_buy=lowest_after_buy,
            highest_after_buy=highest_after_buy,
            entry_inefficiency=entry_inefficiency,
            exit_inefficiency=exit_inefficiency,
            close_reason="holding",
        ))

    return trades


def calculate_summary(trades: List[TradeRecord]) -> BacktestSummary:
    """计算回测汇总统计（仅统计已平仓交易，排除持仓中浮盈）"""
    if not trades:
        return BacktestSummary(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_profit_rate=0.0,
            avg_profit_rate=0.0,
            avg_entry_inefficiency=0.0,
            avg_exit_inefficiency=0.0
        )

    # 已平仓：sell_date 不为空
    closed = [t for t in trades if t.sell_date is not None]

    winning_trades = [t for t in closed if t.profit_rate and t.profit_rate > 0]
    losing_trades  = [t for t in closed if t.profit_rate and t.profit_rate <= 0]
    total_profit   = sum(t.profit_rate for t in closed if t.profit_rate)

    valid_entry = [t.entry_inefficiency for t in trades if t.entry_inefficiency is not None]
    valid_exit  = [t.exit_inefficiency  for t in trades if t.exit_inefficiency  is not None]

    return BacktestSummary(
        total_trades=len(trades),
        winning_trades=len(winning_trades),
        losing_trades=len(losing_trades),
        win_rate=len(winning_trades) / len(closed) if closed else 0.0,
        total_profit_rate=total_profit,
        avg_profit_rate=total_profit / len(closed) if closed else 0.0,
        avg_entry_inefficiency=sum(valid_entry) / len(valid_entry) if valid_entry else 0,
        avg_exit_inefficiency =sum(valid_exit)  / len(valid_exit)  if valid_exit  else 0,
    )
