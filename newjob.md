下面是按 Superpowers 工作流整理后的最终交付版：先 brainstorming，再收敛 plan，再评审 plan，最后给出经过 3 轮自我检查的实施计划。Superpowers 的核心思想是：先澄清设计，不急着写代码；再把计划拆成足够具体的小任务；执行时坚持 TDD、代码评审和验证闭环。

说明：这不是投资建议。下面是工程实施计划，目标是构建一个可回放、可风控、可审计的 Polymarket 自动交易系统。

⸻

1. Brainstorming：能力组合方案

1.1 核心判断

不要把 9 个项目硬拼成一个巨型系统。更合理的方式是：

Polymarket 官方 SDK/API 做交易执行内核；其他项目只作为数据、预测、研究、事件分析、UI 或辅助模块。

原因很简单：Polymarket 的 CLOB 交易涉及官方认证、订单签名、API key、WebSocket 用户频道、限流、地理限制和订单生命周期，这些必须以官方文档和 SDK 为准。Polymarket 官方提供 TypeScript、Python、Rust 客户端，Python 对应 py-clob-client，支持 CLOB API 的市场数据、订单管理和认证。

1.2 项目能力映射

项目	在机器人中的角色	是否进主链路
Polymarket 官方 SDK/API	下单、撤单、订单查询、签名、用户频道监听	必须进主链路
OpenBB	宏观、股票、加密、经济、新闻等外部金融数据底座	可进数据层
TrendRadar	RSS、热点、舆情、关键词新闻监控、MCP 分析	可进事件层
public-apis	数据源发现目录，用于补充 API provider	不进运行时主链路
TimesFM	通用时间序列预测，适合 mid-price、spread、volume、trade intensity	可进模型层
Kronos	金融 K 线 foundation model，适合 OHLCV/candle 化后的 Polymarket 或外部资产序列	可进模型层
TradingAgents	多 Agent 慢决策：研究员、情绪、技术、风险、交易员辩论	可进策略研究层
MiroFish	多 Agent 情景推演，适合重大政治/体育/宏观事件市场的离线模拟	离线实验室
FinceptTerminal	金融终端、UI、数据连接器、工作流编辑器参考	参考，不进核心
sherlock-project/sherlock	OSINT 用户名/账号发现工具，可用于公开信息源账号映射	只做研究辅助，严格限制用途

Kronos 是面向金融 K 线的 foundation model，使用 OHLCV 等 K-line 序列；TimesFM 是 Google Research 的时间序列 foundation model，当前 README 描述了 TimesFM 2.5、长上下文、分位数预测和 LoRA 微调示例；TradingAgents 是多 Agent 金融交易框架；MiroFish 是多 Agent 群体智能预测/情景推演引擎；TrendRadar 是热点/舆情/RSS 聚合与 MCP 分析工具；FinceptTerminal 是金融终端和 AI agent 平台；public-apis 是公共 API 目录。

sherlock-project/sherlock 的定位需要特别纠正：它不是交易异常检测库，而是“按用户名查找跨社交平台公开账号”的 OSINT 工具。它最多用于研究公开人物、项目方、新闻源、KOL 的公开账号映射，不能用于骚扰、跟踪、挖私密信息或规避平台规则。

⸻

2. Plan 评审：三种方案对比

方案 A：轻量 MVP，规则策略 + 官方执行

内容：
只做 Polymarket 行情采集、回放、纸交易、规则策略、风控、官方 SDK 下单。

优点： 最快上线、风险最低、最容易验证。
缺点： AI 能力弱。
结论： 作为 Phase 1 必选。

方案 B：模型增强，TimesFM/Kronos + 事件特征

内容：
在方案 A 上加入 TimesFM、Kronos、TrendRadar、OpenBB。

优点： 有真实预测和事件驱动能力。
缺点： 特征泄漏、过拟合、延迟、模型漂移需要严控。
结论： 作为 Phase 2。

方案 C：全 Agent 自动交易，TradingAgents + MiroFish 主导交易

内容：
让 Agent 直接做市场判断和下单。

