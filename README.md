# 股票投资筛选工具 - ValueQuest

## 项目概述

这是一个功能强大的股票投资筛选与策略回溯工具，完全按照您的需求构建。

### 核心功能

#### 1. 基础筛选功能
- **市盈率筛选**：筛选市盈率连续三年小于 30 的股票
- **市值筛选**：筛选当前市值小于 60 亿元的股票
- **自定义条件**：支持调整筛选阈值

#### 2. 策略回溯功能
- **跌买点策略**：当股价从过去半年最高点下跌超过 30% 时买入
- **赢利点策略**：买入后盈利超过 10% 时卖出
- **可调参数**：跌买阈值、盈利目标、回溯周期均可配置

#### 3. 策略优化功能
- **买点无效度分析**：计算实际买价比买后最低价高多少
- **卖点无效度分析**：计算卖价比买后最高价低多少
- **自动优化建议**：根据无效度分析自动调整最优参数

## 技术架构

- **后端**：Python 3 + FastAPI + MySQL + SQLAlchemy
- **前端**：React 18 + TypeScript + Tailwind CSS + Recharts
- **数据**：Pandas 处理金融数据

## 项目结构

```
stock-screener/
├── backend/                    # Python 后端
│   ├── main.py                # FastAPI 主应用
│   ├── database.py            # 数据库配置
│   ├── models.py              # SQLAlchemy 模型
│   ├── schemas.py             # Pydantic 模型
│   ├── demo_data.py           # 演示数据生成
│   ├── requirements.txt       # Python 依赖
│   └── services/              # 业务逻辑
│       ├── screener.py        # 筛选服务
│       ├── backtest.py        # 回测服务
│       └── optimizer.py       # 优化服务
├── frontend/                   # React 前端
│   ├── src/
│   │   ├── components/       # React 组件
│   │   │   ├── ScreenerPanel.tsx    # 筛选面板
│   │   │   ├── BacktestPanel.tsx    # 回测面板
│   │   │   └── OptimizationPanel.tsx # 优化面板
│   │   ├── services/          # API 服务
│   │   ├── types/             # TypeScript 类型
│   │   ├── App.tsx            # 主应用
│   │   └── main.tsx           # 入口文件
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

## 快速开始

### 前置要求

- Python 3.8+
- Node.js 18+
- npm 或 yarn
- MySQL 5.7+ 或 8.0+

---

## 数据库安装与配置

### 一、安装 MySQL

1. 下载并安装 [MySQL Community Server](https://dev.mysql.com/downloads/mysql/)（推荐 8.0）
2. 安装完成后启动 MySQL 服务
3. 使用 root 账号登录，创建数据库（数据库名可自定义，下面以 `stock_db` 为例）：

```sql
CREATE DATABASE stock_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 二、配置数据库连接

后端通过 `C:\Users\<你的用户名>\.vntrader\vt_setting.json` 读取数据库连接信息。

#### 方式 A：使用配置文件（推荐）

