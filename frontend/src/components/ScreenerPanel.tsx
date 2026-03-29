import { useState } from 'react';
import { screenStocks, syncPriceData, syncStockInfo } from '../services/api';
import type { ScreenerCriteria, ScreenerResult, PriceSyncProgress } from '../types';

interface Props {
  onComplete: (results: ScreenerResult[]) => void;
  initialResults: ScreenerResult[];
}

export default function ScreenerPanel({ onComplete, initialResults }: Props) {
  // 用字符串暂存输入，避免清空时被立即重置为 0
  const [form, setForm] = useState({
    min_pe: '0',
    max_pe: '30',
    max_market_cap: '60',
    pe_years: '3',
  });
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<ScreenerResult[]>(initialResults);
  const [syncing, setSyncing]       = useState(false);
  const [syncProg, setSyncProg]     = useState<PriceSyncProgress | null>(null);
  const [syncDone, setSyncDone]     = useState(false);
  const [fundaSyncing, setFundaSyncing] = useState(false);
  const [fundaResult, setFundaResult]   = useState<{ success: number; total: number } | null>(null);

  const handleRefresh = async () => {
    setSyncing(true);
    setSyncDone(false);
    setSyncProg(null);
    try {
      await syncPriceData(p => {
        setSyncProg(p);
        if (p.done) { setSyncing(false); setSyncDone(true); }
      });
    } catch (err) {
      console.error('data refresh failed:', err);
      setSyncing(false);
    }
  };

  const handleSyncFunda = async () => {
    setFundaSyncing(true);
    setFundaResult(null);
    try {
      const res = await syncStockInfo(0);
      setFundaResult({ success: res.success, total: res.total });
    } catch (err) {
      console.error('sync stock info failed:', err);
    } finally {
      setFundaSyncing(false);
    }
  };

  const handleScreener = async () => {
    setLoading(true);
    try {
      const criteria: ScreenerCriteria = {
        min_pe:         parseFloat(form.min_pe)        || 0,
        max_pe:         parseFloat(form.max_pe)        || 30,
        max_market_cap: parseFloat(form.max_market_cap)|| 60,
        pe_years:       parseInt(form.pe_years)        || 3,
      };
      const data = await screenStocks(criteria);
      setResults(data);
      onComplete(data);
    } catch (error) {
      console.error('筛选失败:', error);
    }
    setLoading(false);
  };

  return (
    <div className="space-y-6">
      {/* 筛选条件卡片 */}
      <div className="card">
        <div className="card-header">
          <h2 className="font-semibold text-slate-800">筛选条件</h2>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                最小市盈率 (PE)
              </label>
              <input
                type="number"
                value={form.min_pe}
                onChange={e => setForm({ ...form, min_pe: e.target.value })}
                className="input"
                min="0"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                最大市盈率 (PE)
              </label>
              <input
                type="number"
                value={form.max_pe}
                onChange={e => setForm({ ...form, max_pe: e.target.value })}
                className="input"
                min="0"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                最大市值 (亿元)
              </label>
              <input
                type="number"
                value={form.max_market_cap}
                onChange={e => setForm({ ...form, max_market_cap: e.target.value })}
                className="input"
                min="0"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                连续年数
              </label>
              <input
                type="number"
                value={form.pe_years}
                onChange={e => setForm({ ...form, pe_years: e.target.value })}
                className="input"
                min="1"
                max="5"
              />
              <p className="mt-1 text-xs text-slate-500">
                PE 需连续满足条件的年数（当年+历年）
              </p>
            </div>
          </div>
          <div className="mt-4 space-y-2">
            <div className="flex items-center gap-3">
              <button
                onClick={handleRefresh}
                disabled={syncing || loading || fundaSyncing}
                className="btn btn-secondary"
              >
                {syncing
                  ? `同步中 ${syncProg?.current ?? 0}/${syncProg?.total ?? '...'}`
                  : syncDone ? '已完成' : '数据刷新'}
              </button>
              <button
                onClick={handleSyncFunda}
                disabled={fundaSyncing || syncing || loading}
                className="btn btn-secondary"
              >
                {fundaSyncing ? '同步基本面中...' : fundaResult ? `完成 ${fundaResult.success}/${fundaResult.total}` : '同步基本面'}
              </button>
              <button
                onClick={handleScreener}
                disabled={loading || syncing || fundaSyncing}
                className="btn btn-primary"
              >
                {loading ? '筛选中...' : '开始筛选'}
              </button>
            </div>
            {syncing && syncProg && syncProg.total > 0 && (
              <div>
                <div className="w-full bg-slate-200 rounded-full h-1.5">
                  <div
                    className="bg-blue-500 h-1.5 rounded-full transition-all duration-200"
                    style={{ width: `${((syncProg.current / syncProg.total) * 100).toFixed(1)}%` }}
                  />
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  新增 {syncProg.added_total} 条 &middot; 当前: {syncProg.code}
                </p>
              </div>
            )}
            {syncDone && syncProg && (
              <p className="text-xs text-green-600">
                刷新完成，共新增 {syncProg.added_total} 条数据
              </p>
            )}
          </div>
        </div>
      </div>

      {/* 筛选结果 */}
      <div className="card">
        <div className="card-header flex justify-between items-center">
          <h2 className="font-semibold text-slate-800">筛选结果</h2>
          <span className="text-sm text-slate-500">
            共 {results.length} 只股票符合条件
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="table-header">
                <th className="table-cell text-left">代码</th>
                <th className="table-cell text-left">名称</th>
                <th className="table-cell text-left">行业</th>
                <th className="table-cell text-right">当年PE</th>
                <th className="table-cell text-right">去年PE</th>
                <th className="table-cell text-right">前年PE</th>
                <th className="table-cell text-right">市值(亿)</th>
              </tr>
            </thead>
            <tbody>
              {results.map(stock => (
                <tr key={stock.code} className="table-row">
                  <td className="table-cell font-medium">{stock.code}</td>
                  <td className="table-cell">{stock.name}</td>
                  <td className="table-cell">{stock.sector || '-'}</td>
                  <td className="table-cell text-right">
                    {stock.pe_current?.toFixed(2) || '-'}
                  </td>
                  <td className="table-cell text-right">
                    {stock.pe_year1?.toFixed(2) || '-'}
                  </td>
                  <td className="table-cell text-right">
                    {stock.pe_year2?.toFixed(2) || '-'}
                  </td>
                  <td className="table-cell text-right">
                    {stock.market_cap?.toFixed(2) || '-'}
                  </td>
                </tr>
              ))}
              {results.length === 0 && (
                <tr>
                  <td colSpan={7} className="table-cell text-center text-slate-500 py-8">
                    暂无筛选结果，请点击"开始筛选"
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