优点： 叙事分析强，适合复杂事件。
缺点： 慢、不稳定、不可直接信任、难以回测。
结论： 不允许直接下单，只能作为“慢决策建议层”。

最终选择：A → B → C 分阶段推进。

⸻

3. 最终架构

3.1 总体架构

Polymarket Gamma/Data/CLOB/WSS
        │
        ▼
Market Ingestion Layer
市场发现、订单簿、成交、价格、事件状态
        │
        ▼
Canonical Data Layer
PostgreSQL + ClickHouse + Redis + Object Storage
        │
        ▼
Feature Layer
book imbalance、spread、mid、volume、news heat、event novelty
        │
        ├── Rule Strategy
        ├── TimesFM Service
        ├── Kronos Service
        ├── TradingAgents Slow Research
        └── MiroFish Offline Scenario Lab
        │
        ▼
Signal Ensemble
统一 Signal：方向、价格、数量、置信度、TTL、理由
        │
        ▼
Risk Engine
限额、滑点、敞口、地理限制、限流、staleness、kill switch
        │
        ▼
Execution Adapter
py-clob-client / official CLOB client
        │
        ▼
Order Manager + Reconcile + Monitoring

Polymarket WebSocket 提供 market、user、sports、RTDS 等频道；market channel 可获得订单簿、价格变化、成交、best bid/ask、新市场和 resolved 事件；user channel 需要 API 凭证，用于订单和交易更新。

3.2 核心设计原则

1. 执行层只信官方 SDK/API。
    下单、撤单、heartbeat、订单签名、API key、funder、signature type 都不交给外部 AI 项目。
2. LLM/Agent 只能提案，不能越过风控。
    TradingAgents 和 MiroFish 的输出只能形成 ResearchOpinion 或 ScenarioScore，不能直接生成 ApprovedOrder。
3. 先回放，再纸交易，再小资金，再扩大。
    没有通过 replay、paper、shadow、small-live 四级验证，不允许进入实盘主链路。
4. 所有信号必须可解释、可复现、可审计。
    每笔订单都要记录：输入行情、特征、模型输出、风控决策、最终执行结果。

⸻

4. 推荐仓库结构

polymarket-bot/
  apps/
    collector/              # Polymarket 行情与事件采集
    strategy-service/        # 规则策略 + ensemble
    model-service/           # TimesFM/Kronos 推理服务
    agent-research/          # TradingAgents/MiroFish 离线研究
    execution-service/       # 官方 SDK 执行适配器
    risk-service/            # 风控与审批
    dashboard/               # 控制台
  packages/
    schemas/                 # Pydantic canonical schemas
    clients/
      polymarket/
      openbb/
      trendradar/
    backtest/
    replay/
    metrics/
  infra/
    docker-compose.yml
    k8s/
    terraform/
  tests/
    contract/
    unit/
    integration/
    replay/
    paper/
  docs/
    architecture.md
    risk_policy.md
    runbook.md
    compliance_checklist.md

⸻

5. Canonical Schemas

必须先定义统一对象，否则后续模型、回测、执行都会混乱。

class MarketCatalog:
    condition_id: str
    yes_token_id: str
    no_token_id: str
    question: str
    category: str
    end_time: str
    active: bool
    closed: bool
    fees_enabled: bool
    resolution_source: str | None
class OrderBookEvent:
    token_id: str
    ts_ms: int
    bids: list[tuple[float, float]]
    asks: list[tuple[float, float]]
    event_type: str
class TradeEvent:
    token_id: str
    ts_ms: int
    price: float
    size: float
    side: str
class FeatureVector:
    token_id: str
    ts_ms: int
    mid: float
    spread: float
    imbalance_5: float
    realized_vol: float
    trade_intensity: float
    news_heat: float
    sentiment: float
    model_edge: float | None
class Signal:
    token_id: str
    side: str              # BUY / SELL / HOLD
    target_price: float
    size_usdc: float
    confidence: float
    ttl_seconds: int
    rationale: str
    source: str            # rule / timesfm / kronos / agent / ensemble
