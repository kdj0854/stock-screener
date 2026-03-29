"""
市场数据模型 - 归属 market_data.db
存储从 baostock 拉取的股票基本信息与财务指标（PE/PB/PS/夏普率等）
"""
from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from market_database import MarketBase


class Stock(MarketBase):
    """股票基本信息表"""
    __tablename__ = "stocks"

    id       = Column(Integer, primary_key=True, index=True)
    code     = Column(String(20), unique=True, index=True, nullable=False)  # 股票代码
    name     = Column(String(100), nullable=False)                          # 股票名称
    sector   = Column(String(100))                                          # 所属行业
    exchange = Column(String(20))                                           # 交易所：SSE / SZSE

    financials = relationship("StockFinancial", back_populates="stock", cascade="all, delete-orphan")


class StockFinancial(MarketBase):
    """股票财务/估值数据表（来源：baostock）"""
    __tablename__ = "stock_financials"

    id           = Column(Integer, primary_key=True, index=True)
    stock_id     = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    report_date  = Column(Date, nullable=False)   # 报告日期（通常为年末 12-31）
    pe_ratio     = Column(Float)                  # 市盈率 TTM
    pb_ratio     = Column(Float)                  # 市净率 MRQ
    ps_ratio     = Column(Float)                  # 市销率 TTM
    market_cap   = Column(Float)                  # 总市值（亿元，由价格数据估算）
    sharpe_ratio = Column(Float)                  # 年化夏普率（近1年日线收益计算）
    data_source  = Column(String(20), default="baostock")  # 数据来源

    stock = relationship("Stock", back_populates="financials")
