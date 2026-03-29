"""
回测数据库配置模块 - stock_data.db
存储回测交易记录和 RL 训练结果
市场/财务数据请使用 market_database.py（market_data.db）
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# 数据库文件路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'stock_data.db')}"

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化回测数据库表（stock_data.db）"""
    Base.metadata.create_all(bind=engine)