class ApprovedOrder:
    signal_id: str
    token_id: str
    side: str
    price: float
    size: float
    order_type: str
    expires_at_ms: int
    risk_checks: list[str]
class ExecutionReport:
    order_id: str
    status: str
    filled_size: float
    avg_price: float | None
    reject_reason: str | None

⸻

6. 分阶段实施计划

Phase 0：合规、账户、环境定标

目标： 确认机器人是否允许运行，以及用什么账户形态运行。

任务：

1. 确认交易地区是否可用。Polymarket 提供 geoblock 检查，文档说明受限制地区提交的订单会被拒绝。
2. 确认钱包类型、funder、signature type、allowance、API key 生成方式。
3. 创建 .env.example，禁止提交真实私钥。
4. 创建 risk_policy.yaml。
5. 明确资金上限，例如：

max_total_capital_usdc: 500
max_position_per_market_usdc: 50
max_order_size_usdc: 10
max_daily_loss_usdc: 25
require_manual_enable_live: true

验收标准：

* 启动时自动检查 geoblock。
* 没有 API key 或私钥时只能进入 read-only/paper mode。
* 所有 secret 只允许从 KMS、环境变量或 secret manager 注入。

⸻

Phase 1：Polymarket 数据采集与回放

目标： 先把市场数据采集、落库、回放做好。

任务：

1. 实现 Market Discovery：
    * 从 Polymarket Gamma/Data/CLOB 读取 active markets、condition_id、token_id、fees、resolution 相关字段。
2. 实现 WebSocket collector：
    * market channel 订阅 asset IDs。
    * user channel 订阅 condition IDs。
    * heartbeat 自动 PING/PONG。
3. 落库：
    * PostgreSQL：市场元数据、订单状态、策略配置。
    * ClickHouse：订单簿快照、成交、特征、信号。
    * Redis：实时事件流。
4. 实现 event replay：
    * 给定时间窗口，重放历史 book/trade/news events。
    * 保证同样输入得到同样特征。

验收标准：

* 可连续采集 24 小时不中断。
* WebSocket 断线自动重连。
* 采集数据可按 event-time 重放。
* 每个 market 能从 condition_id 映射到 YES/NO token_id。

⸻

Phase 2：Baseline 策略与回测

目标： 不引入 AI，先做可解释的规则策略。

Baseline 策略：

1. 订单簿不平衡策略
    * imbalance_5 = (bid_depth_5 - ask_depth_5) / total_depth_5
    * 当 imbalance 明显偏正、spread 小、成交活跃时做多 YES。
2. 事件热度策略
    * TrendRadar 关键词热度突增时提高关注优先级。
3. 均值回归策略
    * mid-price 短期偏离 rolling mean，且无重大新闻时做回归。
4. 流动性奖励观察策略
    * 只在符合最小 size、最大 spread、盘口稳定的市场上挂单。Polymarket 文档说明 liquidity rewards 鼓励 maker 挂 resting limit orders，并可从 market objects 中获取 min_incentive_size 和 max_incentive_spread 等字段。

验收标准：

* 每个策略有单元测试。
* 每个策略可在 replay 中输出信号。
* 回测报告包含：
    * PnL
    * hit rate
    * max drawdown
    * slippage
    * order staleness
    * market exposure
    * fill ratio

⸻

Phase 3：风控引擎

目标： 所有订单先过风控，风控永远优先于策略。

必须实现的风控规则：

pre_trade_checks:
  - geoblock_check
  - market_active_check
  - market_not_resolved_check
  - price_range_check
  - max_order_size_check
  - max_market_exposure_check
  - max_total_exposure_check
  - max_daily_loss_check
  - spread_check
  - liquidity_check
  - stale_signal_check
  - rate_limit_bucket_check
  - kill_switch_check

Polymarket 文档说明 CLOB trading endpoints 有 burst/sustained rate limits，超过限制后请求会被 Cloudflare 延迟/排队，而不一定是立即拒绝；因此机器人必须做本地限流、订单 TTL 和 staleness guard。

验收标准：

