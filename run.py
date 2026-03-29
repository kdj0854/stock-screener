"""
股票筛选与策略回溯工具 - 命令行运行脚本
直接运行此脚本即可完成：数据生成 -> 筛选 -> 回测 -> 优化
"""
import os
import sys

# 确保能够导入当前目录的模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, init_db
from market_database import MarketSessionLocal, init_market_db
from market_models import Stock
from schemas import ScreenerCriteria, BacktestConfig
from services import screen_stocks, run_backtest, optimize_strategy
from demo_data import generate_demo_data


def print_header(title):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(title, data):
    """打印结果"""
    print(f"\n【{title}】")
    for item in data:
        print(item)


def main():
    """主函数"""
    print_header("股票筛选与策略回溯工具")
    print("开始运行...")
    
    # 1. 初始化数据库和生成演示数据
    print_header("Step 1: 初始化数据")
    print("正在生成演示数据...")
    generate_demo_data()
    print("✅ 演示数据生成完成！")
    
    db = MarketSessionLocal()
    
    try:
        # 2. 获取所有股票列表
        print_header("Step 2: 获取股票列表")
        stocks = db.query(Stock).all()
        stock_codes = [s.code for s in stocks]
        print(f"✅ 共获取 {len(stock_codes)} 只股票")
        
        # 3. 执行筛选
        print_header("Step 3: 股票筛选")
        print("筛选条件：")
        print("  - 市盈率连续 3 年小于 30")
        print("  - 当前市值小于 60 亿元")
        
        criteria = ScreenerCriteria(
            max_pe=30,
            max_market_cap=60,
            pe_years=3
        )
        screened_stocks = screen_stocks(db, criteria)
        
        print(f"\n✅ 筛选结果：共 {len(screened_stocks)} 只股票符合条件")
        if screened_stocks:
            print("\n符合条件股票列表：")
            print("-" * 80)
            print(f"{'代码':<10} {'名称':<15} {'行业':<10} {'当年PE':<10} {'市值(亿)':<10}")
            print("-" * 80)
            for stock in screened_stocks:
                print(f"{stock.code:<10} {stock.name:<15} {(stock.sector or '-'):<10} "
                      f"{stock.pe_current:.2f if stock.pe_current else '-':<10} "
                      f"{stock.market_cap:.2f if stock.market_cap else '-':<10}")
        
        # 使用筛选出的股票进行回测，如果没有符合条件的则使用全部股票
        if screened_stocks:
            backtest_codes = [s.code for s in screened_stocks]
            print(f"\n✅ 使用筛选出的 {len(backtest_codes)} 只股票进行回测")
        else:
            backtest_codes = stock_codes
            print(f"\n⚠️ 没有符合筛选条件的股票，使用全部 {len(backtest_codes)} 只股票进行回测")
        
        # 4. 执行回测
        print_header("Step 4: 策略回测")
        print("回测参数：")
        print("  - 跌买阈值：30% (股价从半年高点下跌30%后买入)")
        print("  - 盈利目标：10% (盈利10%后卖出)")
        print("  - 回溯周期：120天 (计算过去120天的最高价)")
        
        config = BacktestConfig(
            dip_threshold=0.3,
            profit_target=0.1,
            lookback_period=120
        )
        
        backtest_result = run_backtest(db, backtest_codes, config)
        
        print(f"\n✅ 回测完成！")
        print(f"\n【回测统计】")
        print(f"  总交易次数: {backtest_result.summary.total_trades}")
        print(f"  盈利交易: {backtest_result.summary.winning_trades}")
        print(f"  亏损交易: {backtest_result.summary.losing_trades}")
        print(f"  胜率: {backtest_result.summary.win_rate * 100:.2f}%")
        print(f"  总收益率: {backtest_result.summary.total_profit_rate * 100:.2f}%")
        print(f"  平均收益率: {backtest_result.summary.avg_profit_rate * 100:.2f}%")
        print(f"  平均买点无效度: {backtest_result.summary.avg_entry_inefficiency * 100:.2f}%")
        print(f"  平均卖点无效度: {backtest_result.summary.avg_exit_inefficiency * 100:.2f}%")
        
        # 显示交易记录
        if backtest_result.trades:
            print(f"\n【交易记录】(显示前10笔)")
            print("-" * 100)
            print(f"{'股票代码':<10} {'买入日期':<12} {'买入价':<10} {'卖出日期':<12} {'卖出价':<10} {'收益率':<10}")
            print("-" * 100)
            for trade in backtest_result.trades[:10]:
                profit_str = f"{trade.profit_rate * 100:.2f}%" if trade.profit_rate else "-"
                sell_date = trade.sell_date.strftime('%Y-%m-%d') if trade.sell_date else "-"
                print(f"{trade.stock_code:<10} {str(trade.buy_date):<12} {trade.buy_price:<10.2f} "
                      f"{sell_date:<12} {trade.sell_price if trade.sell_price else '-':<10} {profit_str:<10}")
        
        # 5. 执行优化
        print_header("Step 5: 策略优化")
        print("正在分析并优化策略参数...")
        
        optimization_result = optimize_strategy(db, backtest_codes, config)
        
        print(f"\n✅ 优化完成！")
        print(f"\n【参数优化建议】")
        print(f"  跌买阈值: {(optimization_result.original_config.dip_threshold * 100):.0f}% → "
              f"{(optimization_result.optimized_dip_threshold * 100):.0f}%")
        print(f"  盈利目标: {(optimization_result.original_config.profit_target * 100):.0f}% → "
              f"{(optimization_result.optimized_profit_target * 100):.0f}%")
        
        print(f"\n【优化分析详情】")
        print(optimization_result.recommendation)
        
        # 优化前后对比
        if optimization_result.simulated_summary:
            print(f"\n【优化前后效果对比】")
            print("-" * 60)
            print(f"{'指标':<20} {'优化前':<15} {'优化后':<15}")
            print("-" * 60)
            orig = optimization_result.original_summary
            sim = optimization_result.simulated_summary
            print(f"{'交易次数':<20} {orig.total_trades:<15} {sim.total_trades:<15}")
            print(f"{'胜率':<20} {orig.win_rate * 100:.2f}%{'':<10} {sim.win_rate * 100:.2f}%")
            print(f"{'平均收益率':<20} {orig.avg_profit_rate * 100:.2f}%{'':<10} {sim.avg_profit_rate * 100:.2f}%")
            print(f"{'买点无效度':<20} {orig.avg_entry_inefficiency * 100:.2f}%{'':<10} {sim.avg_entry_inefficiency * 100:.2f}%")
            print(f"{'卖点无效度':<20} {orig.avg_exit_inefficiency * 100:.2f}%{'':<10} {sim.avg_exit_inefficiency * 100:.2f}%")
        
        # 6. 完成
        print_header("运行完成！")
        print("""
使用说明：
  1. 筛选功能：过滤出市盈率连续3年<30且市值<60亿的股票
  2. 回测功能：模拟"跌买"策略（下跌30%买入，盈利10%卖出）
  3. 优化功能：分析买卖点无效度，自动优化参数

如需图形界面，请启动 Web 服务：
  - 后端: cd backend && python main.py
  - 前端: cd frontend && npm run dev

""")
        
    except Exception as e:
        print(f"\n❌ 运行出错: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
