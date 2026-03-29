import { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import type { BacktestConfig, OptimizationResult } from '../types';

interface Props {
  onOptimize: (config: BacktestConfig) => void;
  result: OptimizationResult | null;
  loading: boolean;
}

export default function OptimizationPanel({ onOptimize, result, loading }: Props) {
  const [config, setConfig] = useState<BacktestConfig>({
    dip_threshold: 0.3,
    profit_target: 0.1,
    lookback_period: 120
  });

  const handleSubmit = () => {
    onOptimize(config);
  };

  // 对比图表数据
  const comparisonData = result ? [
    {
      name: '交易次数',
      original: result.original_summary.total_trades,
      optimized: result.simulated_summary?.total_trades || 0,
    },
    {
      name: '胜率(%)',
      original: result.original_summary.win_rate * 100,
      optimized: (result.simulated_summary?.win_rate || 0) * 100,
    },
    {
      name: '平均收益(%)',
      original: result.original_summary.avg_profit_rate * 100,
      optimized: (result.simulated_summary?.avg_profit_rate || 0) * 100,
    },
  ] : [];

  return (
    <div className="space-y-6">
      {/* 优化配置 */}
      <div className="card">
        <div className="card-header">
          <h2 className="font-semibold text-slate-800">策略优化</h2>
        </div>
        <div className="card-body">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
            <h4 className="font-medium text-blue-800 mb-2">优化说明</h4>
            <ul className="text-sm text-blue-700 space-y-1">
              <li>• 分析买点分析率：实际买价比买后最低价高多少</li>
              <li>• 分析卖点分析率：卖价比买后最高价低多少</li>
              <li>• 根据分析率自动调整跌买阈値和盈利目标</li>
            </ul>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                当前跌买阈值 (%)
              </label>
              <input
                type="number"
                value={config.dip_threshold * 100}
                onChange={e => setConfig({ ...config, dip_threshold: Number(e.target.value) / 100 })}
                className="input"
                min="0"
                max="100"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                当前盈利目标 (%)
              </label>
              <input
                type="number"
                value={config.profit_target * 100}
                onChange={e => setConfig({ ...config, profit_target: Number(e.target.value) / 100 })}
                className="input"
                min="0"
                max="100"
              />
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
            </div>
          </div>
          <div className="mt-4">
            <button
              onClick={handleSubmit}
              disabled={loading}
              className="btn btn-primary"
            >
              {loading ? '优化中...' : '开始优化'}
            </button>
          </div>
        </div>
      </div>

      {/* 优化结果 */}
      {result && (
        <>
          {/* 优化建议 */}
          <div className="card">
            <div className="card-header">
              <h3 className="font-semibold text-slate-800">优化建议</h3>
            </div>
            <div className="card-body">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                <div className="bg-slate-50 rounded-lg p-4">
                  <div className="text-sm text-slate-500 mb-1">跌买阈值优化</div>
                  <div className="flex items-center justify-between">
                    <span className="text-lg font-semibold">
                      {(result.original_config.dip_threshold * 100).toFixed(0)}%
                    </span>
                    <span className="text-primary-600">→</span>
                    <span className="text-lg font-semibold text-success-600">
                      {(result.optimized_dip_threshold * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
                <div className="bg-slate-50 rounded-lg p-4">
                  <div className="text-sm text-slate-500 mb-1">盈利目标优化</div>
                  <div className="flex items-center justify-between">
                    <span className="text-lg font-semibold">
                      {(result.original_config.profit_target * 100).toFixed(0)}%
                    </span>
                    <span className="text-primary-600">→</span>
                    <span className="text-lg font-semibold text-success-600">
                      {(result.optimized_profit_target * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              </div>

              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <h4 className="font-medium text-yellow-800 mb-2">详细分析</h4>
                <pre className="text-sm text-yellow-700 whitespace-pre-wrap font-sans">
                  {result.recommendation}
                </pre>
              </div>
            </div>
          </div>

          {/* 效果对比图表 */}
          {comparisonData.length > 0 && (
            <div className="card">
              <div className="card-header">
                <h3 className="font-semibold text-slate-800">优化前后对比</h3>
              </div>
              <div className="card-body">
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={comparisonData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="name" stroke="#64748b" fontSize={12} />
                    <YAxis stroke="#64748b" fontSize={12} />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: '#fff', 
                        border: '1px solid #e2e8f0',
                        borderRadius: '8px'
                      }}
                    />
                    <Legend />
                    <Bar dataKey="original" name="优化前" fill="#94a3b8" />
                    <Bar dataKey="optimized" name="优化后" fill="#10b981" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* 详细对比表 */}
          <div className="card">
            <div className="card-header">
              <h3 className="font-semibold text-slate-800">指标对比</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="table-header">
                    <th className="table-cell text-left">指标</th>
                    <th className="table-cell text-right">优化前</th>
                    <th className="table-cell text-right">优化后</th>
                    <th className="table-cell text-right">变化</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="table-row">
                    <td className="table-cell font-medium">总交易次数</td>
                    <td className="table-cell text-right">{result.original_summary.total_trades}</td>
                    <td className="table-cell text-right">{result.simulated_summary?.total_trades || 0}</td>
                    <td className="table-cell text-right">
                      {result.simulated_summary && (
                        <span className={result.simulated_summary.total_trades >= result.original_summary.total_trades ? 'text-success-500' : 'text-danger-500'}>
                          {result.simulated_summary.total_trades - result.original_summary.total_trades}
                        </span>
                      )}
                    </td>
                  </tr>
                  <tr className="table-row">
                    <td className="table-cell font-medium">胜率</td>
                    <td className="table-cell text-right">{(result.original_summary.win_rate * 100).toFixed(2)}%</td>
                    <td className="table-cell text-right">{((result.simulated_summary?.win_rate || 0) * 100).toFixed(2)}%</td>
                    <td className="table-cell text-right">
                      {result.simulated_summary && (
                        <span className={(result.simulated_summary.win_rate - result.original_summary.win_rate) >= 0 ? 'text-success-500' : 'text-danger-500'}>
                          {((result.simulated_summary.win_rate - result.original_summary.win_rate) * 100).toFixed(2)}%
                        </span>
                      )}
                    </td>
                  </tr>
                  <tr className="table-row">
                    <td className="table-cell font-medium">平均收益率</td>
                    <td className="table-cell text-right">{(result.original_summary.avg_profit_rate * 100).toFixed(2)}%</td>
                    <td className="table-cell text-right">{((result.simulated_summary?.avg_profit_rate || 0) * 100).toFixed(2)}%</td>
                    <td className="table-cell text-right">
                      {result.simulated_summary && (
                        <span className={(result.simulated_summary.avg_profit_rate - result.original_summary.avg_profit_rate) >= 0 ? 'text-success-500' : 'text-danger-500'}>
                          {((result.simulated_summary.avg_profit_rate - result.original_summary.avg_profit_rate) * 100).toFixed(2)}%
                        </span>
                      )}
                    </td>
                  </tr>
                  <tr className="table-row">
                    <td className="table-cell font-medium">平均买点分析率</td>
                    <td className="table-cell text-right">{(result.original_summary.avg_entry_inefficiency * 100).toFixed(2)}%</td>
                    <td className="table-cell text-right">{((result.simulated_summary?.avg_entry_inefficiency || 0) * 100).toFixed(2)}%</td>
                    <td className="table-cell text-right">
                      {result.simulated_summary && (
                        <span className={(result.original_summary.avg_entry_inefficiency - result.simulated_summary.avg_entry_inefficiency) >= 0 ? 'text-success-500' : 'text-danger-500'}>
                          {((result.original_summary.avg_entry_inefficiency - result.simulated_summary.avg_entry_inefficiency) * 100).toFixed(2)}%
                        </span>
                      )}
                    </td>
                  </tr>
                  <tr className="table-row">
                    <td className="table-cell font-medium">平均卖点分析率</td>
                    <td className="table-cell text-right">{(result.original_summary.avg_exit_inefficiency * 100).toFixed(2)}%</td>
                    <td className="table-cell text-right">{((result.simulated_summary?.avg_exit_inefficiency || 0) * 100).toFixed(2)}%</td>
                    <td className="table-cell text-right">
                      {result.simulated_summary && (
                        <span className={(result.original_summary.avg_exit_inefficiency - result.simulated_summary.avg_exit_inefficiency) >= 0 ? 'text-success-500' : 'text-danger-500'}>
                          {((result.original_summary.avg_exit_inefficiency - result.simulated_summary.avg_exit_inefficiency) * 100).toFixed(2)}%
                        </span>
                      )}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
