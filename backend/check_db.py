"""
数据库连接与数据状态检查脚本
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 50)
print("1. 读取数据库配置")
print("=" * 50)
try:
    from config import get_mysql_config
    cfg = get_mysql_config()
    safe_cfg = {k: ("***" if k == "password" else v) for k, v in cfg.items()}
    print("配置:", safe_cfg)
except Exception as e:
    print("❌ 读取配置失败:", e)
    sys.exit(1)

print()
print("=" * 50)
print("2. 测试 MySQL 连接")
print("=" * 50)
try:
    import pymysql
    conn = pymysql.connect(**cfg)
    print("✅ MySQL 连接成功")
    cursor = conn.cursor()

    # 检查各表行数
    tables = ["stocks", "stock_financials", "backtest_trades_current",
              "backtest_trades_history", "rl_training_runs", "dbbardata",
              "dbbaroverview"]
    for t in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM `{t}`")
            count = cursor.fetchone()[0]
            print(f"  {t}: {count} 行")
        except Exception as e:
            print(f"  {t}: ❌ {e}")

    conn.close()
except Exception as e:
    print("❌ MySQL 连接失败:", e)
