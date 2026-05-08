# Polymarket Web Terminal Agent 开发改造说明书

更新日期：2026-05-07

## 目标读者

本文面向后续接手该平台的 Codex/Claude/其他 Agent 和人类开发者。目标是降低误改安全边界、误读 mock 数据、绕过 audit contract 或破坏 F1-F8 路由模型的风险。

## 核心约束

必须遵守：

- Web 端口：`4177`
- API 端口：`8765`
- 启动服务前先检查端口。
- MVP 只允许 paper trading。
- 禁止 live trading、私钥、API secret、真实 CLOB 下单路径。
- 默认审批模式是 `manual_approval`。
- 信号必须先进入 proposal/approval queue。
- 审批后仍需重新检查 freshness、order book、risk，才能 paper fill。
- 所有 start/stop/approve/reject/kill-switch/config changes 都必须写 audit event。
- F1-F8 是完整页面路由，不是单页面内的八个聚合 panel。

## 代码结构

### Frontend

路径：`web/polymarket-terminal`

关键文件：

- `src/App.tsx`：应用入口。
- `src/components/shell/TerminalShell.tsx`：整体 terminal shell、F1-F8 键盘监听、主页面渲染。
- `src/routes/routeConfig.ts`：primary routes 和 support routes 定义。
- `src/api/client.ts`：前端 API client 和 mock fallback。
- `src/api/types.ts`：前端视图模型。
- `src/data/mockTerminalData.ts`：mock/fallback 数据。
- `src/pages/*.tsx`：F1-F8 页面和 support page。
- `src/components/ui/*.tsx`：表格、按钮、状态、图表等基础 UI。

### API

路径：`fincept-qt/scripts/polymarket_web_api`

关键文件：

- `app.py`：FastAPI app factory 和 route 定义。
- `schemas.py`：Pydantic response/request model。
- `repository.py`：SQLite read/write facade、proposal expiry、audit 写入。
- `control.py`：start/stop/kill-switch/approve/reject 控制动作。
- `requirements.txt`：API 运行依赖。

### Paper Bot

路径：`fincept-qt/scripts/algo_trading`

关键文件：

- `polymarket_config.py`：默认 bot 配置，包括 `approval_mode`。
- `polymarket_runner.py`：paper cycle、manual approval、proposal/fill 流程。
- `polymarket_store.py`：SQLite schema 和 CRUD helpers。
- `polymarket_paper.py`：paper trade/position 逻辑。
- `polymarket_risk.py`：risk checks。
- `polymarket_sources.py`：fixture/public data source helpers。

## 运行方式

安装依赖：

```powershell
python -m pip install -r fincept-qt\scripts\polymarket_web_api\requirements.txt
npm ci --prefix web\polymarket-terminal
```

端口检查：

```powershell
Get-NetTCPConnection -LocalPort 4177,8765 -ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort,State,OwningProcess
```

启动 API：

```powershell
$env:PYTHONPATH = "fincept-qt/scripts;fincept-qt/scripts/algo_trading"
$env:POLYMARKET_WEB_DB = ".polymarket-web.sqlite"
python -m uvicorn polymarket_web_api.app:create_app --factory --host 127.0.0.1 --port 8765
```

启动 Web：

```powershell
$env:VITE_POLYMARKET_API_BASE = "http://127.0.0.1:8765"
npm run dev --prefix web/polymarket-terminal -- --host 127.0.0.1 --port 4177
```

## 验证命令

后端/API：

```powershell
python -m pytest fincept-qt/scripts/algo_trading/tests fincept-qt/scripts/polymarket_web_api/tests -q --basetemp .pytest_tmp
```

前端：

```powershell
npm test --prefix web/polymarket-terminal
npm run lint --prefix web/polymarket-terminal
npm run build --prefix web/polymarket-terminal
```

E2E：

```powershell
Get-NetTCPConnection -LocalPort 4177,8765 -ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort,State,OwningProcess
npm run test:e2e --prefix web/polymarket-terminal
```

E2E 会自己启动 `8765` 和 `4177`，因此运行前端口必须为空。

## API 合约

当前 API routes：

| Method | Path | 用途 |
| --- | --- | --- |
| GET | `/api/bot/status` | paper bot/API 状态 |
| GET | `/api/audit` | audit events |
| GET | `/api/proposals` | proposal queue |
| GET | `/api/candidates` | market candidates |
| GET | `/api/signals` | signals |
| GET | `/api/skips` | skips |
| GET | `/api/trades` | paper trades |
| GET | `/api/positions` | paper positions |
| POST | `/api/control/start` | 记录 start 控制动作 |
| POST | `/api/control/stop` | 记录 stop 控制动作 |
| POST | `/api/control/kill-switch` | paper kill switch |
| POST | `/api/proposals/{proposal_id}/approve` | 审批 proposal |
| POST | `/api/proposals/{proposal_id}/reject` | 拒绝 proposal |

查询默认使用 `deployment_id=default`。新增多 deployment UI 时，必须把 deployment id 显式传入 API client。

## 数据模型要点

关键 SQLite 表：

