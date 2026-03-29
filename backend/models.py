"""
数据模型模块 - 回测数据库 stock_data.db 的表结构
股票基本信息与财务数据请使用 market_models.py（market_data.db）
"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime
from datetime import datetime
from database import Base


# ========== 回测交易存储表 ==========

class BacktestTrade(Base):
    """当前回测交易记录表（每次回测视为一次覆盖）"""
    __tablename__ = "backtest_trades_current"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    run_id      = Column(String(36), nullable=False, index=True)   # UUID分组本次回测
    stock_code  = Column(String(20), nullable=False, index=True)
    stock_name  = Column(String(100))
    market      = Column(String(10), index=True)  # SH/SZ/CYB/OTHER
    buy_date    = Column(Date)
    buy_price   = Column(Float)
    sell_date   = Column(Date, nullable=True)
    sell_price  = Column(Float, nullable=True)
    profit_rate = Column(Float, nullable=True)
    lowest_after_buy   = Column(Float, nullable=True)
    highest_after_buy  = Column(Float, nullable=True)
    entry_inefficiency = Column(Float, nullable=True)
    exit_inefficiency  = Column(Float, nullable=True)
    close_reason = Column(String(20), nullable=True)   # profit/timeout/holding
    created_at   = Column(DateTime, default=datetime.now)


class BacktestTradeHistory(Base):
    """回测交易历史表（每次新回测前将当前表庐存于此）"""
    __tablename__ = "backtest_trades_history"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    run_id      = Column(String(36), nullable=False, index=True)
    stock_code  = Column(String(20), nullable=False, index=True)
    stock_name  = Column(String(100))
    market      = Column(String(10), index=True)
    buy_date    = Column(Date)
    buy_price   = Column(Float)
    sell_date   = Column(Date, nullable=True)
    sell_price  = Column(Float, nullable=True)
    profit_rate = Column(Float, nullable=True)
    lowest_after_buy   = Column(Float, nullable=True)
    highest_after_buy  = Column(Float, nullable=True)
    entry_inefficiency = Column(Float, nullable=True)
    exit_inefficiency  = Column(Float, nullable=True)
    close_reason = Column(String(20), nullable=True)
    created_at   = Column(DateTime)                             # 原始创建时间
    archived_at  = Column(DateTime, default=datetime.now)       # 入历史时间


# ========== 贝叶斯参数优化训练记录表 ==========

class RLTrainingRun(Base):
    """每一轮贝叶斯/RL训练的结果记录"""
    __tablename__ = "rl_training_runs"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    session_id      = Column(String(36), nullable=False, index=True)  # 一次训练会话的 UUID
    trial_number    = Column(Integer, nullable=False)                  # 本轮编号（从1开始）
    dip_threshold   = Column(Float, nullable=False)
    profit_target   = Column(Float, nullable=False)
    reward          = Column(Float, nullable=False)   # 总收益（元）
    total_trades    = Column(Integer)
    closed_trades   = Column(Integer)
    win_rate        = Column(Float)
    avg_profit_rate = Column(Float)
    holding_count   = Column(Integer)
    created_at      = Column(DateTime, default=datetime.now)
