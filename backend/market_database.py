"""
市场数据库配置模块
独立 SQLite 数据库 market_data.db，存储从 baostock 获取的股票基本信息与财务指标
（与回测数据库 stock_data.db 完全分离）
"""
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKET_DB_URL = f"sqlite:///{os.path.join(BASE_DIR, 'market_data.db')}"

market_engine = create_engine(
    MARKET_DB_URL,
    connect_args={"check_same_thread": False}
)

MarketSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=market_engine)

MarketBase = declarative_base()


def get_market_db():
    """FastAPI 依赖注入：获取 market_data.db 会话"""
    db = MarketSessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_market_db():
    """初始化 market_data.db 表结构"""
    MarketBase.metadata.create_all(bind=market_engine)
