"""
初始化股票列表模块
从 MySQL 历史行情库读取真实股票列表，写入 stocks 表。
财务数据（PE/PB/市値）请通过「同步基本面」按鈕从 baostock 获取真实数据。
"""
from market_database import MarketSessionLocal, init_market_db
from market_models import Stock, StockFinancial
from price_db import get_all_symbols


def generate_demo_data():
    """
    初始化股票列表：
      1. 从 MySQL dbbardata 读取全部股票列表
      2. 写入 stocks 表（代码、交易所）
      3. 不写入任何财务数据，请后续点击「同步基本面」获取真实 PE/PB/市値
    """
    init_market_db()
    db = MarketSessionLocal()

    try:
        # 清空现有元数据
        db.query(StockFinancial).delete()
        db.query(Stock).delete()
        db.commit()

        print("正在从 MySQL 行情库获取股票列表...")
        symbol_list = get_all_symbols()
        if not symbol_list:
            print("⚠️ MySQL 中无数据，请确认 dbbardata 表不为空")
            return

        total = len(symbol_list)
        print(f"✅ 共 {total} 只股票，开始写入...\n")
        batch_size = 200

        for idx, s in enumerate(symbol_list):
            db.add(Stock(
                code=s["code"],
                name=s["code"],   # 行情库无名称，先用代码代替，同步基本面后会更新
                sector="未知",
                exchange=s["exchange"],
            ))
            if (idx + 1) % batch_size == 0:
                db.commit()
                print(f"  💾 {idx+1}/{total} 已提交")

        db.commit()
        print(f"\n✅ 初始化完成！共导入 {total} 只股票")
        print("请点击「同步基本面」获取真实 PE/PB/市値数据")

    except Exception as e:
        import traceback
        print(f"❌ 初始化失败: {e}")
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    generate_demo_data()
