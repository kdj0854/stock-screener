import { useState } from 'react';
import {
  LineChart, Line, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, ReferenceLine,
} from 'recharts';
import type { RLTrainConfig, RLTrialResult } from '../types';
import { runRLTrain } from '../services/api';

interface Props {
  stockCodes: string[];
}

// 散点图自定义 dot：绿色=盈利，红色=亏损，金色三角=最优轮次
const ScatterDot = (bestTrial: number | null) => (props: Record<string, unknown>) => {
  const cx = props.cx as number;
  const cy = props.cy as number;
  const payload = props.payload as { reward: number; trial: number };
  const isBest = bestTrial !== null && payload.trial === bestTrial;
  if (isBest) {
    const pts = `${cx},${cy - 9} ${cx + 8},${cy + 5} ${cx - 8},${cy + 5}`;
    return <polygon points={pts} fill="#f59e0b" stroke="#fff" strokeWidth={1} />;
  }
  return (
    <circle
      cx={cx} cy={cy} r={4}
      fill={payload.reward >= 0 ? '#10b981' : '#ef4444'}
      fillOpacity={0.65}
    />
  );
};

export default function RLPanel({ stockCodes }: Props) {
  const [config, setConfig] = useState<RLTrainConfig>({
    n_trials: 30,
    stocks_per_trial: 50,
    lookback_period: 120,
  });
  const [training, setTraining]   = useState(false);
  const [trials,   setTrials]     = useState<RLTrialResult[]>([]);
  const [message,  setMessage]    = useState<string | null>(null);

  const handleStart = async () => {
    if (stockCodes.length === 0) {
      setMessage('暂无股票数据，请先在「股票筛选」界面执行「数据刷新」');
      return;
    }
    setTraining(true);
    setTrials([]);
    setMessage(null);
    try {
      await runRLTrain(stockCodes, config, (result) => {
        setTrials(prev => [...prev, result]);
      });
      setMessage('训练完成！');
    } catch (err) {
      setMessage(`训练失败: ${err instanceof Error ? err.message : '未知错误'}`);
    }
    setTraining(false);
  };

  const current  = trials[trials.length - 1];
  const bestTrial = trials.reduce<RLTrialResult | null>(
    (best, t) => !best || t.reward > best.reward ? t : best,
    null
  );

  // 奖励曲线数据（转换为万元）
  const rewardCurve = trials.map(t => ({
    trial:   t.trial,
    reward:  +(t.reward       / 10000).toFixed(2),
    best:    +(t.best_reward  / 10000).toFixed(2),
  }));

  // 散点数据
  const scatterData = trials.map(t => ({
    x:      t.dip_threshold,
    y:      t.profit_target,
    reward: t.reward,
    trial:  t.trial,
  }));

  return (
    <div className="space-y-6">
      {/* 训练配置 */}
      <div className="card">
        <div className="card-header">
          <h2 className="font-semibold text-slate-800">贝叶斯参数优化（RL 框架）</h2>
        </div>
        <div className="card-body">
          <p className="text-sm text-slate-500 mb-4">
            使用 Optuna TPE 采样器自动探索最优的「跌买阈值」和「盈利目标」组合。
            奖励函数 = Σ（平仓收益率 × 10万元），每轮在随机采样的股票池上运行回测。
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">训练轮次</label>
              <input
                type="number"
                value={config.n_trials}
                onChange={e => setConfig({ ...config, n_trials: +e.target.value })}
                className="input" min={5} max={10000} disabled={training}
              />
              <p className="text-xs text-slate-500 mt-1">每轮 = 一次完整回测，建议 30–100 轮</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">每轮采样股票数</label>
              <input
                type="number"
                value={config.stocks_per_trial}
                onChange={e => setConfig({ ...config, stocks_per_trial: +e.target.value })}
                className="input" min={0} disabled={training}
              />
              <p className="text-xs text-slate-500 mt-1">
                0 = 使用全部 {stockCodes.length} 只（较慢）
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">回溯周期（天）</label>
              <input
                type="number"
                value={config.lookback_period}
                onChange={e => setConfig({ ...config, lookback_period: +e.target.value })}
                className="input" min={30} max={365} disabled={training}
              />
              <p className="text-xs text-slate-500 mt-1">计算历史高点的时间窗口</p>
            </div>
          </div>

          <div className="mt-4">
            <button onClick={handleStart} disabled={training} className="btn btn-success">
              {training
                ? `训练中 ${current?.trial ?? 0} / ${config.n_trials}…`
                : '开始训练'}
            </button>
          </div>

          {/* 进度条 */}
          {training && current && (
            <div className="mt-3">
              <div className="w-full bg-slate-200 rounded-full h-2">
                <div
                  className="bg-primary-500 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${(current.trial / config.n_trials) * 100}%` }}
                />
              </div>
            </div>
          )}

          {message && (
            <p className={`mt-2 text-sm font-medium ${message.includes('失败') ? 'text-red-600' : 'text-green-600'}`}>
              {message}
            </p>
          )}
        </div>
      </div>

      {trials.length > 0 && (
        <>
          {/* 摘要卡片 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="card">
              <div className="card-body text-center">
                <div className="text-2xl font-bold text-primary-600">{trials.length}</div>
                <div className="text-sm text-slate-500">已完成轮次</div>
              </div>
            </div>
            <div className="card">
              <div className="card-body text-center">
                <div className={`text-2xl font-bold ${(bestTrial?.reward ?? 0) >= 0 ? 'text-success-500' : 'text-danger-500'}`}>
                  {bestTrial ? `${(bestTrial.reward / 10000).toFixed(2)}万` : '-'}
                </div>
                <div className="text-sm text-slate-500">最优总收益</div>
              </div>
            </div>
            <div className="card">
              <div className="card-body text-center">
                <div className="text-2xl font-bold text-warning-600">
                  {bestTrial ? `${(bestTrial.dip_threshold * 100).toFixed(1)}%` : '-'}
                </div>
                <div className="text-sm text-slate-500">最优跌买阈值</div>
              </div>
            </div>
            <div className="card">
              <div className="card-body text-center">
                <div className="text-2xl font-bold text-warning-600">
                  {bestTrial ? `${(bestTrial.profit_target * 100).toFixed(1)}%` : '-'}
                </div>
                <div className="text-sm text-slate-500">最优盈利目标</div>
              </div>
            </div>
          </div>

          {/* 奖励曲线 */}
          <div className="card">
            <div className="card-header">
              <h3 className="font-semibold text-slate-800">奖励曲线（万元）</h3>
            </div>
            <div className="card-body">
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={rewardCurve}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis
                    dataKey="trial"
                    stroke="#64748b" fontSize={11}
                    label={{ value: '轮次', position: 'insideBottomRight', offset: -5 }}
                  />
                  <YAxis stroke="#64748b" fontSize={11} tickFormatter={(v: number) => `${v}万`} />
                  <Tooltip
                    formatter={(v: number) => [`${v}万`, undefined]}
                    contentStyle={{ backgroundColor: '#fff', border: '1px solid #e2e8f0', borderRadius: '8px' }}
                  />
                  <Legend />
                  <ReferenceLine y={0} stroke="#94a3b8" strokeDasharray="4 2" />
                  <Line
                    type="monotone" dataKey="reward" name="本轮奖励"
                    stroke="#94a3b8" dot={false} strokeWidth={1.5}
                  />
                  <Line
                    type="monotone" dataKey="best" name="历史最优"
                    stroke="#10b981" dot={false} strokeWidth={2.5}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 参数探索散点图 */}
          <div className="card">
            <div className="card-header">
              <h3 className="font-semibold text-slate-800">
                参数探索空间
                <span className="ml-2 text-xs font-normal text-slate-500">
                  绿点=盈利 &nbsp;红点=亏损 &nbsp;▲=最优轮次
                </span>
              </h3>
            </div>
            <div className="card-body">
              <ResponsiveContainer width="100%" height={300}>
                <ScatterChart margin={{ top: 10, right: 30, bottom: 40, left: 40 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis
                    type="number" dataKey="x" name="跌买阈値"
                    domain={[0.05, 0.40]} stroke="#64748b" fontSize={10}
                    ticks={Array.from({length: 36}, (_, i) => +(0.05 + i * 0.01).toFixed(2))}
                    tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                    label={{ value: '跌买阈値', position: 'insideBottom', offset: -25 }}
                    interval={4}
                  />
                  <YAxis
                    type="number" dataKey="y" name="盈利目标"
                    domain={[0.01, 0.20]} stroke="#64748b" fontSize={10}
                    ticks={Array.from({length: 20}, (_, i) => +(0.01 + i * 0.01).toFixed(2))}
                    tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                    label={{ value: '盈利目标', angle: -90, position: 'insideLeft', offset: 10 }}
                    interval={0}
                  />
                  <Tooltip
                    cursor={{ strokeDasharray: '3 3' }}
                    content={({ payload }) => {
                      if (!payload?.length) return null;
                      const d = payload[0].payload as typeof scatterData[0];
                      return (
                        <div className="bg-white border border-slate-200 rounded p-2 text-xs shadow">
                          <p className="font-medium mb-1">第 {d.trial} 轮</p>
                          <p>跌买阈值：{(d.x * 100).toFixed(1)}%</p>
                          <p>盈利目标：{(d.y * 100).toFixed(1)}%</p>
                          <p className={d.reward >= 0 ? 'text-green-600 font-medium' : 'text-red-600 font-medium'}>
                            奖励：{(d.reward / 10000).toFixed(2)} 万元
                          </p>
                        </div>
                      );
                    }}
                  />
                  <Scatter
                    data={scatterData}
                    shape={ScatterDot(bestTrial?.trial ?? null) as unknown as React.ReactElement}
                  />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 训练历史表（最近 20 轮） */}
          <div className="card">
            <div className="card-header">
              <h3 className="font-semibold text-slate-800">训练历史（最近 20 轮）</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="table-header">
                    <th className="table-cell text-center">轮次</th>
                    <th className="table-cell text-right">跌买阈值</th>
                    <th className="table-cell text-right">盈利目标</th>
                    <th className="table-cell text-right">总奖励</th>
                    <th className="table-cell text-right">平仓笔数</th>
                    <th className="table-cell text-right">胜率</th>
                  </tr>
                </thead>
                <tbody>
                  {[...trials].reverse().slice(0, 20).map(t => (
                    <tr
                      key={t.trial}
                      className={`table-row ${bestTrial?.trial === t.trial ? 'bg-yellow-50 font-medium' : ''}`}
                    >
                      <td className="table-cell text-center">
                        {bestTrial?.trial === t.trial && (
                          <span className="mr-1 text-yellow-500">★</span>
                        )}
                        {t.trial}
                      </td>
                      <td className="table-cell text-right">
                        {(t.dip_threshold * 100).toFixed(1)}%
                      </td>
                      <td className="table-cell text-right">
                        {(t.profit_target * 100).toFixed(1)}%
                      </td>
                      <td className={`table-cell text-right ${t.reward >= 0 ? 'text-success-500' : 'text-danger-500'}`}>
                        {(t.reward / 10000).toFixed(2)} 万
                      </td>
                      <td className="table-cell text-right">{t.closed_trades}</td>
                      <td className="table-cell text-right">
                        {(t.win_rate * 100).toFixed(1)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
