"""
项目配置模块 - 从 vt_setting.json 读取数据库配置
"""
import json
import os

# VnPy 配置文件路径
VT_SETTING_PATH = r"C:\Users\Administrator\.vntrader\vt_setting.json"


def get_mysql_config() -> dict:
    """从 vt_setting.json 读取 MySQL 配置"""
    try:
        with open(VT_SETTING_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        return {
            "host": cfg.get("database.host", "127.0.0.1"),
            "port": int(cfg.get("database.port", 3306)),
            "user": cfg.get("database.user", "root"),
            "password": cfg.get("database.password", ""),
            "database": cfg.get("database.database", "vnpy"),
            "charset": "utf8mb4"
        }
    except Exception as e:
        print(f"⚠️ 读取配置文件失败: {e}，使用默认配置")
        return {
            "host":     os.environ.get("MYSQL_HOST",     "127.0.0.1"),
            "port":     int(os.environ.get("MYSQL_PORT", "3306")),
            "user":     os.environ.get("MYSQL_USER",     "root"),
            "password": os.environ.get("MYSQL_PASSWORD", ""),
            "database": os.environ.get("MYSQL_DATABASE", "vnpy"),
            "charset":  "utf8mb4"
        }