* 策略无法绕过风控。
* kill_switch=true 时禁止所有新订单，只允许撤单。
* 风控拒绝必须写入日志和数据库。
* 每个风控规则都有单元测试和集成测试。

⸻

Phase 4：执行适配器

目标： 用官方 SDK 完成最小闭环：签名、下单、撤单、查询、对账。

实现内容：

1. ExecutionAdapter.place_limit_order()
2. ExecutionAdapter.cancel_order()
3. ExecutionAdapter.cancel_market_orders()
4. ExecutionAdapter.get_open_orders()
5. ExecutionAdapter.reconcile()
6. ExecutionAdapter.heartbeat()

Polymarket 认证分 L1 和 L2：L1 用私钥签 EIP-712 消息，L2 用 API key/secret/passphrase 生成 HMAC 请求；即使有 L2 header，创建订单仍需要本地签名订单 payload。

验收标准：

* 支持 dry-run。
* 支持 paper mode。
* 支持 shadow mode。
* 支持 live mode，但默认关闭。
* 小额实盘只允许手动开启。
* 每笔订单都有完整状态机：

CREATED → SIGNED → SUBMITTED → ACKED → PARTIAL_FILLED → FILLED
                       │
                       ├── REJECTED
                       ├── CANCEL_REQUESTED → CANCELLED
                       └── EXPIRED

⸻

Phase 5：TimesFM/Kronos 模型服务

目标： 把预测模型做成独立服务，而不是塞进执行主进程。

TimesFM 用途：

* 预测 mid-price。
* 预测 spread。
* 预测 trade intensity。
* 输出分位数区间，用于风险调整。

Kronos 用途：

* 将 Polymarket token mid-price 聚合成 OHLCV。
* 对 YES/NO token 或相关外部资产做 candle 预测。
* 与 TimesFM 形成 ensemble。

服务接口：

POST /forecast/timesfm
{
  "token_id": "...",
  "series": [0.51, 0.515, 0.512],
  "horizon": 12,
  "features": {
    "spread": [...],
    "volume": [...],
    "news_heat": [...]
  }
}
POST /forecast/kronos
{
  "token_id": "...",
  "ohlcv": [
    {"open": 0.50, "high": 0.53, "low": 0.49, "close": 0.52, "volume": 1234}
  ],
  "horizon": 12
}

验收标准：

* 模型服务挂掉时，策略自动降级到 rule-only。
* 模型输出必须带置信区间或 uncertainty proxy。
* 模型不直接下单，只输出 ModelForecast。
* 离线回测和在线推理使用同一套 feature transform。

⸻

Phase 6：TradingAgents 慢决策层

目标： 让 Agent 做研究，不让 Agent 直接交易。

TradingAgents 使用多角色 LLM agent 来模拟金融机构的研究、技术分析、情绪分析、交易员和风险管理流程，并基于 LangGraph 组织。

适合的使用场景：

* 选哪些市场值得关注。
* 对重大事件市场做 bull/bear/risk 辩论。
* 给出自然语言解释。
* 发现 resolution rule 的歧义。
* 生成人工复盘报告。

不允许：

* 不允许 Agent 直接调用执行适配器。
* 不允许 Agent 改风控参数。
* 不允许 Agent 在无引用来源时提高 confidence。

验收标准：

* TradingAgents 输出格式固定：

class AgentOpinion:
    market_id: str
    stance: str
    confidence: float
    thesis: str
    risks: list[str]
    citations: list[str]
    expires_at: int

* Agent opinion 只能进入 ensemble，权重默认不超过 15%。

⸻

Phase 7：TrendRadar、OpenBB、public-apis 数据增强

目标： 为 Polymarket 事件市场引入外部信息优势。

OpenBB：

* 宏观数据。
* 股票/ETF/加密数据。
* 利率、商品、指数。
* 财报或经济指标相关市场的外部变量。

TrendRadar：

* 新闻关键词热度。
* RSS 事件突发。
* 多平台热点变化。
* MCP 查询本地积累新闻数据。TrendRadar 的英文 README 说明，AI 分析依赖本地已积累新闻数据，不是直接查询实时在线数据。