- `algo_polymarket_trade_proposals`
- `algo_polymarket_audit_events`
- `algo_polymarket_candidates`
- `algo_polymarket_signals`
- `algo_polymarket_skips`
- `algo_polymarket_paper_trades`
- `algo_polymarket_paper_positions`

Proposal 状态：

- `proposed`
- `approved`
- `rejected`
- `expired`
- `cancelled`
- `filled`
- `failed`

Audit event 必须包含：

- deployment_id
- strategy_id
- actor_type / actor_id
- action
- entity_type / entity_id
- before / after
- result
- reason
- request_id
- created_at

不要直接从 UI 修改 audit event。修正必须追加新 event。

## Frontend 改造规则

### 路由

新增 F1-F8 主页面必须修改：

- `src/routes/routeConfig.ts`
- `src/components/shell/TerminalShell.tsx`
- 对应页面测试
- E2E keyboard route 测试

不要把 F1-F8 做成一个聚合页里的 tabs。

Support routes 可以是独立页面，也可以继续使用 disabled placeholder，但必须清楚显示禁用原因。

### API client

`src/api/client.ts` 当前会在 fetch 失败时 fallback 到 mock 数据。改造时注意：

- 会影响用户对真实数据/假数据的判断。
- 涉及审批、控制、风险的页面不得让 mock 数据触发真实 API 写操作。
- 如果新增 fallback，必须在 UI 明示来源。

推荐下一步：

- 引入统一 `DataSourceState`。
- 将 API error、mock fallback、lastUpdated 显示到 shell。
- 不要吞掉控制类 POST 的错误。

### 状态变更按钮

任何会改变后端状态的按钮都必须：

- 使用明确文案。
- 有确认流程。
- 传入 `deployment_id`、`strategy_id`、`actor_id`、`reason`。
- 成功和失败都能被 audit 追踪。
- 有测试覆盖失败状态。

### UI 文案

金融终端 UI 要避免营销化解释，优先短、清晰、可扫描。关键状态必须直说：

- paper-only
- live disabled
- mock fallback
- API unavailable
- stale data
- proposal expired

## Backend 改造规则

### Repository

API 层只通过 `PolymarketRepository` 读写 SQLite。不要让 FastAPI route 直接拼 SQL，除非是在 repository 内部。

### Proposal lifecycle

approve/reject 必须检查：

- proposal 是否存在。
- deployment_id 是否匹配。
- 当前状态是否仍是 `proposed`。
- `expires_at` 是否已过期。
- 状态更新是否成功。

失败也要写 audit event。

### Runner

manual approval 模式下：

- runner 产生 signal 后创建 proposal。
- 不得立即 paper fill。
- approved proposal 进入后续处理前，需要重新检查 freshness/order book/risk。
- paper fill 只写 paper trade/position，不接真实 CLOB 下单。

### Config

默认配置必须保持：

```python
"approval_mode": "manual_approval"
```

如果测试需要自动 paper fill，可以在 fixture 里显式设置：

```python
{"approval_mode": "auto_paper"}
```

不要把默认模式改成自动。

## 测试策略

新增行为优先使用 TDD：

- 后端状态机：pytest。
- API 合约：FastAPI TestClient。
- Frontend route/UI：Vitest + React Testing Library。
- 视觉/响应式/键盘流：Playwright。

必须覆盖的常见风险：

- explicit empty arrays 不能被当成 missing payload。
- expired proposal 不能被 approve/reject。
- mock proposal 不能触发 approve/reject。
- F1-F8 必须切完整页面。
- paper-only 文案和 NO CLOB 状态不能被移除。
- Audit event 对成功和失败控制动作都存在。

## 推荐改造路线

1. 明确 mock fallback/API live 状态。
2. 增加 Deployment/Strategy 选择器。
3. 增加 Web paper scan/start/stop 控制台。
4. 用审批 modal 替换 `window.confirm()`。
5. 增加 Audit drilldown 和导出。
6. 将 Settings/Watchlist 做成最小可用 support routes。
7. 对接更多只读数据 adapter。

每一步都应保持 paper-only，并先补测试。

## 禁止事项

Agent 不得擅自：

- 添加真实 CLOB 下单。
- 添加钱包私钥输入框。
- 添加 API secret 存储。
- 把 advisory agent 输出直接变成订单。
- 删除 audit event。
- 为了演示效果隐藏 mock fallback。
- 使用默认端口 `5173` 或 `8000` 启动服务。
- 跳过端口检查启动服务。

## PR/提交前检查

提交前至少运行：

```powershell
python -m pytest fincept-qt/scripts/algo_trading/tests fincept-qt/scripts/polymarket_web_api/tests -q --basetemp .pytest_tmp
npm test --prefix web/polymarket-terminal
npm run lint --prefix web/polymarket-terminal
npm run build --prefix web/polymarket-terminal
```

涉及页面布局、F1-F8、mobile drawer 或 dev server 时，额外运行：

```powershell
Get-NetTCPConnection -LocalPort 4177,8765 -ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort,State,OwningProcess
npm run test:e2e --prefix web/polymarket-terminal
```
