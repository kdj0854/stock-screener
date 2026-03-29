import { useState, useEffect, useRef } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import type { BacktestConfig, BacktestResponse, BacktestProgress, TradeFilters, PaginatedTradesResponse, ProfitCurvePoint } from '../types';
import { getBacktestTrades, getBacktestProfitCurve } from '../services/api';

const PAGE_SIZE = 50;

const MARKET_LABELS: Record<string, string> = {
  SH: '上证',
  SZ: '深圳',
  CYB: '创业板',
  OTHER: '其他',
};

interface Props {
  onBacktest: (config: BacktestConfig) => void;
  result: BacktestResponse | null;
  loading: boolean;
  progress?: BacktestProgress | null;
  selectedCount?: number;
}

export default function BacktestPanel({ onBacktest, result, loading, progress, selectedCount = 0 }: Props) {
  const [config, setConfig] = useState<BacktestConfig>({
    dip_threshold: 0.3,
    profit_target: 0.1,
    lookback_period: 120
  });

  // —— DB 交易记录分页状态 ——
  const defaultFilters: TradeFilters = { stockCode: '', market: '', holdingOnly: false, excludeKcb: true };
  const [tradeFilters, setTradeFilters]   = useState<TradeFilters>(defaultFilters);
  const [draftFilters, setDraftFilters]   = useState<TradeFilters>(defaultFilters); // 用户正在编辑中的内容
  const [tradePage,   setTradePage]       = useState(1);
  const [tradeData,   setTradeData]       = useState<PaginatedTradesResponse | null>(null);
  const [tradeLoading, setTradeLoading]   = useState(false);
  const [curveData, setCurveData]         = useState<ProfitCurvePoint[]>([]);
  const prevLoadingRef = useRef(false);

  const fetchTrades = async (page: number, filters: TradeFilters) => {
    setTradeLoading(true);
    try {
      const data = await getBacktestTrades({ page, pageSize: PAGE_SIZE, ...filters });
      setTradeData(data);
      setTradePage(page);
      setTradeFilters(filters);
    } catch {
      // 静默失败
    }
    setTradeLoading(false);
  };

  const fetchCurve = async (filters: TradeFilters) => {
    try {
      const data = await getBacktestProfitCurve(filters);
      setCurveData(data);
    } catch {
      // 静默失败
    }
  };

  // 页面加载时初始查询一次
  useEffect(() => { fetchTrades(1, defaultFilters); fetchCurve(defaultFilters); }, []); // eslint-disable-line

  // 回测完成后自动刷新到第一页
  useEffect(() => {
    if (prevLoadingRef.current && !loading) {
      setDraftFilters(defaultFilters);
      fetchTrades(1, defaultFilters);
      fetchCurve(defaultFilters);
    }
    prevLoadingRef.current = loading;
  }, [loading]); // eslint-disable-line

  const handleSearch = () => { fetchTrades(1, draftFilters); fetchCurve(draftFilters); };
  const handlePageChange = (p: number) => fetchTrades(p, tradeFilters);
  const totalPages = tradeData ? Math.ceil(tradeData.total / PAGE_SIZE) : 0;

  const handleSubmit = () => { onBacktest(config); };

  return (
    <div className="space-y-6">
      {/* 回测配置 */}
      <div className="card">
        <div className="card-header">
          <h2 className="font-semibold text-slate-800">回测配置</h2>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                跌买阈值 (%)
              </label>
              <input
                type="number"
                value={config.dip_threshold * 100}
                onChange={e => setConfig({ ...config, dip_threshold: Number(e.target.value) / 100 })}
                className="input"
                min="0"
                max="100"
              />
              <p className="mt-1 text-xs text-slate-500">
                股价从半年高点下跌 {(config.dip_threshold * 100).toFixed(0)}% 时买入
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                盈利目标 (%)
              </label>
              <input
                type="number"
                value={config.profit_target * 100}
                onChange={e => setConfig({ ...config, profit_target: Number(e.target.value) / 100 })}
                className="input"
                min="0"
                max="100"
              />
              <p className="mt-1 text-xs text-slate-500">
                盈利 {(config.profit_target * 100).toFixed(0)}% 时卖出
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                回溯周期 (天)
              </label>
              <input
                type="number"
                value={config.lookback_period}
                onChange={e => setConfig({ ...config, lookback_period: Number(e.target.value) })}
                className="input"
                min="30"
                max="365"
              />
              <p className="mt-1 text-xs text-slate-500">
                计算过去 {config.lookback_period} 天的最高价
              </p>
            </div>
          </div>
          <div className="mt-4 flex items-center gap-3">
            <button
              onClick={handleSubmit}
              disabled={loading}
              className="btn btn-success"
            >
              {loading ? '回测中...' : '运行回测'}
            </button>
            {!loading && (
              <span className="text-sm text-slate-500">
                {selectedCount > 0
                  ? `已选 ${selectedCount} 只股票`
                  : <span className="text-orange-500">请先在左侧勾选股票</span>
                }
              </span>
            )}
          </div>

          {/* 进度条（流式回测时显示） */}
          {loading && progress && (
            <div className="mt-4">
              <div className="flex justify-between text-sm text-slate-600 mb-1">
                <span>正在回测...</span>
                <span>{progress.current} / {progress.total} 只</span>
              </div>
              <div className="w-full bg-slate-200 rounded-full h-2">
                <div
                  className="bg-primary-500 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${Math.round(progress.current / progress.total * 100)}%` }}
                />
              </div>
              <p className="text-xs text-slate-400 mt-1">
                已处理 {progress.current} 只，共 {progress.total} 只——结果实时刷新
              </p>
            </div>
          )}
        </div>
      </div>

      {/* 回测结果 */}
      {result && (
        <>
          {/* 统计摘要 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="card">
              <div className="card-body text-center">
                <div className="text-2xl font-bold text-primary-600">
                  {result.summary.total_trades}
                </div>
                <div className="text-sm text-slate-500">总交易次数</div>
              </div>
            </div>
            <div className="card">
              <div className="card-body text-center">
                <div className="text-2xl font-bold text-success-500">
                  {(result.summary.win_rate * 100).toFixed(1)}%
                </div>
                <div className="text-sm text-slate-500">胜率</div>
              </div>
            </div>
            <div className="card">
              <div className="card-body text-center">
                <div className={`text-2xl font-bold ${result.summary.avg_profit_rate >= 0 ? 'text-success-500' : 'text-danger-500'}`}>
                  {(result.summary.avg_profit_rate * 100).toFixed(2)}%
                </div>
                <div className="text-sm text-slate-500">平均收益率</div>
              </div>
            </div>
            <div className="card">
              <div className="card-body text-center">
                <div className="text-2xl font-bold text-slate-700">
                  {result.summary.winning_trades} / {result.summary.losing_trades}
                </div>
                <div className="text-sm text-slate-500">盈利/亏损笔数</div>
              </div>
            </div>
          </div>

          {/* 分析率分析 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="card">
              <div className="card-header">
                <h3 className="font-semibold text-slate-800">买点分析率分析</h3>
              </div>
              <div className="card-body">
                <div className="text-center">
                  <div className="text-3xl font-bold text-warning-600">
                    {(result.summary.avg_entry_inefficiency * 100).toFixed(2)}%
                  </div>
                  <p className="text-sm text-slate-500 mt-2">
                    平均买价比实际最低价高
                  </p>
                  <p className="text-xs text-slate-400 mt-1">
                    数值越小说明买點越接近底部
                  </p>
                </div>
              </div>
            </div>
            <div className="card">
              <div className="card-header">
                <h3 className="font-semibold text-slate-800">卖点分析率分析</h3>
              </div>
              <div className="card-body">
                <div className="text-center">
                  <div className="text-3xl font-bold text-warning-600">
                    {(result.summary.avg_exit_inefficiency * 100).toFixed(2)}%
                  </div>
                  <p className="text-sm text-slate-500 mt-2">
                    平均卖价比实际最高价低
                  </p>
                  <p className="text-xs text-slate-400 mt-1">
                    数值越小说明卖点越接近顶部
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* 累计收益率曲线 */}
          {curveData.length > 0 && (
            <div className="card">
              <div className="card-header">
                <h3 className="font-semibold text-slate-800">累计收益率曲线</h3>
                <span className="text-xs text-slate-400">共 {curveData.length} 个交易日，每笔止盈收益率累计和</span>
              </div>
              <div className="card-body">
                <ResponsiveContainer width="100%" height={280}>
                  <LineChart data={curveData} margin={{ top: 4, right: 16, left: 8, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis
                      dataKey="date"
                      stroke="#64748b"
                      fontSize={11}
                      tickFormatter={v => v.slice(0, 7)}
                      interval={Math.floor(curveData.length / 8)}
                    />
                    <YAxis
                      stroke="#64748b"
                      fontSize={11}
                      tickFormatter={v => `${v.toFixed(0)}%`}
                    />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#fff', border: '1px solid #e2e8f0', borderRadius: '8px' }}
                      formatter={(value: number, name: string) => [
                        `${value.toFixed(2)}%`,
                        name === 'cumulative' ? '累计收益率' : '当日收益率',
                      ]}
                      labelFormatter={label => `日期: ${label}`}
                    />
                    <ReferenceLine y={0} stroke="#94a3b8" strokeDasharray="4 2" />
                    <Line
                      type="monotone"
                      dataKey="cumulative"
                      stroke={curveData[curveData.length - 1]?.cumulative >= 0 ? '#10b981' : '#ef4444'}
                      dot={false}
                      strokeWidth={2}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* 收益率分布图表（从 DB 当前页数据生成） */}
          {tradeData && tradeData.trades.length > 0 && (
            <div className="card">
              <div className="card-header">
                <h3 className="font-semibold text-slate-800">收益率分布（当前页）</h3>
              </div>
              <div className="card-body">
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={tradeData.trades.map(t => ({
                    name: t.stock_code,
                    收益率: +((t.profit_rate || 0) * 100).toFixed(2),
                  }))}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="name" stroke="#64748b" fontSize={11} />
                    <YAxis stroke="#64748b" fontSize={11} />
                    <Tooltip contentStyle={{ backgroundColor: '#fff', border: '1px solid #e2e8f0', borderRadius: '8px' }} />
                    <Bar dataKey="收益率" fill="#10b981" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* 交易明细：DB 分页查询 */}
          <div className="card">
            <div className="card-header flex flex-wrap items-center justify-between gap-2">
              <h3 className="font-semibold text-slate-800">交易记录</h3>
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <input type="text" placeholder="股票代码" value={draftFilters.stockCode}
                  onChange={e => setDraftFilters(f => ({ ...f, stockCode: e.target.value }))}
                  className="input w-24 text-sm" />
                <select value={draftFilters.market}
                  onChange={e => setDraftFilters(f => ({ ...f, market: e.target.value }))}
                  className="input w-28 text-sm">
                  <option value="">全部板块</option>
                  <option value="SH">上证</option>
                  <option value="SZ">深圳主板</option>
                  <option value="CYB">创业板</option>
                </select>
                <label className="flex items-center gap-1 cursor-pointer">
                  <input type="checkbox" checked={draftFilters.holdingOnly}
                    onChange={e => setDraftFilters(f => ({ ...f, holdingOnly: e.target.checked }))}
                    className="rounded border-slate-300 text-primary-600" />
                  <span>仅持仓中</span>
                </label>
                <label className="flex items-center gap-1 cursor-pointer">
                  <input type="checkbox" checked={draftFilters.excludeKcb}
                    onChange={e => setDraftFilters(f => ({ ...f, excludeKcb: e.target.checked }))}
                    className="rounded border-slate-300 text-primary-600" />
                  <span>排除科创板</span>
                </label>
                <button onClick={handleSearch} disabled={tradeLoading}
                  className="btn btn-primary text-xs px-3 py-1.5">查询</button>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="table-header">
                    <th className="table-cell text-left">股票</th>
                    <th className="table-cell text-left">板块</th>
                    <th className="table-cell text-left">买入日期</th>
                    <th className="table-cell text-right">买入价</th>
                    <th className="table-cell text-left">卖出日期</th>
                    <th className="table-cell text-right">卖出价</th>
                    <th className="table-cell text-right">收益率</th>
                    <th className="table-cell text-right">买点分析率</th>
                    <th className="table-cell text-right">卖点分析率</th>
                  </tr>
                </thead>
                <tbody>
                  {tradeLoading && (
                    <tr><td colSpan={9} className="table-cell text-center text-slate-400 py-6">加载中...</td></tr>
                  )}
                  {!tradeLoading && tradeData?.trades.map((trade, idx) => (
                    <tr key={idx} className={`table-row ${!trade.sell_date ? 'bg-blue-50' : ''}`}>
                      <td className="table-cell">
                        <div className="font-medium">{trade.stock_code}</div>
                        <div className="text-xs text-slate-500">{trade.stock_name}</div>
                      </td>
                      <td className="table-cell">
                        {trade.market && (
                          <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                            trade.market === 'SH'  ? 'bg-red-100 text-red-700' :
                            trade.market === 'CYB' ? 'bg-purple-100 text-purple-700' :
                            'bg-sky-100 text-sky-700'
                          }`}>{MARKET_LABELS[trade.market] ?? trade.market}</span>
                        )}
                      </td>
                      <td className="table-cell">{trade.buy_date}</td>
                      <td className="table-cell text-right">{trade.buy_price.toFixed(2)}</td>
                      <td className="table-cell">
                        {trade.sell_date
                          ? trade.sell_date
                          : <span className="text-xs font-medium text-blue-600 bg-blue-100 px-1.5 py-0.5 rounded">持仓中</span>
                        }
                        {trade.close_reason === 'timeout' && (
                          <span className="ml-1 text-xs font-medium text-orange-600 bg-orange-100 px-1.5 py-0.5 rounded">超期</span>
                        )}
                      </td>
                      <td className="table-cell text-right">{trade.sell_price?.toFixed(2) || '-'}</td>
                      <td className={`table-cell text-right font-medium ${
                        (trade.profit_rate || 0) >= 0 ? 'text-success-500' : 'text-danger-500'
                      }`}>
                        {trade.profit_rate != null
                          ? `${(trade.profit_rate * 100).toFixed(2)}%${!trade.sell_date ? ' (浮)' : ''}`
                          : '-'}
                      </td>
                      <td className="table-cell text-right">
                        {trade.entry_inefficiency ? `${(trade.entry_inefficiency * 100).toFixed(2)}%` : '-'}
                      </td>
                      <td className="table-cell text-right">
                        {trade.exit_inefficiency ? `${(trade.exit_inefficiency * 100).toFixed(2)}%` : '-'}
                      </td>
                    </tr>
                  ))}
                  {!tradeLoading && (!tradeData || tradeData.trades.length === 0) && (
                    <tr><td colSpan={9} className="table-cell text-center text-slate-500 py-8">暂无交易记录</td></tr>
                  )}
                </tbody>
              </table>
            </div>
            {/* 分页控制 */}
            {tradeData && tradeData.total > 0 && (
              <div className="px-4 py-3 border-t border-slate-200 flex items-center justify-between text-sm text-slate-600">
                <span>共 {tradeData.total} 条记录，第 {tradePage} 页 / 共 {totalPages} 页</span>
                <div className="flex gap-2">
                  <button onClick={() => handlePageChange(tradePage - 1)}
                    disabled={tradePage <= 1 || tradeLoading}
                    className="btn btn-secondary text-xs px-3 py-1.5 disabled:opacity-40">上一页</button>
                  <button onClick={() => handlePageChange(tradePage + 1)}
                    disabled={tradePage >= totalPages || tradeLoading}
                    className="btn btn-secondary text-xs px-3 py-1.5 disabled:opacity-40">下一页</button>
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {/* 无回测结果时也展示 DB 查询入口 */}
      {!result && (
        <div className="card">
          <div className="card-header flex flex-wrap items-center justify-between gap-2">
            <h3 className="font-semibold text-slate-800">交易记录查询</h3>
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <input type="text" placeholder="股票代码" value={draftFilters.stockCode}
                onChange={e => setDraftFilters(f => ({ ...f, stockCode: e.target.value }))}
                className="input w-24 text-sm" />
              <select value={draftFilters.market}
                onChange={e => setDraftFilters(f => ({ ...f, market: e.target.value }))}
                className="input w-28 text-sm">
                <option value="">全部板块</option>
                <option value="SH">上证</option>
                <option value="SZ">深圳主板</option>
                <option value="CYB">创业板</option>
              </select>
              <label className="flex items-center gap-1 cursor-pointer">
                <input type="checkbox" checked={draftFilters.holdingOnly}
                  onChange={e => setDraftFilters(f => ({ ...f, holdingOnly: e.target.checked }))}
                  className="rounded border-slate-300 text-primary-600" />
                <span>仅持仓中</span>
              </label>
              <label className="flex items-center gap-1 cursor-pointer">
                <input type="checkbox" checked={draftFilters.excludeKcb}
                  onChange={e => setDraftFilters(f => ({ ...f, excludeKcb: e.target.checked }))}
                  className="rounded border-slate-300 text-primary-600" />
                <span>排除科创板</span>
              </label>
              <button onClick={handleSearch} disabled={tradeLoading}
                className="btn btn-primary text-xs px-3 py-1.5">查询</button>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="table-header">
                  <th className="table-cell text-left">股票</th>
                  <th className="table-cell text-left">板块</th>
                  <th className="table-cell text-left">买入日期</th>
                  <th className="table-cell text-right">买入价</th>
                  <th className="table-cell text-left">卖出日期</th>
                  <th className="table-cell text-right">卖出价</th>
                  <th className="table-cell text-right">收益率</th>
                  <th className="table-cell text-right">买点分析率</th>
                  <th className="table-cell text-right">卖点分析率</th>
                </tr>
              </thead>
              <tbody>
                {tradeLoading && (
                  <tr><td colSpan={9} className="table-cell text-center text-slate-400 py-6">加载中...</td></tr>
                )}
                {!tradeLoading && tradeData?.trades.map((trade, idx) => (
                  <tr key={idx} className={`table-row ${!trade.sell_date ? 'bg-blue-50' : ''}`}>
                    <td className="table-cell">
                      <div className="font-medium">{trade.stock_code}</div>
                      <div className="text-xs text-slate-500">{trade.stock_name}</div>
                    </td>
                    <td className="table-cell">
                      {trade.market && (
                        <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                          trade.market === 'SH'  ? 'bg-red-100 text-red-700' :
                          trade.market === 'CYB' ? 'bg-purple-100 text-purple-700' :
                          'bg-sky-100 text-sky-700'
                        }`}>{MARKET_LABELS[trade.market] ?? trade.market}</span>
                      )}
                    </td>
                    <td className="table-cell">{trade.buy_date}</td>
                    <td className="table-cell text-right">{trade.buy_price.toFixed(2)}</td>
                    <td className="table-cell">
                      {trade.sell_date
                        ? trade.sell_date
                        : <span className="text-xs font-medium text-blue-600 bg-blue-100 px-1.5 py-0.5 rounded">持仓中</span>
                      }
                      {trade.close_reason === 'timeout' && (
                        <span className="ml-1 text-xs font-medium text-orange-600 bg-orange-100 px-1.5 py-0.5 rounded">超期</span>
                      )}
                    </td>
                    <td className="table-cell text-right">{trade.sell_price?.toFixed(2) || '-'}</td>
                    <td className={`table-cell text-right font-medium ${
                      (trade.profit_rate || 0) >= 0 ? 'text-success-500' : 'text-danger-500'
                    }`}>
                      {trade.profit_rate != null
                        ? `${(trade.profit_rate * 100).toFixed(2)}%${!trade.sell_date ? ' (浮)' : ''}`
                        : '-'}
                    </td>
                    <td className="table-cell text-right">
                      {trade.entry_inefficiency ? `${(trade.entry_inefficiency * 100).toFixed(2)}%` : '-'}
                    </td>
                    <td className="table-cell text-right">
                      {trade.exit_inefficiency ? `${(trade.exit_inefficiency * 100).toFixed(2)}%` : '-'}
                    </td>
                  </tr>
                ))}
                {!tradeLoading && (!tradeData || tradeData.trades.length === 0) && (
                  <tr><td colSpan={9} className="table-cell text-center text-slate-500 py-8">暂无交易记录</td></tr>
                )}
              </tbody>
            </table>
          </div>
          {/* 分页控制 */}
          {tradeData && tradeData.total > 0 && (
            <div className="px-4 py-3 border-t border-slate-200 flex items-center justify-between text-sm text-slate-600">
              <span>共 {tradeData.total} 条记录，第 {tradePage} 页 / 共 {totalPages} 页</span>
              <div className="flex gap-2">
                <button onClick={() => handlePageChange(tradePage - 1)}
                  disabled={tradePage <= 1 || tradeLoading}
                  className="btn btn-secondary text-xs px-3 py-1.5 disabled:opacity-40">上一页</button>
                <button onClick={() => handlePageChange(tradePage + 1)}
                  disabled={tradePage >= totalPages || tradeLoading}
                  className="btn btn-secondary text-xs px-3 py-1.5 disabled:opacity-40">下一页</button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
