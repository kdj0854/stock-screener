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

- **后端**：Python 3 + FastAPI + SQLite
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

- **Stock**：股票基本信息
- **StockFinancial**：财务数据（市盈率、市值）
- **StockPrice**：历史价格数据
- **BacktestResult**：回测交易记录

### 核心技术栈

- **FastAPI**：现代高性能 Python Web 框架
- **SQLAlchemy**：Python ORM
- **Pandas**：强大的数据分析库
- **React**：用于构建用户界面
- **Recharts**：数据可视化图表库
- **Tailwind CSS**：实用优先的 CSS 框架
