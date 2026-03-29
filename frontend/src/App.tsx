import { useState, useEffect, useRef, useCallback } from 'react';
import { getAllStocks, runBacktestStream } from './services/api';
import type { ScreenerResult, BacktestConfig, BacktestResponse, StockInfo, BacktestProgress } from './types';
import ScreenerPanel from './components/ScreenerPanel';
import BacktestPanel from './components/BacktestPanel';
import RLPanel from './components/RLPanel';

type TabType = 'screener' | 'backtest' | 'rl';

function App() {
  const [activeTab, setActiveTab] = useState<TabType>('screener');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const msgTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 消息自动消失（成功3s，错误6s）
  const showMessage = useCallback((msg: { type: 'success' | 'error'; text: string }) => {
    setMessage(msg);
    if (msgTimerRef.current) clearTimeout(msgTimerRef.current);
    msgTimerRef.current = setTimeout(() => setMessage(null), msg.type === 'success' ? 3000 : 6000);
  }, []);
  const [stocks, setStocks] = useState<StockInfo[]>([]);
  const [stockSearch, setStockSearch] = useState('');
  const [stockPage, setStockPage] = useState(1);
  const STOCK_PAGE_SIZE = 20;
  const [screenerResults, setScreenerResults] = useState<ScreenerResult[]>([]);
  const [selectedStocks, setSelectedStocks] = useState<string[]>([]);
  const [backtestResult, setBacktestResult] = useState<BacktestResponse | null>(null);
  const [backtestProgress, setBacktestProgress] = useState<BacktestProgress | null>(null);
  const allTradesRef = useRef<BacktestResponse['trades']>([]);

  // 加载股票列表
  useEffect(() => {
    const loadStocks = async () => {
      try {
        const stockList = await getAllStocks();
        setStocks(stockList);
      } catch (error) {
        console.error('加载股票列表失败:', error);
      }
    };
    loadStocks();
  }, []);

  // 处理筛选结果
  const handleScreenerComplete = (results: ScreenerResult[]) => {
    setScreenerResults(results);
    // 自动选中筛选出的股票
    setSelectedStocks(results.map(r => r.code));
  };

  // 切换股票选择
  const handleStockToggle = (code: string) => {
    setSelectedStocks(prev => 
      prev.includes(code) 
        ? prev.filter(c => c !== code)
        : [...prev, code]
    );
  };

  // 全选/取消全选
  const handleSelectAll = () => {
    if (selectedStocks.length === stocks.length) {
      setSelectedStocks([]);
    } else {
      setSelectedStocks(stocks.map(s => s.code));
    }
  };

  // 运行流式回测
  const handleBacktest = async (config: BacktestConfig) => {
    if (selectedStocks.length === 0) {
      setMessage({ type: 'error', text: '请先选择股票' });
      return;
    }
    setLoading(true);
    setBacktestResult(null);
    setBacktestProgress(null);
    allTradesRef.current = [];
    try {
      await runBacktestStream(selectedStocks, config, (chunk) => {
        // 累加本批新入交易
        allTradesRef.current = [...allTradesRef.current, ...chunk.new_trades];
        setBacktestProgress(chunk.progress);
        setBacktestResult({
          config,
          summary: chunk.summary,
          trades: allTradesRef.current,
        });
      });
      const total = allTradesRef.current.length;
      showMessage({ type: 'success', text: `回测完成！共 ${total} 笔交易` });
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : '回测失败';
      showMessage({ type: 'error', text: msg });
    }
    setLoading(false);
    setBacktestProgress(null);
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* 顶部导航 */}
      <header className="bg-white shadow-sm border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-3">
              <svg className="w-8 h-8 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
              <h1 className="text-xl font-bold text-slate-800">股票筛选与策略回溯工具</h1>
            </div>
          </div>
        </div>
      </header>

      {/* 消息提示 */}
      {message && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-4">
          <div className={`p-4 rounded-lg flex items-start justify-between gap-2 ${
            message.type === 'success'
              ? 'bg-green-50 text-green-800 border border-green-200'
              : 'bg-red-50 text-red-800 border border-red-200'
          }`}>
            <span>{message.text}</span>
            <button
              onClick={() => setMessage(null)}
              className="ml-2 text-current opacity-50 hover:opacity-100 shrink-0 leading-none"
              aria-label="关闭"
            >✕</button>
          </div>
        </div>
      )}

      {/* 标签导航 */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-4">
        <div className="flex space-x-2 border-b border-slate-200">
          <button
            onClick={() => setActiveTab('screener')}
            className={`px-4 py-2 font-medium text-sm transition-colors ${
              activeTab === 'screener'
                ? 'text-primary-600 border-b-2 border-primary-600'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            股票筛选
          </button>
          <button
            onClick={() => setActiveTab('backtest')}
            className={`px-4 py-2 font-medium text-sm transition-colors ${
              activeTab === 'backtest'
                ? 'text-primary-600 border-b-2 border-primary-600'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            策略回测
          </button>
          <button
            onClick={() => setActiveTab('rl')}
            className={`px-4 py-2 font-medium text-sm transition-colors ${
              activeTab === 'rl'
                ? 'text-primary-600 border-b-2 border-primary-600'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            参数优化训练
          </button>
        </div>
      </div>

      {/* 主内容区 */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* 左侧股票列表 */}
          <div className="lg:col-span-1">
            <div className="card">
              <div className="card-header flex justify-between items-center">
                <h2 className="font-semibold text-slate-800">股票列表</h2>
                <span className="text-sm text-slate-500">{stocks.length}只</span>
              </div>
              {/* 搜索框 */}
              <div className="px-4 py-2 border-b border-slate-200">
                <input
                  type="text"
                  placeholder="搜索代码或名称..."
                  value={stockSearch}
                  onChange={e => { setStockSearch(e.target.value); setStockPage(1); }}
                  className="input text-sm w-full"
                />
              </div>
              <div className="px-4 py-2 border-b border-slate-200">
                <button
                  onClick={handleSelectAll}
                  className="text-sm text-primary-600 hover:text-primary-700"
                >
                  {selectedStocks.length === stocks.length ? '取消全选' : '全选'}
                </button>
                <span className="ml-2 text-sm text-slate-500">
                  已选 {selectedStocks.length} 只
                </span>
              </div>
              <div className="max-h-96 overflow-y-auto">
                {(() => {
                  const filtered = stocks.filter(s => !stockSearch || s.code.includes(stockSearch) || s.name.includes(stockSearch));
                  const totalPages = Math.max(1, Math.ceil(filtered.length / STOCK_PAGE_SIZE));
                  const curPage = Math.min(stockPage, totalPages);
                  const pageStocks = filtered.slice((curPage - 1) * STOCK_PAGE_SIZE, curPage * STOCK_PAGE_SIZE);
                  return (
                    <>
                      {pageStocks.map(stock => (
                        <label
                          key={stock.code}
                          className="flex items-center px-4 py-2 hover:bg-slate-50 cursor-pointer"
                        >
                          <input
                            type="checkbox"
                            checked={selectedStocks.includes(stock.code)}
                            onChange={() => handleStockToggle(stock.code)}
                            className="mr-3 rounded border-slate-300 text-primary-600 focus:ring-primary-500"
                          />
                          <div>
                            <div className="text-sm font-medium text-slate-800">{stock.code}</div>
                            <div className="text-xs text-slate-500">{stock.name}</div>
                          </div>
                        </label>
                      ))}
                      {stocks.length === 0 && (
                        <div className="p-4 text-center text-slate-500 text-sm">
                          暂无数据，请先点击「数据刷新」
                        </div>
                      )}
                      {filtered.length > STOCK_PAGE_SIZE && (
                        <div className="flex items-center justify-between px-4 py-2 border-t border-slate-200 bg-slate-50">
                          <button
                            onClick={() => setStockPage(p => Math.max(1, p - 1))}
                            disabled={curPage <= 1}
                            className="text-xs text-primary-600 hover:text-primary-700 disabled:text-slate-300"
                          >上一页</button>
                          <span className="text-xs text-slate-500">{curPage}/{totalPages}</span>
                          <button
                            onClick={() => setStockPage(p => Math.min(totalPages, p + 1))}
                            disabled={curPage >= totalPages}
                            className="text-xs text-primary-600 hover:text-primary-700 disabled:text-slate-300"
                          >下一页</button>
                        </div>
                      )}
                    </>
                  );
                })()}
              </div>
            </div>
          </div>

          {/* 右侧内容区 */}
          <div className="lg:col-span-3">
            {activeTab === 'screener' && (
              <ScreenerPanel 
                onComplete={handleScreenerComplete}
                initialResults={screenerResults}
              />
            )}
            {activeTab === 'backtest' && (
              <BacktestPanel 
                onBacktest={handleBacktest}
                result={backtestResult}
                loading={loading}
                progress={backtestProgress}
                selectedCount={selectedStocks.length}
              />
            )}
            {activeTab === 'rl' && (
              <RLPanel stockCodes={stocks.map(s => s.code)} />
            )}
          </div>
        </div>
      </main>

      {/* 页脚 */}
      <footer className="bg-white border-t border-slate-200 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <p className="text-center text-sm text-slate-500">
            股票筛选与策略回溯工具 - 仅供学习研究，不构成投资建议
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
