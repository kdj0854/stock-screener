"""
回测数据库配置模块
存储回测交易记录和 RL 训练结果，使用 MySQL
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import get_mysql_config


def _build_url() -> str:
    cfg = get_mysql_config()
    return (
        f"mysql+pymysql://{cfg['user']}:{cfg['password']}"
        f"@{cfg['host']}:{cfg['port']}/{cfg['database']}"
        f"?charset={cfg['charset']}"
    )


# 全局单例引擎
engine = create_engine(_build_url(), pool_pre_ping=True, pool_size=5, max_overflow=10)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI 依赖注入：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """(已删除）初始化回测数据库表结构（MySQL 下建表请执行说明文档中的 SQL）"""
    Base.metadata.create_all(bind=engine)
