# Polymarket Web Terminal 待改进方案

更新日期：2026-05-07

## 评审范围

本评审从普通使用者视角检查当前 Polymarket Web Terminal MVP，而不是从代码完成度视角检查。评审对象包括：

- Web 前端：`web/polymarket-terminal`
- API 门面：`fincept-qt/scripts/polymarket_web_api`
- paper bot 状态与持久化：`fincept-qt/scripts/algo_trading/polymarket_*.py`
- 当前运行入口：Web `4177`，API `8765`

当前 MVP 的安全边界是正确的：只允许 paper trading，不暴露私钥、API secret 或真实 CLOB 下单路径。后续改进不应绕开这个边界。

## 当前用户可完成的工作流

用户现在可以完成以下工作：

- 打开 Web terminal 并通过 F1-F8 切换完整页面。
- 查看 paper mode、live disabled、positions、pending proposals、recent activity。
- 查看 candidate markets、signals、risk queue、audit projections。
- 在 Risk 页面审批或拒绝 API 来源且未过期的 proposal。
- 触发 paper kill switch，并将操作写入 audit event。
- 使用 Audit 页面查看 audit events、trades、signals、positions、candidates、skips、proposals。

这些能力足以支撑一个安全的 paper-only 演示，但还不足以支撑日常研究和交易运营。

## 主要使用缺口

### P0：数据来源状态必须更明确

当前前端 API client 在请求失败时会静默 fallback 到 mock 数据。页面有 `mock fallback` 标签，但普通用户仍容易误以为数据来自真实 API。

改进建议：

- 在全局顶部或底部状态栏显示明确数据源：`API live`、`API unavailable, showing mock data`、`mixed data`。
- 每个页面在使用 mock fallback 时显示不可忽略的 warning。
- API 请求失败时保留错误详情，例如 status code、API base URL、最后请求时间。
- Risk 页面禁止 mock proposal 已实现，应把同类来源保护扩展到所有会影响判断的页面。

验收标准：

- 关闭 API 后刷新页面，用户能在 3 秒内明确看到当前是 mock 数据。
- 所有 mock 数据区域都带来源标识。
- 用户不会在 mock fallback 状态下看到可执行 approve/reject 控件。

### P0：缺少从“启动扫描”到“产生 proposal”的完整操作入口

当前 UI 可以展示 proposals 和审批 proposals，但缺少一键启动 paper bot cycle、选择 strategy/deployment、触发扫描、查看运行日志的入口。用户必须依赖外部脚本或已有数据库状态。

改进建议：

- 增加 Deployment/Strategy 选择器。
- 在 Overview 或 Risk 页面增加只读状态 + 手动触发 paper scan cycle 的入口。
- 为 `/api/control/start`、`/api/control/stop` 提供 Web 控件，但保持 paper-only。
- 展示最近一次 runner cycle 的 scanned/signals/proposals/fills/skips 统计。

验收标准：

- 空数据库首次使用时，用户能按页面指引启动一次 paper scan。
- scan 完成后，候选、信号、proposal、skip 结果在对应页面可见。
- 所有 start/stop/scan 操作写入 audit event。

### P0：审批流程需要更适合人类决策

当前 approve/reject 使用浏览器原生 `confirm()`，理由固定为代码里的默认文本。用户不能输入拒绝原因、调整审批备注，也看不到审批后重新检查 freshness/order book/risk 的详细结果。

改进建议：

- 用应用内审批 modal 替代 `window.confirm()`。
- approve/reject 都要求用户填写或选择 reason。
- 审批前显示关键检查项：proposal age、expires_at、price、size、edge、confidence、risk limit、order book freshness。
- 审批后显示最终状态：approved、expired、failed recheck、paper filled、paper fill skipped。

验收标准：

- 审批前用户能看到为什么该 proposal 可批或不可批。
- reject reason 写入 audit event。
- expired/stale/risk failed 的错误信息能被用户理解。

### P1：页面刷新和实时性不足

当前多数页面只在 mount 时加载一次。审批后 Risk 会 reload，但 Overview、Markets、Signals、Audit 没有统一刷新机制，也没有轮询或实时更新时间。

改进建议：

- 增加全局 Refresh 按钮和每页 last updated 时间。
- 对 Overview/Risk/Audit 增加低频轮询，例如 10-30 秒。
- 加入请求中、请求失败、重试状态。
- 保留用户手动刷新优先级，避免自动刷新打断用户正在填写审批理由。

验收标准：

- 用户能看到每页数据更新时间。
- API 恢复后页面能从 mock fallback 回到 API live。
- 审批队列状态能在其他页面同步更新。

