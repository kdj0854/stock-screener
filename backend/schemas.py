"""
Pydantic 模型 - 用于 API 请求和响应
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date


# ========== 股票相关模型 ==========

class StockBase(BaseModel):
    """股票基础模型"""
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    sector: Optional[str] = Field(None, description="所属行业")


class StockCreate(StockBase):
    """创建股票请求"""
    pass


class StockResponse(StockBase):
    """股票响应"""
    id: int
    
    class Config:
        from_attributes = True


class StockFinancialBase(BaseModel):
    """财务数据基础模型"""
    report_date: date
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None
    market_cap: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    data_source: Optional[str] = None


class StockFinancialResponse(StockFinancialBase):
    """财务数据响应"""
    id: int
    stock_id: int
    
    class Config:
        from_attributes = True


class StockWithFinancials(StockResponse):
    """带财务数据的股票"""
    financials: List[StockFinancialResponse] = []
    
    class Config:
        from_attributes = True


# ========== 筛选相关模型 ==========

class ScreenerCriteria(BaseModel):
    """筛选条件"""
    min_pe: float = Field(0, description="最小市盈率（0=不限）")
    max_pe: float = Field(30, description="最大市盈率")
    max_market_cap: float = Field(60, description="最大市值（亿元）")
    pe_years: int = Field(3, description="市盈率连续年数")


class ScreenerResult(BaseModel):
    """筛选结果"""
    code: str
    name: str
    sector: Optional[str]
    pe_current: Optional[float]
    pe_year1: Optional[float]
    pe_year2: Optional[float]
    pb_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None
    market_cap: Optional[float]
    sharpe_ratio: Optional[float] = None
    data_source: Optional[str] = None


# ========== 回测相关模型 ==========

class BacktestConfig(BaseModel):
    """回测配置"""
    dip_threshold: float = Field(0.3, description="跌买阈值（0.3表示30%）")
    profit_target: float = Field(0.1, description="盈利目标（0.1表示10%）")
    lookback_period: int = Field(120, description="回溯周期（天），默认120天=半年")


class TradeRecord(BaseModel):
    """交易记录"""
    stock_code: str
    stock_name: str
    market: Optional[str] = None          # SH/SZ/CYB—来自 DB 查询时有値
    buy_date: date
    buy_price: float
    sell_date: Optional[date]
    sell_price: Optional[float]
    profit_rate: Optional[float]
    lowest_after_buy: Optional[float]
    highest_after_buy: Optional[float]
    entry_inefficiency: Optional[float]
    exit_inefficiency: Optional[float]
    close_reason: Optional[str] = None  # 平仓原因: profit/timeout/holding


class BacktestSummary(BaseModel):
    """回测摘要"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_profit_rate: float
    avg_profit_rate: float
    avg_entry_inefficiency: float
    avg_exit_inefficiency: float


class BacktestResponse(BaseModel):
    """回测响应"""
    config: BacktestConfig
    summary: BacktestSummary
    trades: List[TradeRecord]


class PaginatedTradesResponse(BaseModel):
    """分页交易记录响应"""
    total: int
    page: int
    page_size: int
    trades: List[TradeRecord]


# ========== 优化相关模型 ==========

class OptimizationResult(BaseModel):
    """优化结果"""
    original_config: BacktestConfig
    optimized_dip_threshold: float
    optimized_profit_target: float
    original_summary: BacktestSummary
    simulated_summary: Optional[BacktestSummary]
    recommendation: str


# ========== 演示数据模型 ==========

class DemoStockData(BaseModel):
    """演示用股票数据"""
    code: str
    name: str
    sector: str
    financials: List[StockFinancialBase]
    prices: List[dict]  # date, open, high, low, close, volume
