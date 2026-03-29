"""
策略优化服务
根据回测结果优化买卖点参数：
1. 分析买点无效度：如果买点无效度高，建议增大跌买阈值
2. 分析卖点无效度：如果卖点无效度高，建议增大盈利目标
"""
from typing import List
from sqlalchemy.orm import Session

from schemas import BacktestConfig, BacktestResponse, OptimizationResult, BacktestSummary
from services.backtest import run_backtest


def optimize_strategy(
    db: Session,
    stock_codes: List[str],
    original_config: BacktestConfig
) -> OptimizationResult:
    """
    优化策略参数
    
    优化逻辑：
    1. 运行原始回测，获取买点无效度和卖点无效度
    2. 根据无效度分析调整参数：
       - 如果平均买点无效度 > 5%，建议增大跌买阈值
       - 如果平均卖点无效度 > 10%，建议增大盈利目标
    3. 使用优化后的参数重新回测，比较效果
    
    Args:
        db: 数据库会话
        stock_codes: 股票代码列表
        original_config: 原始回测配置
    
    Returns:
        优化结果
    """
    # 运行原始回测
    original_result = run_backtest(db, stock_codes, original_config)
    original_summary = original_result.summary
    
    # 分析无效度
    avg_entry_ineff = original_summary.avg_entry_inefficiency
    avg_exit_ineff = original_summary.avg_exit_inefficiency
    
    # 计算优化参数
    optimized_dip = original_config.dip_threshold
    optimized_profit = original_config.profit_target
    
    recommendation_parts = []
    
    # 分析买点无效度
    if avg_entry_ineff > 0.05:  # 超过5%
        # 建议增大跌买阈值，等待更深的回调再买入
        adjustment = min(0.1, avg_entry_ineff * 0.5)  # 每次最多增加10%
        optimized_dip = min(0.6, original_config.dip_threshold + adjustment)
        recommendation_parts.append(
            f"买点无效度较高({avg_entry_ineff:.1%})，建议将跌买阈值从{original_config.dip_threshold:.0%}调整到{optimized_dip:.0%}"
        )
    else:
        recommendation_parts.append(
            f"买点无效度适中({avg_entry_ineff:.1%})，跌买阈值保持{original_config.dip_threshold:.0%}"
        )
    
    # 分析卖点无效度
    if avg_exit_ineff > 0.10:  # 超过10%
        # 建议增大盈利目标，让利润奔跑
        adjustment = min(0.1, avg_exit_ineff * 0.5)
        optimized_profit = min(0.5, original_config.profit_target + adjustment)
        recommendation_parts.append(
            f"卖点无效度较高({avg_exit_ineff:.1%})，建议将盈利目标从{original_config.profit_target:.0%}调整到{optimized_profit:.0%}"
        )
    else:
        recommendation_parts.append(
            f"卖点无效度适中({avg_exit_ineff:.1%})，盈利目标保持{original_config.profit_target:.0%}"
        )
    
    # 使用优化后的参数重新回测
    optimized_config = BacktestConfig(
        dip_threshold=optimized_dip,
        profit_target=optimized_profit,
        lookback_period=original_config.lookback_period
    )
    
    simulated_result = run_backtest(db, stock_codes, optimized_config)
    simulated_summary = simulated_result.summary
    
    # 构建优化建议
    recommendation = "\n".join(recommendation_parts)
    
    # 添加对比分析
    if simulated_summary.total_trades > 0:
        recommendation += f"\n\n优化后效果预测："
        recommendation += f"\n- 交易次数：{original_summary.total_trades} -> {simulated_summary.total_trades}"
        recommendation += f"\n- 胜率：{original_summary.win_rate:.1%} -> {simulated_summary.win_rate:.1%}"
        recommendation += f"\n- 平均收益：{original_summary.avg_profit_rate:.1%} -> {simulated_summary.avg_profit_rate:.1%}"
    
    return OptimizationResult(
        original_config=original_config,
        optimized_dip_threshold=optimized_dip,
        optimized_profit_target=optimized_profit,
        original_summary=original_summary,
        simulated_summary=simulated_summary,
        recommendation=recommendation
    )


def simulate_with_params(
    db: Session,
    stock_codes: List[str],
    config: BacktestConfig
) -> BacktestSummary:
    """
    使用指定参数模拟回测
    
    Args:
        db: 数据库会话
        stock_codes: 股票代码列表
        config: 回测配置
    
    Returns:
        回测汇总
    """
    result = run_backtest(db, stock_codes, config)
    return result.summary
