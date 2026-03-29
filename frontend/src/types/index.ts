// 股票筛选条件
export interface ScreenerCriteria {
  min_pe: number;
  max_pe: number;
  max_market_cap: number;
  pe_years: number;
}

// 筛选结果
export interface ScreenerResult {
  code: string;
  name: string;
  sector: string | null;
  pe_current: number | null;
  pe_year1: number | null;
  pe_year2: number | null;
  market_cap: number | null;
}

// 财务数据
export interface FinancialData {
  report_date: string;
  pe_ratio: number | null;
  market_cap: number | null;
}

// 价格数据
export interface PriceData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

// 回测配置
export interface BacktestConfig {
  dip_threshold: number;
  profit_target: number;
  lookback_period: number;
}

// 交易记录
export interface TradeRecord {
  stock_code: string;
  stock_name: string;
  market: string | null;   // SH/SZ/CYB—来自 DB 查询时有値
  buy_date: string;
  buy_price: number;
  sell_date: string | null;
  sell_price: number | null;
  profit_rate: number | null;
  lowest_after_buy: number | null;
  highest_after_buy: number | null;
  entry_inefficiency: number | null;
  exit_inefficiency: number | null;
  close_reason: string | null;
}

// 回测汇总
export interface BacktestSummary {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_profit_rate: number;
  avg_profit_rate: number;
  avg_entry_inefficiency: number;
  avg_exit_inefficiency: number;
}

// 回测响应
export interface BacktestResponse {
  config: BacktestConfig;
  summary: BacktestSummary;
  trades: TradeRecord[];
}

// 优化结果
export interface OptimizationResult {
  original_config: BacktestConfig;
  optimized_dip_threshold: number;
  optimized_profit_target: number;
  original_summary: BacktestSummary;
  simulated_summary: BacktestSummary | null;
  recommendation: string;
}

// 分页交易记录响应
export interface PaginatedTradesResponse {
  total: number;
  page: number;
  page_size: number;
  trades: TradeRecord[];
}

// 交易筛选条件
export interface TradeFilters {
  stockCode: string;
  market: string;     // '' | 'SH' | 'SZ' | 'CYB'
  holdingOnly: boolean;
  excludeKcb: boolean;
}

// 股票信息
export interface StockInfo {
  code: string;
  name: string;
  sector: string | null;
}

// 流式回测进度
export interface BacktestProgress {
  current: number;
  total: number;
}

// RL / 贝叶斯参数优化训练配置
export interface RLTrainConfig {
  n_trials: number;          // 总训练轮次
  stocks_per_trial: number;  // 每轮采样股票数，0=全部
  lookback_period: number;
}

// 每一轮训练结果（后端流式推送）
export interface RLTrialResult {
  trial: number;
  total_trials: number;
  dip_threshold: number;
  profit_target: number;
  reward: number;         // 本轮总收益（元）
  best_reward: number;    // 历史最优奖励
  best_params: { dip_threshold: number; profit_target: number } | null;
  total_trades: number;
  closed_trades: number;
  win_rate: number;
  done: boolean;
}

// 价格数据增量同步进度
export interface PriceSyncProgress {
  current: number;
  total: number;
  code: string;
  added: number;
  added_total: number;
  error?: string;
  done: boolean;
}

// 累计收益率曲线数据点
export interface ProfitCurvePoint {
  date: string;
  daily_profit: number;
  cumulative: number;
  count: number;
}

// 流式回测每个数据块
export interface BacktestChunk {
  progress: BacktestProgress;
  summary: BacktestSummary;
  new_trades: TradeRecord[];  // 本批次新增的交易记录
  done: boolean;
}