public-apis：

* 只作为数据源目录。
* 不作为生产依赖。
* 新 provider 进入系统前必须经过 contract test。

验收标准：

* 每个外部数据源都有 freshness timestamp。
* 数据源失败不影响 Polymarket 主行情采集。
* 任何新闻信号必须带 source、published_at、ingested_at。
* 过期新闻不得触发交易。

⸻

Phase 8：MiroFish 情景实验室

目标： 用于重大事件的离线推演。

MiroFish 的 README 描述了基于多 Agent 的预测引擎：从现实种子材料中构建知识图谱、生成 agent、并行仿真，最后生成预测报告。

适合场景：

* 大选。
* 地缘政治。
* 公司并购。
* 重大诉讼。
* 体育季后赛。
* 政策投票。

不适合场景：

* 高频盘口响应。
* 秒级交易。
* 直接决定下单。

输出进入系统的方式：

class ScenarioScore:
    market_id: str
    scenario_name: str
    probability_shift: float
    confidence: float
    reasoning: str
    generated_at: int

验收标准：

* MiroFish 只在离线 notebook 或 batch job 中运行。
* 输出必须人工复核后才能进入策略配置。
* 默认不进入实盘 ensemble。

⸻

Phase 9：Sherlock 辅助信息源映射

目标： 只用于公开账号发现和信息源整理。

sherlock-project/sherlock 可根据用户名在多个社交网站查找公开账号。

允许用途：

* 找公开项目、机构、候选人、KOL 的公开账号。
* 建立新闻源 whitelist。
* 发现账号迁移或冒名风险。
* 辅助 TrendRadar 关键词和 source list。

禁止用途：

* 私人 doxxing。
* 批量跟踪普通个人。
* 绕过隐私设置。
* 把 OSINT 结果直接转成交易信号。

验收标准：

* 只允许查询白名单实体。
* 每次查询写审计日志。
* 输出只进入 source_registry，不直接进入交易策略。

⸻

7. 技术栈

推荐默认栈

Language: Python 3.11/3.12
API: FastAPI
Async: asyncio, aiohttp, websockets
Schema: Pydantic v2
DB: PostgreSQL + ClickHouse
Queue/Cache: Redis / Redis Streams
Model: PyTorch, TimesFM, Kronos
Agent: TradingAgents, optional LangGraph
Execution: py-clob-client
Observability: OpenTelemetry + Prometheus + Grafana
Deployment: Docker Compose first, Kubernetes later
Secrets: 1Password / Doppler / AWS Secrets Manager / GCP Secret Manager / HashiCorp Vault

MVP 不建议一开始就上

* 不建议一开始上 Kubernetes。
* 不建议一开始做复杂 RL。
* 不建议一开始做 HFT。
* 不建议一开始把 MiroFish、TradingAgents、TimesFM、Kronos 全塞进主链路。
* 不建议一开始做自动调参实盘。

⸻

8. TDD 实施任务拆解

按照 Superpowers 风格，任务要足够具体，能让初级工程师照着做。

Sprint 1：项目骨架

任务 1：创建 monorepo

* 创建目录结构。
* 配置 ruff、mypy、pytest。
* 配置 pre-commit。
* 写第一个 failing test：test_import_schemas.py。
* 实现最小 schema 包。
* 测试通过后提交。

完成标准：

pytest
ruff check .
mypy packages apps

⸻

Sprint 2：Polymarket 只读数据

任务 2：实现 MarketCatalog client

* 写 contract test，mock Gamma/CLOB 响应。
* 实现 client。
* 保存市场元数据到 PostgreSQL。
* 写重复运行幂等测试。

任务 3：实现 WebSocket collector

* 写 fake WSS server test。
* 测试订阅 asset_ids。
* 测试 heartbeat。
* 测试断线重连。
* 测试 message normalization。

⸻

Sprint 3：回放引擎

任务 4：实现 ClickHouse event store

* 写 insert/query 测试。
* 写 event-time 排序测试。
* 写去重测试。

任务 5：实现 replay runner