在 `C:\Users\<你的用户名>\.vntrader\` 目录下创建或编辑 `vt_setting.json`，填入以下内容：

```json
{
    "database.host": "127.0.0.1",
    "database.port": 3306,
    "database.user": "root",
    "database.password": "你的MySQL密码",
    "database.database": "stock_db"
}
```

#### 方式 B：使用环境变量

若配置文件不存在，后端会回退读取以下环境变量：

| 环境变量 | 说明 | 默认值 |
|---|---|---|
| `MYSQL_HOST` | 数据库主机 | `127.0.0.1` |
| `MYSQL_PORT` | 端口 | `3306` |
| `MYSQL_USER` | 用户名 | `root` |
| `MYSQL_PASSWORD` | 密码 | 空 |
| `MYSQL_DATABASE` | 数据库名 | `vnpy` |

### 三、创建数据表

连接到上一步创建好的数据库，依次执行以下 SQL 建表语句：

```sql
-- 股票基本信息表
CREATE TABLE IF NOT EXISTS stocks (
    id       INT PRIMARY KEY AUTO_INCREMENT,
    code     VARCHAR(20) NOT NULL,
    name     VARCHAR(100) NOT NULL,
    sector   VARCHAR(100),
    exchange VARCHAR(20),
    UNIQUE INDEX idx_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 股票财务/估值数据表（PE、PB、市值等）
CREATE TABLE IF NOT EXISTS stock_financials (
    id           INT PRIMARY KEY AUTO_INCREMENT,
    stock_id     INT NOT NULL,
    report_date  DATE NOT NULL,
    pe_ratio     FLOAT,
    pb_ratio     FLOAT,
    ps_ratio     FLOAT,
    market_cap   FLOAT,
    sharpe_ratio FLOAT,
    data_source  VARCHAR(20) DEFAULT 'baostock',
    INDEX idx_stock_id (stock_id),
    CONSTRAINT fk_stock FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 当前回测交易记录表
CREATE TABLE IF NOT EXISTS backtest_trades_current (
    id                 INT PRIMARY KEY AUTO_INCREMENT,
    run_id             VARCHAR(36) NOT NULL,
    stock_code         VARCHAR(20) NOT NULL,
    stock_name         VARCHAR(100),
    market             VARCHAR(10),
    buy_date           DATE,
    buy_price          FLOAT,
    sell_date          DATE,
    sell_price         FLOAT,
    profit_rate        FLOAT,
    lowest_after_buy   FLOAT,
    highest_after_buy  FLOAT,
    entry_inefficiency FLOAT,
    exit_inefficiency  FLOAT,
    close_reason       VARCHAR(20),
    created_at         DATETIME,
    INDEX idx_run_id (run_id),
    INDEX idx_stock_code (stock_code),
    INDEX idx_market (market)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 回测历史归档表
CREATE TABLE IF NOT EXISTS backtest_trades_history (
    id                 INT PRIMARY KEY AUTO_INCREMENT,
    run_id             VARCHAR(36) NOT NULL,
    stock_code         VARCHAR(20) NOT NULL,
    stock_name         VARCHAR(100),
    market             VARCHAR(10),
    buy_date           DATE,
    buy_price          FLOAT,
    sell_date          DATE,
    sell_price         FLOAT,
    profit_rate        FLOAT,
    lowest_after_buy   FLOAT,
    highest_after_buy  FLOAT,
    entry_inefficiency FLOAT,
    exit_inefficiency  FLOAT,
    close_reason       VARCHAR(20),
    created_at         DATETIME,
    archived_at        DATETIME,
    INDEX idx_run_id (run_id),
    INDEX idx_stock_code (stock_code),
    INDEX idx_market (market)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 贝叶斯/RL 参数优化训练记录表
CREATE TABLE IF NOT EXISTS rl_training_runs (
    id              INT PRIMARY KEY AUTO_INCREMENT,
    session_id      VARCHAR(36) NOT NULL,
    trial_number    INT NOT NULL,
    dip_threshold   FLOAT NOT NULL,
    profit_target   FLOAT NOT NULL,
    reward          FLOAT NOT NULL,
    total_trades    INT,
    closed_trades   INT,
    win_rate        FLOAT,
    avg_profit_rate FLOAT,
    holding_count   INT,
    created_at      DATETIME,
    INDEX idx_session_id (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 四、历史行情数据表（dbbardata）

回测和市值估算依赖一张名为 `dbbardata` 的历史 K 线数据表，结构如下：

```sql
CREATE TABLE IF NOT EXISTS dbbardata (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    symbol      VARCHAR(20) NOT NULL,
    exchange    VARCHAR(20) NOT NULL,
    `interval`  VARCHAR(10) NOT NULL,
    datetime    DATETIME NOT NULL,
    open_price  FLOAT,
    high_price  FLOAT,
    low_price   FLOAT,
    close_price FLOAT,
    volume      FLOAT,
    INDEX idx_symbol_exchange (symbol, exchange, `interval`, datetime)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

> **说明**：`dbbardata` 表中的数据需自行导入。可使用 baostock 或其他行情数据源获取历史日线（`interval = 'd'`）数据后批量写入。无此数据时，筛选和回测功能将无法正常运行。

---

### 安装步骤

#### 1. 安装后端依赖

```bash
cd stock-screener/backend
pip install -r requirements.txt
```

#### 2. 安装前端依赖

```bash
cd stock-screener/frontend
npm install
```

#### 3. 启动应用

**启动后端**（终端 1）：
```bash
cd stock-screener/backend
python main.py
```
后端将在 http://localhost:8000 运行

**启动前端**（终端 2）：
```bash
cd stock-screener/frontend
npm run dev
```
前端将在 http://localhost:5173 运行

#### 4. 使用应用

1. 打开浏览器访问 http://localhost:5173
2. 点击右上角「初始化演示数据」按钮
3. 在「股票筛选」标签页设置筛选条件并点击「开始筛选」
4. 在「策略回测」标签页配置回测参数并点击「运行回测」
5. 在「策略优化」标签页查看优化建议

## API 文档

后端启动后访问 http://localhost:8000/docs 查看完整 API 文档。

### 主要 API 端点

- `POST /api/screen` - 筛选股票
- `POST /api/backtest` - 运行回测
- `POST /api/optimize` - 优化策略
- `POST /api/init-data` - 初始化演示数据
- `GET /api/stocks` - 获取股票列表

## 使用说明

### 筛选股票

1. 设置最大市盈率（默认 30）
2. 设置最大市值（默认 60 亿元）
3. 设置连续年数（默认 3 年）
4. 点击「开始筛选」

### 策略回测

1. 在左侧股票列表选择要回测的股票
2. 设置回测参数：
   - 跌买阈值：股价从半年高点下跌多少百分比时买入（默认 30%）
   - 盈利目标：盈利多少百分比时卖出（默认 10%）
   - 回溯周期：计算过去多少天的最高价（默认 120 天）
3. 点击「运行回测」

### 策略优化

1. 设置当前策略参数
2. 点击「开始优化」
3. 查看优化建议和效果对比

## 策略说明

### 跌买点策略逻辑

```
对于每个交易日：
1. 计算过去 N 天的最高价（滚动最高价）
2. 计算当前价格与滚动最高价的跌幅
3. 如果跌幅 >= 跌买阈值，则触发买入信号
4. 买入后，如果收益率 >= 盈利目标，则触发卖出信号
```

### 优化算法

```
1. 运行原始回测，记录每笔交易的：
   - 买点无效度 = (买入价 - 买入后最低价) / 买入后最低价
   - 卖点无效度 = (买入后最高价 - 卖出价) / 买入后最高价

2. 计算平均无效度：
   - 如果买点无效度 > 5%，建议增大跌买阈值
   - 如果卖点无效度 > 10%，建议增大盈利目标

3. 使用优化后的参数重新回测，对比效果
```

## 注意事项

1. 本工具仅供学习和研究使用，不构成投资建议
2. 回测结果不代表未来收益
3. 实际交易前请谨慎评估风险
4. 演示数据为模拟数据，仅供参考

## 技术细节

### 数据模型

| 表名 | 说明 |
|---|---|
| `stocks` | 股票基本信息（代码、名称、行业、交易所） |
| `stock_financials` | 财务/估值数据（PE、PB、PS、市值、夏普率） |
| `backtest_trades_current` | 当次回测交易记录 |
| `backtest_trades_history` | 历史回测归档记录 |
| `rl_training_runs` | 贝叶斯/RL 参数优化训练结果 |
| `dbbardata` | 历史日线行情数据（需外部导入） |

### 核心技术栈

- **FastAPI**：现代高性能 Python Web 框架
- **SQLAlchemy**：Python ORM
- **Pandas**：强大的数据分析库
- **React**：用于构建用户界面
- **Recharts**：数据可视化图表库
- **Tailwind CSS**：实用优先的 CSS 框架
