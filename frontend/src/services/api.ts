import axios from 'axios';
import type { 
  ScreenerCriteria, 
  ScreenerResult, 
  BacktestConfig, 
  BacktestResponse,
  OptimizationResult,
  StockInfo,
  BacktestChunk,
  PaginatedTradesResponse,
  TradeFilters,
  RLTrainConfig,
  RLTrialResult,
  ProfitCurvePoint,
  PriceSyncProgress,
} from '../types';

const API_BASE = '/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

// 筛选股票
export async function screenStocks(criteria: ScreenerCriteria): Promise<ScreenerResult[]> {
  const response = await api.post<ScreenerResult[]>('/screen', criteria);
  return response.data;
}

// 获取所有股票（支持搜索）
export async function getAllStocks(q: string = ''): Promise<StockInfo[]> {
  const response = await api.get<StockInfo[]>('/stocks', { params: q ? { q } : {} });
  return response.data;
}

// 获取股票财务数据
export async function getStockFinancials(stockCode: string) {
  const response = await api.get(`/stocks/${stockCode}/financials`);
  return response.data;
}

// 获取股票价格数据
export async function getStockPrices(stockCode: string) {
  const response = await api.get(`/stocks/${stockCode}/prices`);
  return response.data;
}

// 运行回测
export async function runBacktest(
  stockCodes: string[], 
  config: BacktestConfig
): Promise<BacktestResponse> {
  const response = await api.post<BacktestResponse>('/backtest', stockCodes, {
    params: config,
    paramsSerializer: { indexes: null },
    timeout: 300000,  // 回测可能较慢，超时延长到 5 分钟
  });
  return response.data;
}

// 流式回测（每 30 只推送一次中间结果）
export async function runBacktestStream(
  stockCodes: string[],
  config: BacktestConfig,
  onChunk: (chunk: BacktestChunk) => void
): Promise<void> {
  const params = new URLSearchParams({
    dip_threshold: String(config.dip_threshold),
    profit_target:  String(config.profit_target),
    lookback_period: String(config.lookback_period),
  });

  const response = await fetch(`/api/backtest/stream?${params}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(stockCodes),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`回测失败: ${response.status} ${text}`);
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';
    for (const line of lines) {
      if (line.trim()) onChunk(JSON.parse(line) as BacktestChunk);
    }
  }
  // 处理最后可能剩余的内容
  if (buffer.trim()) onChunk(JSON.parse(buffer) as BacktestChunk);
}

// 优化策略
export async function optimizeStrategy(
  stockCodes: string[], 
  config: BacktestConfig
): Promise<OptimizationResult> {
  const response = await api.post<OptimizationResult>('/optimize', stockCodes, {
    params: config,
    paramsSerializer: { indexes: null },
    timeout: 300000,  // 同上
  });
  return response.data;
}

// 查询当前回测交易记录（分页 + 多维度筛选）
export async function getBacktestTrades(
  filters: Partial<TradeFilters> & { page?: number; pageSize?: number } = {}
): Promise<PaginatedTradesResponse> {
  const response = await api.get<PaginatedTradesResponse>('/backtest/trades', {
    params: {
      page:       filters.page      ?? 1,
      page_size:  filters.pageSize  ?? 50,
      stock_code: filters.stockCode ?? '',
      market:     filters.market    ?? '',
      holding:    filters.holdingOnly ?? false,
      exclude_kcb: filters.excludeKcb ?? false,
    },
  });
  return response.data;
}

// 获取累计收益率曲线数据
export async function getBacktestProfitCurve(
  filters: Partial<TradeFilters> = {}
): Promise<ProfitCurvePoint[]> {
  const response = await api.get<ProfitCurvePoint[]>('/backtest/profit-curve', {
    params: {
      stock_code:  filters.stockCode  ?? '',
      market:      filters.market     ?? '',
      exclude_kcb: filters.excludeKcb ?? false,
    },
  });
  return response.data;
}

// RL / 贝叶斯参数优化训练
export async function runRLTrain(
  stockCodes: string[],
  config: RLTrainConfig,
  onTrial: (result: RLTrialResult) => void
): Promise<void> {
  const params = new URLSearchParams({
    n_trials:         String(config.n_trials),
    stocks_per_trial: String(config.stocks_per_trial),
    lookback_period:  String(config.lookback_period),
  });

  const response = await fetch(`/api/rl/train?${params}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(stockCodes),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`RL训练失败: ${response.status} ${text}`);
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';
    for (const line of lines) {
      if (line.trim()) onTrial(JSON.parse(line) as RLTrialResult);
    }
  }
  if (buffer.trim()) onTrial(JSON.parse(buffer) as RLTrialResult);
}

// 同步股票基本面数据（PE/PB/市值/夏普率）
export async function syncStockInfo(
  maxStocks: number = 0
): Promise<{ total: number; success: number; failed: number }> {
  const response = await api.post('/sync-stock-info', null, {
    params: { max_stocks: maxStocks, years: 3, delay: 0.3 },
    timeout: 1800000,  // 全量同步最长 30 分钟
  });
  return response.data;
}

// 初始化演示数据
export async function initDemoData(): Promise<void> {
  await api.post('/init-data');
}

// 增量同步价格数据（流式）
export async function syncPriceData(
  onProgress: (p: PriceSyncProgress) => void
): Promise<void> {
  const response = await fetch('/api/sync-price-data');
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`同步失败: ${response.status} ${text}`);
  }
  const reader  = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';
    for (const line of lines) {
      if (line.trim()) onProgress(JSON.parse(line) as PriceSyncProgress);
    }
  }
  if (buffer.trim()) onProgress(JSON.parse(buffer) as PriceSyncProgress);
}

export default api;