* 输入 market_id、start、end。
* 输出 event stream。
* 同一数据重放两次结果必须一致。

⸻

Sprint 4：特征工程

任务 6：实现 book features

* spread。
* best bid/ask。
* depth。
* imbalance。
* realized volatility。
* trade intensity。

任务 7：实现 feature snapshot

* 每 N 秒生成一次 FeatureVector。
* 支持在线和离线一致计算。

⸻

Sprint 5：Baseline 策略

任务 8：实现 rule strategy

* 先写测试：
    * spread 过大 → HOLD。
    * imbalance 强 + news heat 高 → BUY。
    * liquidity 不足 → HOLD。
* 实现最小策略。
* 生成 Signal。

⸻

Sprint 6：风控

任务 9：实现 RiskEngine

* 写所有 pre-trade check 的 failing tests。
* 实现规则。
* 输出 reject reason。
* 任何未知状态默认 reject。

任务 10：实现 kill switch

* 配置文件 kill switch。
* Redis kill switch。
* dashboard kill switch。
* 三者任一为 true，都停止新订单。

⸻

Sprint 7：执行适配器

任务 11：封装 py-clob-client

* mock client。
* 测试 place/cancel/reconcile。
* 禁止单元测试访问真实网络。
* live test 单独标记：pytest -m live。

任务 12：实现 paper execution

* 模拟订单簿撮合。
* 模拟部分成交。
* 模拟滑点。
* 模拟订单过期。

⸻

Sprint 8：Shadow mode

任务 13：实现 shadow trader

* 真实读行情。
* 真实生成信号。
* 真实过风控。
* 不真实下单。
* 记录“如果下单会怎样”。

完成标准：

* 连续跑 7 天。
* 没有未处理异常。
* 每天自动生成报告。

⸻

Sprint 9：模型服务

任务 14：TimesFM service

* 写 API test。
* 输入序列，输出 point forecast + quantile。
* 模型 unavailable 时返回降级错误。

任务 15：Kronos service

* 写 OHLCV transform test。
* 写 candle aggregation test。
* 输出 forecast。

任务 16：ensemble

* rule、timesfm、kronos 三路合成。
* 默认权重：

rule: 0.50
timesfm: 0.25
kronos: 0.25
trading_agents: 0.00

⸻

Sprint 10：慢决策和事件层

任务 17：TrendRadar adapter

* 读取本地新闻输出。
* 标准化为 EventSignal。
* 测试 freshness 和去重。

任务 18：TradingAgents adapter

* 输入 market question、rules、latest news、features。
* 输出 AgentOpinion。
* 缓存结果。
* 默认不参与实盘权重。

任务 19：MiroFish offline pipeline

* 只做 notebook/batch。
* 输出 ScenarioScore。
* 人工审批后进入配置。

⸻

9. 上线门禁

9.1 从 read-only 到 paper

必须满足：

* 数据采集连续 24 小时。
* replay 能复现。
* schema tests 通过。
* contract tests 通过。
* 风控测试通过。

9.2 从 paper 到 shadow

必须满足：

* paper 跑满 7 天。
* 没有严重异常。
* 最大回撤低于设定阈值。
* 所有 reject reason 可解释。
* dashboard 能显示所有信号和订单状态。

9.3 从 shadow 到 small-live

必须满足：

* shadow 跑满 7 天。
* 人工审查前 100 个信号。
* 执行 adapter live dry-run 通过。
* geoblock check 通过。
* allowance check 通过。
* API key rotation 测试通过。
* kill switch 演练通过。

9.4 small-live 资金限制

初始建议：

max_total_capital_usdc: 100
max_order_size_usdc: 5
max_position_per_market_usdc: 20
max_daily_loss_usdc: 10
live_markets_allowlist:
  - highly_liquid_markets_only

连续 30 天稳定后再考虑提高。

⸻

10. 监控和告警

必须监控：

* WebSocket 延迟。
* WebSocket reconnect 次数。
* market data freshness。
* signal count。
* reject count。
* open orders。
* stale orders。
* partial fills。
* realized/unrealized PnL。
* daily loss。
* exposure per market。
* API rate bucket。
* model inference latency。
* model unavailable count。
* agent timeout count。

