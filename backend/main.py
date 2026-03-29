import json
import uuid
import random
import asyncio
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from datetime import date

from database import get_db, init_db, SessionLocal
from market_database import get_market_db, init_market_db, MarketSessionLocal
from models import BacktestTrade, BacktestTradeHistory, RLTrainingRun
from market_models import Stock
from schemas import (
    ScreenerCriteria, 
    ScreenerResult,
    BacktestConfig,
    BacktestResponse,
    OptimizationResult,
    BacktestSummary,
    PaginatedTradesResponse,
    TradeRecord
)
from services import (
    screen_stocks, 
    get_stock_financials,
    get_stock_prices,
    run_backtest,
    optimize_strategy
)
from services.backtest import backtest_single_stock, calculate_summary


def get_market(code: str) -> str:
    """根据股票代码判断板块"""
    if code.startswith('6'):
        return 'SH'   # 上证（主板 + 科创板）
    elif code.startswith('3'):
        return 'CYB'  # 创业板
    elif code.startswith('0') or code.startswith('2') or code.startswith('4'):
        return 'SZ'   # 深圳主板
    else:
        return 'OTHER'

# 创建 FastAPI 应用
app = FastAPI(
    title="股票筛选与策略回溯工具",
    description="A股价值投资筛选工具，支持市盈率筛选和策略回溯优化",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化两个数据库"""
    init_db()          # stock_data.db（回测记录）
    init_market_db()   # market_data.db（股票/财务数据）


# ========== 根路径 ==========

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "股票筛选与策略回溯工具 API",
        "version": "1.0.0",
        "docs": "/docs"
    }


# ========== 股票筛选 API ==========

@app.post("/api/screen", response_model=List[ScreenerResult])
async def screen_stocks_endpoint(
    criteria: ScreenerCriteria,
    db: Session = Depends(get_market_db)
):
    """
    筛选股票
    
    条件：
    - 市盈率连续N年小于阈值（默认30）
    - 当前市值小于阈值（默认60亿）
    """
    return screen_stocks(db, criteria)


@app.get("/api/stocks/{stock_code}/financials")
async def get_stock_financials_endpoint(
    stock_code: str,
    db: Session = Depends(get_market_db)
):
    """获取股票财务数据"""
    financials = get_stock_financials(db, stock_code)
    if not financials:
        raise HTTPException(status_code=404, detail="股票不存在或无财务数据")
    return financials


@app.get("/api/stocks/{stock_code}/prices")
async def get_stock_prices_endpoint(
    stock_code: str,
    db: Session = Depends(get_market_db)
):
    """获取股票价格数据"""
    prices = get_stock_prices(db, stock_code)
    if not prices:
        raise HTTPException(status_code=404, detail="股票不存在或无价格数据")
    return prices


@app.get("/api/stocks")
async def get_all_stocks(
    q: str = "",
    db: Session = Depends(get_market_db)
):
    """获取股票列表，可按代码/名称搜索"""
    query = db.query(Stock)
    if q:
        query = query.filter(
            (Stock.code.contains(q)) | (Stock.name.contains(q))
        )
    stocks = query.order_by(Stock.code).all()
    return [
        {
            "code": s.code,
            "name": s.name,
            "sector": s.sector
        }
        for s in stocks
    ]


# ========== 回测 API ==========

@app.post("/api/backtest", response_model=BacktestResponse)
async def backtest_endpoint(
    stock_codes: List[str],
    dip_threshold: float = Query(0.3, description="跌买阈值"),
    profit_target: float = Query(0.1, description="盈利目标"),
    lookback_period: int = Query(120, description="回溯周期(天)"),
    db: Session = Depends(get_market_db)
):
    """
    运行策略回测
    
    策略：
    - 跌买点：股价从过去N天最高点下跌超过阈值时买入
    - 赢利点：买入后盈利超过目标时卖出
    """
    if not stock_codes:
        raise HTTPException(status_code=400, detail="请提供股票代码列表")
    
    config = BacktestConfig(
        dip_threshold=dip_threshold,
        profit_target=profit_target,
        lookback_period=lookback_period
    )
    return run_backtest(db, stock_codes, config)


# ========== 流式回测 API（每 30 只推送一次中间结果） ==========

@app.post("/api/backtest/stream")
async def backtest_stream_endpoint(
    stock_codes: List[str],
    dip_threshold: float = Query(0.3, description="跌买阈値"),
    profit_target: float  = Query(0.1, description="盈利目标"),
    lookback_period: int  = Query(120, description="回溯周期(天)"),
):
    """流式回测：每处理完 30 只推送一次中间结果，并实时存入 DB"""
    if not stock_codes:
        raise HTTPException(status_code=400, detail="请提供股票代码列表")

    config = BacktestConfig(
        dip_threshold=dip_threshold,
        profit_target=profit_target,
        lookback_period=lookback_period,
    )

    async def generate():
        db = SessionLocal()
        try:
            # ① 将当前表全量迁入历史表（一条 SQL 批量操作，高效）
            db.execute(text("""
                INSERT INTO backtest_trades_history
                    (run_id, stock_code, stock_name, market, buy_date, buy_price,
                     sell_date, sell_price, profit_rate, lowest_after_buy, highest_after_buy,
                     entry_inefficiency, exit_inefficiency, close_reason, created_at, archived_at)
                SELECT run_id, stock_code, stock_name, market, buy_date, buy_price,
                       sell_date, sell_price, profit_rate, lowest_after_buy, highest_after_buy,
                       entry_inefficiency, exit_inefficiency, close_reason, created_at,
                       CURRENT_TIMESTAMP
                FROM backtest_trades_current
            """))
            db.execute(text("DELETE FROM backtest_trades_current"))
            db.commit()

            # ② 生成本次回测的唯一 run_id
            run_id     = str(uuid.uuid4())
            all_trades = []
            total      = len(stock_codes)
            batch_size = 30

            def process_batch(batch: List[str]):
                """\u5728\u7ebf\u7a0b\u6c60\u4e2d\u8fd0\u884c\uff08\u540c\u6b65\u963b\u585e\u64cd\u4f5c\uff09"""
                db2 = MarketSessionLocal()  # 市场库：查 Stock 名称/exchange
                try:
                    result = []
                    for code in batch:
                        result.extend(backtest_single_stock(db2, code, config))
                    return result
                finally:
                    db2.close()

            for i in range(0, total, batch_size):
                batch      = stock_codes[i: i + batch_size]
                new_trades = await asyncio.to_thread(process_batch, batch)
                all_trades.extend(new_trades)

                # ③ 本批交易存入当前表
                for trade in new_trades:
                    db.add(BacktestTrade(
                        run_id             = run_id,
                        stock_code         = trade.stock_code,
                        stock_name         = trade.stock_name,
                        market             = get_market(trade.stock_code),
                        buy_date           = trade.buy_date,
                        buy_price          = trade.buy_price,
                        sell_date          = trade.sell_date,
                        sell_price         = trade.sell_price,
                        profit_rate        = trade.profit_rate,
                        lowest_after_buy   = trade.lowest_after_buy,
                        highest_after_buy  = trade.highest_after_buy,
                        entry_inefficiency = trade.entry_inefficiency,
                        exit_inefficiency  = trade.exit_inefficiency,
                        close_reason       = trade.close_reason,
                    ))
                db.commit()

                current = min(i + batch_size, total)
                summary = calculate_summary(all_trades)

                chunk = {
                    "progress":   {"current": current, "total": total},
                    "summary":    summary.model_dump(),
                    "new_trades": [t.model_dump(mode="json") for t in new_trades],
                    "done":       current >= total,
                }
                yield json.dumps(chunk) + "\n"
        finally:
            db.close()

    return StreamingResponse(generate(), media_type="application/x-ndjson")


# ========== 回测交易分页查询 API ==========

@app.get("/api/backtest/trades", response_model=PaginatedTradesResponse)
async def get_backtest_trades(
    page:       int  = Query(1,    ge=1, description="页码"),
    page_size:  int  = Query(50,   ge=1, le=200, description="每页条数"),
    stock_code:  str  = Query("",    description="按股票代码模糊查询"),
    market:      str  = Query("",    description="板块: SH/SZ/CYB"),
    holding:     bool = Query(False, description="仅返回当前持仓中的记录"),
    exclude_kcb: bool = Query(False, description="排除科创板（688 开头）"),
    db: Session = Depends(get_db),
):
    """查询当前回测交易记录，支持分页和多维度筛选"""
    q = db.query(BacktestTrade)
    if stock_code:
        q = q.filter(BacktestTrade.stock_code.contains(stock_code))
    if market:
        q = q.filter(BacktestTrade.market == market)
    if holding:
        q = q.filter(BacktestTrade.sell_date == None)  # noqa: E711
    if exclude_kcb:
        q = q.filter(~BacktestTrade.stock_code.like('688%'))

    total  = q.count()
    trades = (
        q.order_by(BacktestTrade.buy_date.desc())
         .offset((page - 1) * page_size)
         .limit(page_size)
         .all()
    )

    return {
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "trades": [
            {
                "stock_code":         t.stock_code,
                "stock_name":         t.stock_name,
                "market":             t.market,
                "buy_date":           t.buy_date,
                "buy_price":          t.buy_price,
                "sell_date":          t.sell_date,
                "sell_price":         t.sell_price,
                "profit_rate":        t.profit_rate,
                "lowest_after_buy":   t.lowest_after_buy,
                "highest_after_buy":  t.highest_after_buy,
                "entry_inefficiency": t.entry_inefficiency,
                "exit_inefficiency":  t.exit_inefficiency,
                "close_reason":       t.close_reason,
            }
            for t in trades
        ],
    }

@app.get("/api/backtest/profit-curve")
async def get_profit_curve(
    stock_code:  str  = Query("",    description="按股票代码模糊查询"),
    market:      str  = Query("",    description="板块: SH/SZ/CYB"),
    exclude_kcb: bool = Query(False, description="排除科创板（688 开头）"),
    db: Session = Depends(get_db),
):
    """获取累计收益率曲线（按卖出日期聚合）"""
    from collections import defaultdict
    q = db.query(BacktestTrade).filter(
        BacktestTrade.sell_date != None,   # noqa: E711
        BacktestTrade.profit_rate != None, # noqa: E711
    )
    if stock_code:
        q = q.filter(BacktestTrade.stock_code.contains(stock_code))
    if market:
        q = q.filter(BacktestTrade.market == market)
    if exclude_kcb:
        q = q.filter(~BacktestTrade.stock_code.like('688%'))

    trades = q.order_by(BacktestTrade.sell_date.asc()).all()

    # 按卖出日期聚合
    date_groups: dict = defaultdict(list)
    for t in trades:
        date_groups[str(t.sell_date)].append(t.profit_rate)

    result = []
    cumulative = 0.0
    for date_str in sorted(date_groups.keys()):
        day_sum = sum(date_groups[date_str])
        cumulative += day_sum * 100
        result.append({
            "date":         date_str,
            "daily_profit": round(day_sum * 100, 4),
            "cumulative":   round(cumulative, 4),
            "count":        len(date_groups[date_str]),
        })
    return result


@app.post("/api/rl/train")
async def rl_train_endpoint(
    stock_codes:      List[str],
    n_trials:         int  = Query(30,  ge=1,  le=10000,  description="训练轮次"),
    stocks_per_trial: int  = Query(50,  ge=0,           description="每轮采样数，0=全部"),
    lookback_period:  int  = Query(120,                 description="回溯周期(天)"),
):
    """贝叶斯参数优化训练：每轮用 Optuna TPE 建议参数 → 运行回测 → 计算奖励 → 更新采样器"""
    if not stock_codes:
        raise HTTPException(status_code=400, detail="请提供股票代码列表")

    async def generate():
        import optuna
        optuna.logging.set_verbosity(optuna.logging.WARNING)

        db         = SessionLocal()
        session_id = str(uuid.uuid4())
        study      = optuna.create_study(
            direction="maximize",
            sampler=optuna.samplers.TPESampler(seed=42),
        )
        best_reward = float('-inf')

        try:
            for trial_num in range(n_trials):
                # 每轮采样股票
                if stocks_per_trial > 0 and stocks_per_trial < len(stock_codes):
                    sample = random.sample(stock_codes, stocks_per_trial)
                else:
                    sample = list(stock_codes)

                # Optuna 建议参数
                trial  = study.ask()
                dip    = trial.suggest_float("dip_threshold", 0.05, 0.40)
                profit = trial.suggest_float("profit_target",  0.01, 0.20)

                config = BacktestConfig(
                    dip_threshold=dip,
                    profit_target=profit,
                    lookback_period=lookback_period,
                )

                # 在独立线程中运行同步回测
                def run_bt(codes=sample, cfg=config):
                    db2 = MarketSessionLocal()  # 市场库：查 Stock 名称/exchange
                    try:
                        trades = []
                        for code in codes:
                            trades.extend(backtest_single_stock(db2, code, cfg))
                        return trades
                    finally:
                        db2.close()

                trades = await asyncio.to_thread(run_bt)

                # 计算奖励：每张已平仓的股票投入 10万元，益亏 = profit_rate * 10万
                closed     = [t for t in trades if t.sell_date is not None]
                reward     = sum((t.profit_rate or 0) * 100_000 for t in closed)
                win_rate   = (
                    sum(1 for t in closed if (t.profit_rate or 0) > 0) / len(closed)
                    if closed else 0.0
                )
                avg_pr     = (
                    sum((t.profit_rate or 0) for t in closed) / len(closed)
                    if closed else 0.0
                )

                # 胜率低于 85% 时强惩罚，Optuna 不会将其选为最优参数
                if win_rate < 0.85:
                    reward = -1_000_000

                # 告知 Optuna 结果
                study.tell(trial, reward)

                if reward > best_reward:
                    best_reward = reward

                # 存入 DB
                db.add(RLTrainingRun(
                    session_id      = session_id,
                    trial_number    = trial_num + 1,
                    dip_threshold   = dip,
                    profit_target   = profit,
                    reward          = reward,
                    total_trades    = len(trades),
                    closed_trades   = len(closed),
                    win_rate        = win_rate,
                    avg_profit_rate = avg_pr,
                    holding_count   = len(trades) - len(closed),
                ))
                db.commit()

                best_p = study.best_params if study.best_trial else None
                yield json.dumps({
                    "trial":          trial_num + 1,
                    "total_trials":   n_trials,
                    "dip_threshold":  round(dip,    4),
                    "profit_target":  round(profit, 4),
                    "reward":         round(reward,      2),
                    "best_reward":    round(best_reward, 2),
                    "best_params":    {
                        "dip_threshold": round(best_p["dip_threshold"], 4),
                        "profit_target": round(best_p["profit_target"],  4),
                    } if best_p else None,
                    "total_trades":   len(trades),
                    "closed_trades":  len(closed),
                    "win_rate":       round(win_rate, 4),
                    "done":           trial_num + 1 >= n_trials,
                }) + "\n"
        finally:
            db.close()

    return StreamingResponse(generate(), media_type="application/x-ndjson")


@app.post("/api/optimize", response_model=OptimizationResult)
async def optimize_endpoint(
    stock_codes: List[str],
    dip_threshold: float = Query(0.3, description="跌买阈值"),
    profit_target: float = Query(0.1, description="盈利目标"),
    lookback_period: int = Query(120, description="回溯周期(天)"),
    db: Session = Depends(get_market_db)
):
    """
    优化策略参数
    
    基于回测结果分析：
    - 买点无效度：实际买价比买后最低价高多少
    - 卖点无效度：卖价比买后最高价低多少
    
    并给出参数优化建议
    """
    if not stock_codes:
        raise HTTPException(status_code=400, detail="请提供股票代码列表")
    
    config = BacktestConfig(
        dip_threshold=dip_threshold,
        profit_target=profit_target,
        lookback_period=lookback_period
    )
    return optimize_strategy(db, stock_codes, config)


# ========== 数据初始化 API ==========

@app.post("/api/init-data")
async def init_demo_data():
    """初始化演示数据"""
    from demo_data import generate_demo_data
    generate_demo_data()
    return {"message": "演示数据生成完成"}


@app.get("/api/sync-price-data")
async def sync_price_data_endpoint():
    """检查 MySQL dbbardata 最新日期，逗层从 baostock 补充缺失数据（流式返回进度）"""
    async def generate():
        import price_db
        from services.baostock_fetcher import bs_login, bs_logout, fetch_stock_prices_incremental
        from datetime import timedelta

        today_str = date.today().strftime("%Y-%m-%d")

        # Step 1: 一次性批量获取所有股票最新日期
        def _prepare():
            symbols     = price_db.get_all_symbols()
            latest_map  = price_db.get_all_latest_dates()
            return symbols, latest_map

        symbols, latest_map = await asyncio.to_thread(_prepare)

        # Step 2: 筛选需要更新的股票
        to_sync = []
        for sym in symbols:
            code     = sym["code"]
            exchange = sym["exchange"]
            key      = f"{code}_{exchange}"
            latest   = latest_map.get(key)
            if latest is None:
                start = "2015-01-01"
            else:
                next_day = (date.fromisoformat(latest) + timedelta(days=1)).strftime("%Y-%m-%d")
                if next_day > today_str:
                    continue   # 已是最新
                start = next_day
            to_sync.append({"code": code, "exchange": exchange, "start": start})

        total       = len(to_sync)
        added_total = 0

        yield json.dumps({"current": 0, "total": total, "code": "", "added": 0,
                          "added_total": 0, "done": False}) + "\n"

        if total == 0:
            yield json.dumps({"current": 0, "total": 0, "code": "", "added": 0,
                              "added_total": 0, "done": True}) + "\n"
            return

        # Step 3: 登录 baostock
        ok = await asyncio.to_thread(bs_login)
        if not ok:
            yield json.dumps({"error": "baostock login failed", "done": True}) + "\n"
            return

        try:
            for i, sym in enumerate(to_sync, 1):
                code, exchange, start = sym["code"], sym["exchange"], sym["start"]

                added, err = await asyncio.to_thread(
                    fetch_stock_prices_incremental, code, exchange, start, today_str
                )
                added_total += added

                yield json.dumps({
                    "current":     i,
                    "total":       total,
                    "code":        code,
                    "added":       added,
                    "added_total": added_total,
                    "error":       err,
                    "done":        i >= total,
                }) + "\n"
        finally:
            await asyncio.to_thread(bs_logout)

    return StreamingResponse(generate(), media_type="application/x-ndjson")


@app.post("/api/sync-stock-info")
async def sync_stock_info_endpoint(
    years:      int  = Query(3,    ge=1, le=5,    description="历史估值年数"),
    max_stocks: int  = Query(0,    ge=0,          description="处理数量限制，0=全部"),
    delay:      float= Query(0.3,  ge=0.1, le=2.0, description="每只股票请求间隔(秒)"),
    db: Session = Depends(get_market_db),
):
    """
    从 baostock 同步 A 股股票基本信息 + 估值数据（PE/PB/PS/市值）+ 夏普率

    - 自动获取股票名称、行业分类
    - 获取真实 PE(TTM)、PB(MRQ)、PS(TTM)
    - 计算近1年年化夏普率
    - 支持增量更新（已有记录直接覆盖，不重复创建）

    ⚠️ 全量同步耗时较长（A 股约 5000 只，预计数分钟），建议先用 max_stocks=10 测试
    """
    from services.baostock_fetcher import sync_all_stock_info
    result = await asyncio.to_thread(
        sync_all_stock_info, db, years, delay, max_stocks
    )
    return {
        "message": "同步完成",
        "total":   result["total"],
        "success": result["success"],
        "failed":  result["failed"],
    }


@app.post("/api/stocks/{stock_code}/refresh")
async def refresh_stock_endpoint(
    stock_code: str,
    db: Session = Depends(get_market_db),
):
    """
    刷新单只股票的 baostock 估值数据（PE/PB/PS/市值/夏普率）

    适合前端按需刷新某只股票的指标，速度快（1~2 秒）
    """
    from services.baostock_fetcher import refresh_single_stock
    ok = await asyncio.to_thread(refresh_single_stock, db, stock_code)
    if not ok:
        raise HTTPException(status_code=404, detail=f"股票 {stock_code} 不存在或数据获取失败")
    return {"message": f"{stock_code} 估值数据已更新"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
