"""
演示数据生成模块
从 MySQL 历史行情库读取真实股票列表，批量估算市値，写入 market_data.db

注：行情库只有 K 线价格数据，没有净利润/EPS 等财务数据，
市値（market_cap）是基于 [平均成交量 x 平均收盘价] 的近似估算，仅供筛选参考。
建议后续调用 sync_all_stock_info() 使用 baostock 获取真实估値。
"""
import random
from datetime import datetime
from market_database import MarketSessionLocal, init_market_db
from market_models import Stock, StockFinancial
from price_db import get_all_symbols, get_all_price_stats


def generate_demo_data():
    """
    初始化所有股票数据：
      1. 从 MySQL dbbardata 读取全部股票列表
      2. 一次批量查询所有股票均价/小山1年成交量
      3. 基于市值估算写入 SQLite，价格数据不复制，回测时直接读 MySQL
    """
    init_market_db()
    db = MarketSessionLocal()

    try:
        # 清空现有元数据
        db.query(StockFinancial).delete()
        db.query(Stock).delete()
        db.commit()

        # 获取真实股票列表
        print("正在从 MySQL 行情库获取股票列表...")
        symbol_list = get_all_symbols()
        if not symbol_list:
            print("⚠️ MySQL 中无数据，请确认 dbbardata 表不为空")
            return

        # 批量获取所有股票近 1 年均价统计（一次查询）
        print("正在批量读取价格统计（一次 SQL）...")
        all_stats = get_all_price_stats()  # {"000001_SZSE": {avg_close, avg_volume}, ...}

        total = len(symbol_list)
        print(f"✅ 共 {total} 只股票，开始写入 SQLite...\n")

        current_year  = datetime.now().year
        financial_years = [current_year - 2, current_year - 1, current_year]
        batch_size = 200

        for idx, s in enumerate(symbol_list):
            code     = s["code"]
            exchange = s["exchange"]

            # 创建 Stock 条目
            stock = Stock(
                code=code,
                name=code,       # 行情库无股票名称，先用代码代替（后续 baostock 同步会更新）
                sector="未知",
                exchange=exchange,
            )
            db.add(stock)
            db.flush()

            # 从批量统计中取当前股票的均价/小山成交量
            key   = f"{code}_{exchange}"
            stats = all_stats.get(key, {})
            avg_close  = stats.get("avg_close",  0)
            avg_volume = stats.get("avg_volume", 0)

            # 估算市値（产）：手均量 x100 x 均价 / 1亿
            if avg_close > 0 and avg_volume > 0:
                market_cap = avg_close * avg_volume * 100 / 1e8
                market_cap = round(max(5.0, min(5000.0, market_cap)), 2)
            else:
                market_cap = round(random.uniform(10.0, 200.0), 2)

            # PE: VnPy 无财务数据，用 A 股常见市盈率范围模拟（并非真实市盈率）
            pe_ratio = round(random.uniform(10.0, 35.0), 2)

            # 写入连续三年财务数据
            for year in financial_years:
                db.add(StockFinancial(
                    stock_id=stock.id,
                    report_date=datetime(year, 12, 31).date(),
                    pe_ratio=round(pe_ratio * random.uniform(0.85, 1.15), 2),
                    market_cap=round(market_cap * random.uniform(0.85, 1.15), 2),
                ))

            # 每 batch_size 条提交一次
            if (idx + 1) % batch_size == 0:
                db.commit()
                print(f"  💾 {idx+1}/{total} 已提交")

        db.commit()
        print(f"\n✅ 初始化完成！共导入 {total} 只股票")
        print(f"⚠️  注意：PE 市盈率为基于 A 股常见范围的模拟値，非真实市盈率")
        print(f"⚠️  市値为基于 [平均成交量 xd7 均价] 的近似估算，不代表真实总市値")

    except Exception as e:
        import traceback
        print(f"❌ 初始化失败: {e}")
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    generate_demo_data()
