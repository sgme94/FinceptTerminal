# Polymarket Web Terminal 用户使用说明书

更新日期：2026-05-07

## 平台定位

Polymarket Web Terminal 是一个 Fincept-style 的 Polymarket paper trading 管理页面。当前版本是 MVP，目标是让用户查看候选市场、信号、proposal 审批队列、paper positions、paper trades 和 audit events。

当前版本只支持 paper trading：

- 不支持 live trading。
- 不需要私钥。
- 不需要 Polymarket API secret。
- 不会提交真实 CLOB 订单。
- 审批 proposal 只会进入 paper workflow。

## 本地启动

所有命令从仓库 worktree 根目录运行：

```powershell
cd C:\Users\x\xFinceptTerminal\.worktrees\polymarket-web-plan
```

首次使用安装依赖：

```powershell
python -m pip install -r fincept-qt\scripts\polymarket_web_api\requirements.txt
npm ci --prefix web\polymarket-terminal
```

启动前检查端口：

```powershell
Get-NetTCPConnection -LocalPort 4177,8765 -ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort,State,OwningProcess
```

如果有输出，说明端口被占用，需要先停止占用进程。

启动 API：

```powershell
$env:PYTHONPATH = "fincept-qt/scripts;fincept-qt/scripts/algo_trading"
$env:POLYMARKET_WEB_DB = ".polymarket-web.sqlite"
python -m uvicorn polymarket_web_api.app:create_app --factory --host 127.0.0.1 --port 8765
```

另开一个 PowerShell 启动 Web：

```powershell
$env:VITE_POLYMARKET_API_BASE = "http://127.0.0.1:8765"
npm run dev --prefix web/polymarket-terminal -- --host 127.0.0.1 --port 4177
```

浏览器打开：

```text
http://127.0.0.1:4177
```

## 页面导航

顶部 F1-F8 是全局主路由快捷键。按下快捷键会切换整个主页面，不是在一个 dashboard 里切换局部板块。

| 快捷键 | 页面 | 用途 |
| --- | --- | --- |
| F1 | Overview | 查看 paper bot 状态、PnL、exposure、pending proposals、recent activity |
| F2 | Markets | 查看候选市场、概率图、订单簿摘要 |
| F3 | Signals | 查看 advisory signals、feature contribution、skip reasons |
| F4 | Risk | 查看 risk limits、proposal approval queue、kill switch、skip/reject history |
| F5 | News | 查看只读 mock news feed |
| F6 | Data | 查看数据源状态、cache health、adapter placeholders |
| F7 | Agents | 查看 advisory agent placeholders 和研究 finding |
| F8 | Audit | 查看 audit events 和 trades/signals/positions/candidates/skips/proposals projection |

左侧还有 secondary/support routes：

- Strategy Arena
- Watchlist
- Dataroom
- Plans & Credits
- Settings
- Logout

这些入口当前是 MVP 占位页，行为被禁用。

## 常用工作流

### 1. 检查系统是否连上 API

打开 F1 Overview，看顶部状态：

- `Paper mode`：当前是 paper workflow。
- `Live disabled`：真实交易关闭。
- `mock fallback`：前端当前使用 mock 数据，而不是 API 数据。

