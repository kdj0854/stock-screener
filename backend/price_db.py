"""
MySQL 历史行情数据访问层
读取 dbbardata 表的真实历史 K 线数据，用于回测和市值估算
"""
import pymysql
import pandas as pd
from sqlalchemy import create_engine, text
from typing import List, Dict, Optional
from config import get_mysql_config


# ── 模块级单例，只创建一次，所有调用复用连接池 ──────────────────────
_engine = None


def get_engine():
    """获取 SQLAlchemy engine（单例，整个进程只创建一次）"""
    global _engine
    if _engine is None:
        cfg = get_mysql_config()
        url = (
            f"mysql+pymysql://{cfg['user']}:{cfg['password']}"
            f"@{cfg['host']}:{cfg['port']}/{cfg['database']}"
            f"?charset={cfg['charset']}"
        )
        _engine = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10)
    return _engine


def get_connection():
    """获取 pymysql 原生连接（用于 cursor 查询）"""
    return pymysql.connect(**get_mysql_config())


def get_all_symbols() -> List[Dict]:
    """
    获取所有股票代码列表（去重，SZSE 优先于 SSE）

    Returns:
        [{"code": "000001", "exchange": "SZSE"}, ...]
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT symbol, exchange
            FROM dbbardata
            WHERE `interval` = 'd'
            ORDER BY symbol, exchange
        """)
        rows = cursor.fetchall()

        # 同一 code 在两个交易所都有时，优先保留 SZSE
        symbols_dict: Dict[str, Dict] = {}
        for symbol, exchange in rows:
            if symbol not in symbols_dict:
                symbols_dict[symbol] = {"code": symbol, "exchange": exchange}
            elif exchange == "SZSE":
                symbols_dict[symbol] = {"code": symbol, "exchange": exchange}

        result = list(symbols_dict.values())
        print(f"[OK] 从历史行情库获取到 {len(result)} 只股票代码")
        return result
    finally:
        conn.close()


def get_stock_prices(symbol: str, exchange: str, start_date: str = "2022-01-01") -> pd.DataFrame:
    """
    获取指定股票的历史日线价格数据

    Args:
        symbol:     股票代码，如 "000001"
        exchange:   交易所，"SSE" 或 "SZSE"
        start_date: 开始日期，格式 YYYY-MM-DD

    Returns:
        DataFrame，列名: date, open, high, low, close, volume
    """
    engine = get_engine()
    query = text("""
        SELECT
            DATE(datetime)  AS date,
            open_price      AS open,
            high_price      AS high,
            low_price       AS low,
            close_price     AS close,
            volume
        FROM dbbardata
        WHERE symbol    = :symbol
          AND exchange  = :exchange
          AND `interval` = 'd'
          AND datetime  >= :start_date
        ORDER BY datetime ASC
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"symbol": symbol, "exchange": exchange, "start_date": start_date})
    return df


def get_all_price_stats() -> Dict[str, Dict]:
    """
    批量获取所有股票近1年的价格统计（一次 SQL，避免 N 次查询）

    Returns:
        {"000001_SZSE": {"avg_close": ..., "avg_volume": ...}, ...}
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                symbol,
                exchange,
                AVG(close_price) AS avg_close,
                AVG(volume)      AS avg_volume
            FROM dbbardata
            WHERE `interval` = 'd'
              AND datetime >= DATE_SUB(NOW(), INTERVAL 1 YEAR)
            GROUP BY symbol, exchange
        """)
        rows = cursor.fetchall()
        result = {}
        for symbol, exchange, avg_close, avg_volume in rows:
            key = f"{symbol}_{exchange}"
            result[key] = {
                "avg_close":  float(avg_close or 0),
                "avg_volume": float(avg_volume or 0),
            }
        print(f"[OK] 批量获取价格统计：{len(result)} 条")
        return result
    finally:
        conn.close()


def get_price_stats(symbol: str, exchange: str) -> Dict:
    """
    获取股票价格统计信息，用于估算市值
    仅查最近 1 年数据，速度快
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                AVG(close_price) AS avg_close,
                AVG(volume)      AS avg_volume,
                MIN(datetime)    AS start_date,
                MAX(datetime)    AS end_date,
                COUNT(*)         AS bar_count
            FROM dbbardata
            WHERE symbol    = %s
              AND exchange   = %s
              AND `interval` = 'd'
              AND datetime   >= DATE_SUB(NOW(), INTERVAL 1 YEAR)
        """, (symbol, exchange))
        row = cursor.fetchone()
        if row and row[0]:
            return {
                "avg_close":  float(row[0]),
                "avg_volume": float(row[1] or 0),
                "start_date": row[2],
                "end_date":   row[3],
                "bar_count":  int(row[4] or 0),
            }
        return {}
    finally:
        conn.close()


def get_all_latest_dates() -> Dict[str, str]:
    """
    一次性批量获取所有股票的最新日期（单条 SQL，避免 N 次查询）

    Returns:
        {"000001_SZSE": "2026-03-20", ...}  日期格式 YYYY-MM-DD
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT symbol, exchange, MAX(DATE(datetime)) AS latest_date
            FROM dbbardata
            WHERE `interval` = 'd'
            GROUP BY symbol, exchange
        """)
        rows = cursor.fetchall()
        result = {}
        for symbol, exchange, latest_date in rows:
            key = f"{symbol}_{exchange}"
            result[key] = str(latest_date) if latest_date else None
        return result
    finally:
        conn.close()


def estimate_financials(symbol: str, exchange: str) -> Dict:
    """
    基于真实价格数据估算市值（baostock 数据不可用时的回退方案）

    估算方法（粗略，仅供参考）：
      总股本 ≈ 平均成交量 × 100（手 → 股）
      总市值 ≈ 最新收盘价 × 总股本 / 1e8（亿元）
      PE     ≈ 用行业中位数 20 作为保守估算（非随机）
    """
    stats = get_price_stats(symbol, exchange)
    if not stats or stats["avg_close"] == 0:
        return {"pe_ratio": 20.0, "market_cap": 50.0, "pb_ratio": None, "ps_ratio": None}

    avg_close  = stats["avg_close"]
    avg_volume = stats["avg_volume"]

    # 估算总股本（手 × 100 = 股）
    estimated_shares = avg_volume * 100

    # 估算总市值（亿元）
    market_cap = avg_close * estimated_shares / 1e8

    # 给市值合理范围：5 ~ 5000 亿
    market_cap = max(5.0, min(5000.0, market_cap))

    # PE 使用 A 股中位数约 20 倍作为保守估算
    pe_ratio = 20.0

    return {
        "pe_ratio":   round(pe_ratio, 2),
        "market_cap": round(market_cap, 2),
        "pb_ratio":   None,
        "ps_ratio":   None,
    }


if __name__ == "__main__":
    print("=" * 50)
    print("测试 MySQL 历史行情连接")
    print("=" * 50)

    symbols = get_all_symbols()
    print(f"\n总股票数: {len(symbols)}")
    print("前5条:", symbols[:5])

    if symbols:
        test = symbols[0]
        print(f"\n读取 {test['code']} ({test['exchange']}) 价格数据...")
        df = get_stock_prices(test["code"], test["exchange"])
        if not df.empty:
            print(f"共 {len(df)} 条，最新5条:")
            print(df.tail(5).to_string(index=False))