### P1：Audit 查询和导出能力不完整

Audit 页面已经展示 append-only events 和 projection tabs，但 action/result 下拉只覆盖部分值，缺少时间范围、entity id、actor、导出。

改进建议：

- action/result 选项由实际数据动态生成。
- 增加时间范围、entity_type、entity_id、actor_id、request_id 过滤。
- 增加 sanitized CSV/JSON 导出。
- 为 proposal lifecycle 提供单 proposal drilldown。

验收标准：

- 用户能追踪一个 proposal 从 created 到 approved/rejected/expired/filled 的完整链路。
- 导出文件不包含 secrets，且字段说明明确。

### P1：Fincept-style support routes 仍是占位

当前左侧 secondary routes 包括 Strategy Arena、Watchlist、Dataroom、Plans & Credits、Settings、Logout，但都进入同一个 disabled placeholder。用户会看到入口却无法形成预期。

改进建议：

- Watchlist：先做本地只读/本地存储列表，展示市场关注项。
- Settings：显示 API base URL、DB path、mode、安全开关、mock fallback 配置，不提供 secrets 输入。
- Dataroom：保持禁用上传，但说明为什么 MVP 禁用。
- Plans & Credits：保留禁用状态，明确“不涉及 billing”。
- Logout：若无 auth，入口改名为 Session 或隐藏。

验收标准：

- 每个 support route 都有独立说明和可验证行为。
- 禁用能力说明“为什么禁用”和“下一步何时开放”。

### P1：Markets 和 Signals 的解释深度不够

Markets 页面能看候选和 selected market，但缺少排序、候选来源、price freshness、order book detail。Signals 页面能看 edge/confidence，但缺少模型来源、阈值解释、特征方向解释。

改进建议：

- Markets 增加排序：liquidity、volume、spread、probability、created_at。
- Signals 增加 signal source、threshold、model/version、created_at、expires_at。
- Feature contribution 用正负贡献和解释文本，而不是单纯数字列表。
- Skip review 增加可操作建议，例如 stale orderbook、low liquidity、risk limit exceeded。

验收标准：

- 用户能判断某个信号为什么出现，以及为什么没有进入 proposal。
- 用户能从 skip reason 推导下一步配置或数据问题。

### P2：用户引导和空状态需要更完整

空数据库时，页面会显示空表或 mock fallback。新用户不知道如何创建 deployment、如何生成 proposal、当前是否连接到真实 API。

改进建议：

- 新增 first-run checklist。
- 在 Overview 显示 3 步路径：启动 API、选择 strategy、运行 paper scan。
- 空状态提供下一步按钮或文档链接。
- 将 Web README 的运行说明链接到页面内帮助。

验收标准：

- 新用户从空数据库进入页面后，不需要看源码也能知道下一步。

### P2：移动端可用但不是主要运营形态

已有 mobile drawer 和 e2e 覆盖，但金融终端主要是桌面密集操作。移动端目前适合查看，不适合审批和审计。

改进建议：

- 明确移动端为 monitoring-only。
- 审批 modal 在移动端增加更强确认。
- 表格支持横向滚动提示和关键列固定。

验收标准：

- 移动端不会误导用户进行高风险审批操作。

## 推荐实施顺序

1. 明确数据来源和 mock fallback 状态。
2. 增加 Deployment/Strategy 选择和 paper scan/start/stop 操作入口。
3. 重做 proposal 审批 modal 和 reason 输入。
4. 增加全局 refresh、last updated、API error 状态。
5. 完善 Audit 动态过滤、drilldown、导出。
6. 将 Settings/Watchlist 从 placeholder 升级为最小可用 support routes。
7. 丰富 Markets/Signals 的解释、排序和 skip 建议。

## 不建议现在做的事

- 不要接入 live trading。
- 不要添加私钥、API secret 或 Polymarket CLOB 下单配置。
- 不要把 Agents 输出直接接到 execution path。
- 不要一次性复刻 FinceptTerminal 全部付费、账户、billing 页面。
- 不要在没有 audit contract 的情况下新增会改变状态的按钮。

## 下一版成功标准

下一版应让用户完成一条闭环：

1. 打开 Web Terminal。
2. 明确看到 API live 和 paper-only 状态。
3. 选择 deployment/strategy。
4. 手动触发一次 paper scan。
5. 查看候选、信号、skip 或 proposal。
6. 审批或拒绝 proposal，填写 reason。
7. 在 Audit 页面追踪完整事件链。
8. 确认没有任何 live order path。