也可以直接检查 API：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/bot/status" | ConvertTo-Json -Depth 5
```

期望看到：

```json
{
  "mode": "paper",
  "live_enabled": false,
  "approval_mode": "manual_approval",
  "healthy": true
}
```

### 2. 查看候选市场

进入 F2 Markets：

- 左侧 Candidate queue 展示候选市场。
- 可以按 category 过滤，也可以按 market id 或 question 搜索。
- 点击 Select 后，右侧显示 selected market detail、probability chart 和 order book summary。

注意：当前 chart 和部分 order book detail 仍可能来自 mock snapshot。看到 `mock fallback` 时，不要把它当成真实市场数据。

### 3. 查看信号和跳过原因

进入 F3 Signals：

- Signal queue 展示方向、edge、confidence、reason。
- Feature contribution 展示信号相关特征值。
- Advisory evidence 展示该信号的解释信息。
- Skip review 展示为什么某些候选没有进入 proposal 或 fill。

Signals 页面是只读页面，不提供下单按钮。

### 4. 审批或拒绝 proposal

进入 F4 Risk：

- Proposal approval queue 展示待审批 proposal。
- 只有 API 来源、状态为 `proposed`、且未 stale 的 proposal 会显示 Approve/Reject。
- 点击 Approve 或 Reject 会弹出浏览器确认框。
- 审批或拒绝后，系统写入 audit event。

审批注意事项：

- 当前审批理由是固定文本，不支持用户手动输入。
- 如果 proposal 已过期，API 会拒绝审批并写 audit event。
- 审批 proposal 不代表真实下单，只是 paper workflow 的状态变更。

### 5. 使用 paper kill switch

进入 F4 Risk，点击 Paper kill switch。

当前 kill switch 会：

- 写入 `kill_switch` audit event。
- 将 open proposals 取消为 `cancelled`。
- 不会触发真实订单取消，因为 MVP 没有真实下单路径。

### 6. 查看审计记录

进入 F8 Audit：

- 上方 Audit event list 展示 append-only audit events。
- 可以按 deployment、action、result 做基础过滤。
- 下方 tabs 可以切换 trades、signals、positions、candidates、skips、proposals。

Audit events 是追加式记录。错误修正应写入新 event，而不是编辑旧 event。

## 数据和状态说明

常见状态含义：

| 状态 | 含义 |
| --- | --- |
| paper | paper trading 模式 |
| live disabled | 不允许真实交易 |
| manual_approval | 信号先进入 proposal queue，需要审批 |
| proposed | proposal 等待审批 |
| approved | proposal 已被用户审批 |
| rejected | proposal 已被用户拒绝 |
| expired | proposal 超过有效期 |
| cancelled | proposal 被 kill switch 或控制动作取消 |
| filled | paper fill 已记录 |
| mock fallback | 前端正在使用 mock 数据 |

## 当前限制

当前版本仍有这些限制：

- 没有 Web 内的一键创建 strategy/deployment。
- 没有 Web 内的一键运行 paper scan cycle。
- Start/Stop API 已存在，但 Web 页面还没有完整控制台。
- News、Data、Agents 多数是 mock/read-only placeholders。
- Support routes 仍是 disabled placeholders。
- Audit 过滤选项不完整，暂不支持导出。
- 审批 modal 还不是应用内表单，不能输入自定义 reason。

## 排错

### 页面打不开

检查 Web 端口：

```powershell
Get-NetTCPConnection -LocalPort 4177 -ErrorAction SilentlyContinue
```

如果没有监听，重新启动前端。

### API 不健康

检查 API：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/bot/status"
```

如果失败，检查 API 启动时是否设置了：

```powershell
$env:PYTHONPATH = "fincept-qt/scripts;fincept-qt/scripts/algo_trading"
$env:POLYMARKET_WEB_DB = ".polymarket-web.sqlite"
```

### 页面显示 mock fallback

说明前端请求 API 失败或 API 没有对应数据。先检查 API 是否启动，再检查浏览器控制台或 API 日志。

### 需要停止服务

如果知道进程号：

```powershell
Stop-Process -Id <pid> -Force
```

如果只知道端口：

```powershell
Get-NetTCPConnection -LocalPort 4177,8765 | Select-Object LocalPort,OwningProcess
```

再停止对应 `OwningProcess`。

## 安全提醒

不要在当前平台输入或保存：

- 钱包私钥
- Polymarket API secret
- CLOB 下单凭证
- 真实资金账户配置

如果未来要增加 live trading，必须另写 spec、risk controls、secret management、audit contract、dry-run verification 和人工确认流程。当前 MVP 不包含这些能力。
