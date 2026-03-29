"""
市场数据库配置模块
存储从 baostock 获取的股票基本信息与财务指标，使用 MySQL
"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from database import engine  # 复用 database.py 中的全局引擎

MarketSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

MarketBase = declarative_base()

# 保留别名，内部代码需要它
market_engine = engine


def get_market_db():
    """FastAPI 依赖注入：获取市场数据库会话"""
    db = MarketSessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_market_db():
    """(已删除）初始化市场数据库表结构（MySQL 下建表请执行说明文档中的 SQL）"""
    MarketBase.metadata.create_all(bind=engine)