告警等级：

P0:
  - private key exposure suspected
  - kill switch failed
  - unexpected live order
  - daily loss exceeded
  - geoblock failed but trading attempted
P1:
  - websocket disconnected > 60s
  - order reconciliation mismatch
  - stale order not cancelled
  - model service unavailable > 5min
P2:
  - external news source stale
  - dashboard unavailable
  - paper mode report missing

⸻

11. 许可证和合规边界

建议核心闭源/商业化系统只直接依赖：

* Polymarket 官方 SDK。
* MIT / Apache-2.0 项目。
* 自研代码。

对 AGPL/GPL 项目要谨慎：

* TrendRadar 是 GPL-3.0。
* MiroFish 是 AGPL-3.0。
* FinceptTerminal 是 AGPL-3.0 + Commercial 双许可，并声明商业使用需要商业授权。
* Kronos 是 MIT。
* TimesFM 是 Apache-2.0。
* public-apis 是 MIT。

保守做法：

核心执行引擎：自研 + 官方 SDK
GPL/AGPL 项目：sidecar / research tool / 不直接链接核心交易进程
模型项目：单独服务化
UI/终端项目：只参考，不复制代码

⸻

12. 三轮自我检查结果

自检 1：需求完整性检查

检查项：是否覆盖用户要求的所有项目？

结果：通过。

已覆盖：

* Kronos：模型预测层。
* TradingAgents：慢决策层。
* MiroFish：离线情景推演。
* FinceptTerminal：UI/终端/工作流参考。
* sherlock-project/sherlock：公开账号/信息源映射辅助。
* OpenBB：外部金融数据底座。
* TrendRadar：新闻/舆情/热点事件层。
* public-apis：数据源目录。
* TimesFM：通用时间序列预测层。

修正点：把 sherlock-project/sherlock 正确定位为 OSINT 用户名工具，而不是交易异常检测工具。

⸻

自检 2：安全、合规、风控检查

检查项：是否有高风险自动交易漏洞？

发现并处理：

1. AI 不能直接下单。
    已规定 Agent/LLM 只能输出 opinion，不能跳过 RiskEngine。
2. 官方认证不可替代。
    已规定交易执行只使用官方 CLOB SDK/API，并遵守 L1/L2 认证模型。
3. 地理限制必须前置。
    已加入 geoblock check 和 read-only fallback。
4. 限流和 stale order 必须本地处理。
    已加入 rate bucket、TTL、staleness guard。
5. OSINT 工具不能滥用。
    已限制 Sherlock 只用于白名单公开实体和 source registry。

结果：通过。

⸻

自检 3：工程可执行性检查

检查项：计划是否能被工程团队照着做？

结果：通过。

计划已经包含：

* 仓库结构。
* 核心 schema。
* 数据流。
* 分阶段 roadmap。
* TDD sprint。
* 上线门禁。
* 风控规则。
* 监控告警。
* 许可证边界。
* live mode 前置条件。

剩余开放问题：

1. 你打算部署在个人服务器、云服务器，还是本地机器？
2. 是否只做 paper/shadow，还是最终要 small-live？
3. 目标市场类型：政治、体育、宏观、加密、科技、还是全部？
4. 账户类型、资金规模、所在地区必须在实盘前确认。

⸻

13. 最终执行顺序

我建议你严格按这个顺序做：

1. 项目骨架 + schema
2. Polymarket read-only collector
3. ClickHouse/PostgreSQL/Redis 数据层
4. event replay
5. baseline rule strategy
6. paper execution
7. risk engine
8. official SDK execution adapter
9. shadow mode
10. small-live mode
11. TimesFM/Kronos
12. TrendRadar/OpenBB
13. TradingAgents
14. MiroFish
15. dashboard / terminal polish

最重要的结论：

先做“可回放、可纸交易、可风控、可撤单、可对账”的交易骨架，再加 AI。
这套顺序比一开始就接入所有 Agent 更安全，也更容易真正上线。