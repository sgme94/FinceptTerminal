# Polymarket Web Terminal MVP Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first Web MVP of a Fincept-style Polymarket paper-bot terminal with persistent shell, F1-F8 full-page routing, proposal approval, audit logging, and paper-bot status views.

**Architecture:** Add a new isolated Web frontend under `web/polymarket-terminal/` and a Python API facade under `fincept-qt/scripts/polymarket_web_api/`. The Web app never calls runner internals directly; it calls API endpoints that read/write SQLite-backed proposal, audit, signal, position, trade, and candidate state.

**Tech Stack:** Vite, React, TypeScript, lightweight-charts, Vitest, Playwright, Python 3, FastAPI, Uvicorn, pytest, SQLite.

---

## References

- Spec: `docs/superpowers/specs/2026-05-06-polymarket-web-research-architecture-design.md`
- Frontend reference package: `docs/fincept-logged-in-frontend-reference-2026-05-06/`
- Existing paper bot modules: `fincept-qt/scripts/algo_trading/polymarket_*.py`
- Baseline test command: `python -m pytest fincept-qt/scripts/algo_trading/tests -q --basetemp .pytest_tmp`

## Scope Check

This plan covers one MVP slice:

- Paper trading only.
- No live CLOB order placement.
- No private keys or Polymarket API credentials.
- No billing/credits flow.
- External projects are represented by adapter interfaces or mock/read-only panels only.

The MVP is still split into two independently testable layers:

- Python persistence/API/control layer.
- React terminal UI layer.

## Non-Default Ports

Before starting any service, check that the configured ports are free:

```powershell
Get-NetTCPConnection -LocalPort 4177,8765 -ErrorAction SilentlyContinue
```

Use:

- Web frontend: `http://localhost:4177`
- API facade: `http://localhost:8765`

Do not use Vite default `5173` or Uvicorn/FastAPI default `8000`.

## File Structure

### Python API and Bot State

- Modify: `fincept-qt/scripts/algo_trading/polymarket_config.py`
  - Add approval mode defaults.
- Modify: `fincept-qt/scripts/algo_trading/polymarket_runner.py`
  - Add manual approval path that creates proposals before paper fills.
- Modify: `fincept-qt/scripts/algo_trading/polymarket_store.py`
  - Add proposal and audit schemas plus CRUD helpers.
- Test: `fincept-qt/scripts/algo_trading/tests/test_polymarket_proposals_audit.py`
  - Proposal lifecycle and audit persistence.
- Test: `fincept-qt/scripts/algo_trading/tests/test_polymarket_runner_manual_approval.py`
  - Runner creates proposals without immediate fills.

Create API package:

- Create: `fincept-qt/scripts/polymarket_web_api/__init__.py`
- Create: `fincept-qt/scripts/polymarket_web_api/app.py`
- Create: `fincept-qt/scripts/polymarket_web_api/repository.py`
- Create: `fincept-qt/scripts/polymarket_web_api/schemas.py`
- Create: `fincept-qt/scripts/polymarket_web_api/control.py`
- Create: `fincept-qt/scripts/polymarket_web_api/requirements.txt`
- Test: `fincept-qt/scripts/polymarket_web_api/tests/test_api_routes.py`

### Web Frontend

Create app:

- Create: `web/polymarket-terminal/package.json`
- Create: `web/polymarket-terminal/vite.config.ts`
- Create: `web/polymarket-terminal/tsconfig.json`
- Create: `web/polymarket-terminal/index.html`
- Create: `web/polymarket-terminal/src/main.tsx`
- Create: `web/polymarket-terminal/src/App.tsx`
- Create: `web/polymarket-terminal/src/styles/tokens.css`
- Create: `web/polymarket-terminal/src/styles/terminal.css`

Create route and data modules:

- Create: `web/polymarket-terminal/src/routes/routeConfig.ts`
- Create: `web/polymarket-terminal/src/api/client.ts`
- Create: `web/polymarket-terminal/src/api/types.ts`
- Create: `web/polymarket-terminal/src/data/mockTerminalData.ts`

Create shell components:

- Create: `web/polymarket-terminal/src/components/shell/TerminalShell.tsx`
- Create: `web/polymarket-terminal/src/components/shell/FunctionKeyBar.tsx`
- Create: `web/polymarket-terminal/src/components/shell/IconRail.tsx`
- Create: `web/polymarket-terminal/src/components/shell/MobileDrawer.tsx`
- Create: `web/polymarket-terminal/src/components/shell/MarketTickerTape.tsx`
- Create: `web/polymarket-terminal/src/components/shell/RightRail.tsx`
- Create: `web/polymarket-terminal/src/components/shell/BottomStatusBar.tsx`

Create shared UI:

- Create: `web/polymarket-terminal/src/components/ui/TerminalButton.tsx`
- Create: `web/polymarket-terminal/src/components/ui/DenseDataTable.tsx`
- Create: `web/polymarket-terminal/src/components/ui/StatusPill.tsx`
- Create: `web/polymarket-terminal/src/components/ui/EmptyStatePanel.tsx`
- Create: `web/polymarket-terminal/src/components/ui/ProbabilityChart.tsx`
- Create: `web/polymarket-terminal/src/components/ui/OrderBookSummary.tsx`

Create pages:

- Create: `web/polymarket-terminal/src/pages/OverviewPage.tsx`
- Create: `web/polymarket-terminal/src/pages/MarketsPage.tsx`
- Create: `web/polymarket-terminal/src/pages/SignalsPage.tsx`
- Create: `web/polymarket-terminal/src/pages/RiskPage.tsx`
- Create: `web/polymarket-terminal/src/pages/NewsPage.tsx`
- Create: `web/polymarket-terminal/src/pages/DataPage.tsx`
- Create: `web/polymarket-terminal/src/pages/AgentsPage.tsx`
- Create: `web/polymarket-terminal/src/pages/AuditPage.tsx`
- Create: `web/polymarket-terminal/src/pages/support/StrategyArenaPage.tsx`
- Create: `web/polymarket-terminal/src/pages/support/SettingsPage.tsx`

Create frontend tests:

- Test: `web/polymarket-terminal/src/routes/routeConfig.test.ts`
- Test: `web/polymarket-terminal/src/components/shell/FunctionKeyBar.test.tsx`
- Test: `web/polymarket-terminal/src/components/shell/TerminalShell.test.tsx`
- Test: `web/polymarket-terminal/tests/polymarket-terminal.spec.ts`

---

### Task 1: Add Proposal and Audit Persistence

**Files:**
- Modify: `fincept-qt/scripts/algo_trading/polymarket_store.py`
- Test: `fincept-qt/scripts/algo_trading/tests/test_polymarket_proposals_audit.py`

- [ ] **Step 1: Write failing proposal/audit schema tests**

Create `fincept-qt/scripts/algo_trading/tests/test_polymarket_proposals_audit.py`:

```python
import sqlite3

from polymarket_models import SignalDecision
from polymarket_store import (
    ensure_polymarket_schema,
    list_audit_events,
    list_trade_proposals,
    record_audit_event,
    record_trade_proposal,
    update_trade_proposal_status,
)


def test_trade_proposal_lifecycle_is_persisted():
    conn = sqlite3.connect(":memory:")
    ensure_polymarket_schema(conn)

    signal = SignalDecision(
        asset_id="asset-1",
        action="buy",
        entry_price=0.42,
        estimated_probability=0.55,
        edge=0.13,
        confidence=0.72,
        reason="edge_threshold_met",
        features={"momentum": 0.2},
    )

    proposal_id = record_trade_proposal(
        conn,
        deployment_id="dep-1",
        strategy_id="strat-1",
        market_id="market-1",
        condition_id="cond-1",
        signal=signal,
        size=10.0,
        now="2026-05-06T00:00:00Z",
        expires_at="2026-05-06T00:01:00Z",
    )
    update_trade_proposal_status(
        conn,
        proposal_id=proposal_id,
        status="approved",
        decided_by="user",
        decided_at="2026-05-06T00:00:10Z",
        decision_reason="manual approval",
    )

    proposals = list_trade_proposals(conn, deployment_id="dep-1")
    assert len(proposals) == 1
    assert proposals[0]["proposal_id"] == proposal_id
    assert proposals[0]["status"] == "approved"
    assert proposals[0]["edge"] == 0.13


def test_audit_events_are_append_only_records():
    conn = sqlite3.connect(":memory:")
    ensure_polymarket_schema(conn)

    event_id = record_audit_event(
        conn,
        deployment_id="dep-1",
        strategy_id="strat-1",
        actor_type="user",
        actor_id="local-user",
        action="approve",
        entity_type="proposal",
        entity_id="proposal-1",
        before={"status": "proposed"},
        after={"status": "approved"},
        result="success",
        reason="manual approval",
        request_id="req-1",
        now="2026-05-06T00:00:10Z",
    )

    events = list_audit_events(conn, deployment_id="dep-1")
    assert len(events) == 1
    assert events[0]["event_id"] == event_id
    assert events[0]["action"] == "approve"
    assert events[0]["after"]["status"] == "approved"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest fincept-qt/scripts/algo_trading/tests/test_polymarket_proposals_audit.py -q --basetemp .pytest_tmp
```

Expected: FAIL because proposal/audit helpers do not exist.

- [ ] **Step 3: Add proposal and audit tables/helpers**

Modify `ensure_polymarket_schema()` in `polymarket_store.py` to create:

- `algo_polymarket_trade_proposals`
- `algo_polymarket_audit_events`

Add helpers:

- `record_trade_proposal(...) -> str`
- `update_trade_proposal_status(...) -> None`
- `list_trade_proposals(...) -> list[dict]`
- `record_audit_event(...) -> str`
- `list_audit_events(...) -> list[dict]`

Use UUID strings for `proposal_id` and `event_id`. Store JSON fields as text and deserialize in list helpers.

- [ ] **Step 4: Run proposal/audit tests**

Run:

```powershell
python -m pytest fincept-qt/scripts/algo_trading/tests/test_polymarket_proposals_audit.py -q --basetemp .pytest_tmp
```

Expected: PASS.

- [ ] **Step 5: Run existing paper-bot tests**

Run:

```powershell
python -m pytest fincept-qt/scripts/algo_trading/tests -q --basetemp .pytest_tmp
```

Expected: `34+ passed`, no regressions.

- [ ] **Step 6: Commit**

```powershell
git add fincept-qt/scripts/algo_trading/polymarket_store.py fincept-qt/scripts/algo_trading/tests/test_polymarket_proposals_audit.py
git commit -m "feat: add polymarket proposal and audit storage"
```

---

### Task 2: Add Manual Approval Mode to the Paper Runner

**Files:**
- Modify: `fincept-qt/scripts/algo_trading/polymarket_config.py`
- Modify: `fincept-qt/scripts/algo_trading/polymarket_runner.py`
- Test: `fincept-qt/scripts/algo_trading/tests/test_polymarket_runner_manual_approval.py`

- [ ] **Step 1: Write failing manual approval runner test**

Create `test_polymarket_runner_manual_approval.py`:

```python
import sqlite3

from polymarket_runner import run_polymarket_cycle
from polymarket_store import ensure_polymarket_schema, list_trade_proposals


def test_manual_approval_creates_proposal_without_fill(tmp_path):
    db_path = tmp_path / "bot.db"
    conn = sqlite3.connect(db_path)
    ensure_polymarket_schema(conn)
    conn.execute(
        "CREATE TABLE algo_strategies (id TEXT PRIMARY KEY, bot_config TEXT)"
    )
    conn.execute(
        "INSERT INTO algo_strategies (id, bot_config) VALUES (?, ?)",
        (
            "strat-1",
            '{"approval_mode":"manual_approval","paper_order_size":10,"min_edge":0.01}',
        ),
    )
    conn.commit()
    conn.close()

    market_payload = {
        "fetched_at": "2026-05-06T00:00:00Z",
        "data": [
            {
                "id": "market-1",
                "conditionId": "cond-1",
                "question": "Will event happen?",
                "active": True,
                "closed": False,
                "volume": 10000,
                "liquidity": 5000,
                "endDate": "2026-06-06T00:00:00Z",
                "tokens": [{"token_id": "asset-1", "outcome": "Yes", "price": 0.4}],
            }
        ],
    }
    order_books = {
        "asset-1": {
            "source_api": "fixture",
            "fetched_at": "2026-05-06T00:00:00Z",
            "data": {
                "asset_id": "asset-1",
                "bids": [{"price": "0.39", "size": "100"}],
                "asks": [{"price": "0.40", "size": "100"}],
            },
        }
    }
    edge_overrides = {
        "asset-1": {
            "action": "buy",
            "reason": "test_override",
            "estimated_probability": 0.55,
            "edge": 0.15,
            "confidence": 0.8,
        }
    }

    result = run_polymarket_cycle(
        db_path=str(db_path),
        deployment_id="dep-1",
        strategy_id="strat-1",
        market_payload=market_payload,
        order_books=order_books,
        edge_overrides=edge_overrides,
        now="2026-05-06T00:00:00Z",
    )

    conn = sqlite3.connect(db_path)
    proposals = list_trade_proposals(conn, deployment_id="dep-1")
    trades = conn.execute(
        "SELECT COUNT(*) FROM algo_polymarket_paper_trades"
    ).fetchone()[0]
    conn.close()

    assert result["proposals"] == 1
    assert result["fills"] == 0
    assert len(proposals) == 1
    assert proposals[0]["status"] == "proposed"
    assert trades == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest fincept-qt/scripts/algo_trading/tests/test_polymarket_runner_manual_approval.py -q --basetemp .pytest_tmp
```

Expected: FAIL because approval mode is not implemented.

- [ ] **Step 3: Add config default**

Modify `default_bot_config()` in `polymarket_config.py` to include:

```python
"approval_mode": "manual_approval",
"proposal_ttl_sec": 60,
```

- [ ] **Step 4: Add runner proposal path**

Modify `_process_entries()` in `polymarket_runner.py`:

- After `check_entry_risk(...)` passes, check `cfg["approval_mode"]`.
- If `manual_approval`, call `record_trade_proposal(...)`, record an audit event, increment `result["proposals"]`, and `continue`.
- If `auto_paper`, keep current fill behavior.

- [ ] **Step 5: Run manual approval test**

Run:

```powershell
python -m pytest fincept-qt/scripts/algo_trading/tests/test_polymarket_runner_manual_approval.py -q --basetemp .pytest_tmp
```

Expected: PASS.

- [ ] **Step 6: Run all paper-bot tests**

Run:

```powershell
python -m pytest fincept-qt/scripts/algo_trading/tests -q --basetemp .pytest_tmp
```

Expected: all tests pass. If older tests assumed immediate fills by default, update those fixtures to set `"approval_mode":"auto_paper"` explicitly.

- [ ] **Step 7: Commit**

```powershell
git add fincept-qt/scripts/algo_trading/polymarket_config.py fincept-qt/scripts/algo_trading/polymarket_runner.py fincept-qt/scripts/algo_trading/tests/test_polymarket_runner_manual_approval.py
git commit -m "feat: add manual approval mode for polymarket paper bot"
```

---

### Task 3: Add Python API Facade

**Files:**
- Create: `fincept-qt/scripts/polymarket_web_api/__init__.py`
- Create: `fincept-qt/scripts/polymarket_web_api/app.py`
- Create: `fincept-qt/scripts/polymarket_web_api/repository.py`
- Create: `fincept-qt/scripts/polymarket_web_api/schemas.py`
- Create: `fincept-qt/scripts/polymarket_web_api/control.py`
- Create: `fincept-qt/scripts/polymarket_web_api/requirements.txt`
- Test: `fincept-qt/scripts/polymarket_web_api/tests/test_api_routes.py`

- [ ] **Step 1: Add API dependencies**

Create `requirements.txt`:

```text
fastapi>=0.115
uvicorn[standard]>=0.30
pydantic>=2
pytest>=8
```

- [ ] **Step 2: Install API dependencies**

Run:

```powershell
python -m pip install -r fincept-qt/scripts/polymarket_web_api/requirements.txt
```

Expected: FastAPI, Uvicorn, Pydantic, and pytest are available in the active Python environment.

- [ ] **Step 3: Write failing API route tests**

Create `test_api_routes.py` using FastAPI `TestClient`:

```python
import sqlite3
import sys
from pathlib import Path

from fastapi.testclient import TestClient

SCRIPT_ROOT = Path(__file__).resolve().parents[2]
ALGO_ROOT = SCRIPT_ROOT / "algo_trading"
for path in (SCRIPT_ROOT, ALGO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from polymarket_web_api.app import create_app
from polymarket_store import ensure_polymarket_schema, record_audit_event


def test_status_route_returns_terminal_status(tmp_path):
    db_path = tmp_path / "bot.db"
    conn = sqlite3.connect(db_path)
    ensure_polymarket_schema(conn)
    conn.close()

    client = TestClient(create_app(db_path=str(db_path)))
    response = client.get("/api/bot/status")

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "paper"
    assert body["live_enabled"] is False


def test_audit_route_returns_events(tmp_path):
    db_path = tmp_path / "bot.db"
    conn = sqlite3.connect(db_path)
    ensure_polymarket_schema(conn)
    record_audit_event(
        conn,
        deployment_id="dep-1",
        strategy_id="strat-1",
        actor_type="user",
        actor_id="local-user",
        action="start",
        entity_type="deployment",
        entity_id="dep-1",
        before={},
        after={"status": "running"},
        result="success",
        reason="start paper bot",
        request_id="req-1",
        now="2026-05-06T00:00:00Z",
    )
    conn.commit()
    conn.close()

    client = TestClient(create_app(db_path=str(db_path)))
    response = client.get("/api/audit?deployment_id=dep-1")

    assert response.status_code == 200
    assert response.json()["events"][0]["action"] == "start"
```

- [ ] **Step 4: Run test to verify it fails**

Run:

```powershell
python -m pytest fincept-qt/scripts/polymarket_web_api/tests -q --basetemp .pytest_tmp
```

Expected: FAIL because API package does not exist.

- [ ] **Step 5: Implement schemas and repository**

Implement `schemas.py` with Pydantic models:

- `BotStatus`
- `AuditEvent`
- `AuditEventList`
- `Proposal`
- `ProposalList`
- `ControlActionRequest`
- `ControlActionResponse`

Implement `repository.py` as a thin SQLite wrapper that calls `polymarket_store` helpers and returns dictionaries.

- [ ] **Step 6: Implement FastAPI app**

Implement `app.py` with:

```python
import os


def create_app(*, db_path: str | None = None) -> FastAPI:
    db_path = db_path or os.environ.get("POLYMARKET_WEB_DB", ".polymarket-web.sqlite")
    app = FastAPI(title="Polymarket Web Terminal API")
    ...
    return app
```

Required MVP endpoints:

- `GET /api/bot/status`
- `GET /api/audit`
- `GET /api/proposals`
- `POST /api/control/start`
- `POST /api/control/stop`
- `POST /api/proposals/{proposal_id}/approve`
- `POST /api/proposals/{proposal_id}/reject`

All control endpoints must call `record_audit_event(...)`.

- [ ] **Step 7: Run API tests**

Run:

```powershell
python -m pytest fincept-qt/scripts/polymarket_web_api/tests -q --basetemp .pytest_tmp
```

Expected: PASS.

- [ ] **Step 8: Run all Python tests**

Run:

```powershell
python -m pytest fincept-qt/scripts/algo_trading/tests fincept-qt/scripts/polymarket_web_api/tests -q --basetemp .pytest_tmp
```

Expected: all tests pass.

- [ ] **Step 9: Commit**

```powershell
git add fincept-qt/scripts/polymarket_web_api fincept-qt/scripts/algo_trading/polymarket_store.py
git commit -m "feat: add polymarket web api facade"
```

---

### Task 4: Scaffold the Web Terminal App

**Files:**
- Create all files under `web/polymarket-terminal/`

- [ ] **Step 1: Create package metadata**

Create `web/polymarket-terminal/package.json`:

```json
{
  "name": "polymarket-terminal",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite --host 127.0.0.1 --port 4177",
    "build": "tsc -b && vite build",
    "test": "vitest run",
    "test:e2e": "playwright test",
    "lint": "tsc -b --noEmit"
  },
  "dependencies": {
    "@vitejs/plugin-react": "^5.0.0",
    "vite": "^7.0.0",
    "typescript": "^5.8.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "lucide-react": "^0.468.0",
    "lightweight-charts": "^5.0.0"
  },
  "devDependencies": {
    "@playwright/test": "^1.50.0",
    "@testing-library/jest-dom": "^6.6.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/user-event": "^14.6.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "jsdom": "^25.0.0",
    "vitest": "^2.1.0"
  }
}
```

- [ ] **Step 2: Create Vite/TS config**

Create:

- `vite.config.ts` with React plugin and dev server port `4177`.
- `tsconfig.json` with strict mode.
- `index.html` mounting `#root`.

- [ ] **Step 3: Create minimal app**

Create `src/main.tsx`, `src/App.tsx`, and base CSS files. The app should render a black terminal shell placeholder.

- [ ] **Step 4: Install frontend dependencies**

Run:

```powershell
npm install --prefix web/polymarket-terminal
```

Expected: installs dependencies and creates `web/polymarket-terminal/package-lock.json`.

- [ ] **Step 5: Run frontend build**

Run:

```powershell
npm run build --prefix web/polymarket-terminal
```

Expected: build succeeds.

- [ ] **Step 6: Commit**

```powershell
git add web/polymarket-terminal
git commit -m "feat: scaffold polymarket web terminal"
```

---

### Task 5: Implement Shell and F1-F8 Routing

**Files:**
- Create/modify route and shell files under `web/polymarket-terminal/src/`
- Test: `routeConfig.test.ts`, `FunctionKeyBar.test.tsx`, `TerminalShell.test.tsx`

- [ ] **Step 1: Write route config tests**

Test requirements:

- Exactly eight primary routes.
- F1-F8 map to Overview, Markets, Signals, Risk, News, Data, Agents, Audit.
- Support entries exist but do not have F-key shortcuts.

- [ ] **Step 2: Implement `routeConfig.ts`**

Define:

```ts
export type PrimaryRouteId =
  | "overview"
  | "markets"
  | "signals"
  | "risk"
  | "news"
  | "data"
  | "agents"
  | "audit";

export const primaryRoutes = [...]
export const supportRoutes = [...]
```

Support routes:

- `strategy-arena`
- `watchlist`
- `dataroom`
- `plans-credits`
- `settings`
- `logout`

- [ ] **Step 3: Write shell interaction tests**

Test:

- Clicking `F2 Markets` renders Markets page.
- Pressing keyboard `F4` renders Risk page.
- Left rail active state follows route.
- Drawer route selection uses same route list.

- [ ] **Step 4: Implement shell components**

Implement:

- `TerminalShell`
- `FunctionKeyBar`
- `IconRail`
- `MobileDrawer`
- `MarketTickerTape`
- `RightRail`
- `BottomStatusBar`

Use native buttons and `aria-current`.

- [ ] **Step 5: Run frontend tests**

Run:

```powershell
npm test --prefix web/polymarket-terminal
```

Expected: PASS.

- [ ] **Step 6: Run build**

Run:

```powershell
npm run build --prefix web/polymarket-terminal
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add web/polymarket-terminal/src
git commit -m "feat: add terminal shell routing"
```

---

### Task 6: Implement Mock Data Layer and Shared UI

**Files:**
- Create: `src/api/types.ts`
- Create: `src/api/client.ts`
- Create: `src/data/mockTerminalData.ts`
- Create shared UI components.

- [ ] **Step 1: Define frontend API types**

Types must match API concepts:

- `BotStatus`
- `MarketCandidate`
- `SignalRow`
- `TradeProposal`
- `AuditEvent`
- `RiskLimit`
- `TerminalStatus`

- [ ] **Step 2: Implement API client with mock fallback**

`client.ts` should:

- Use `VITE_POLYMARKET_API_BASE`, defaulting to `http://localhost:8765`.
- Return mock data if API request fails.
- Mark fallback data with `source: "mock"` or `stale: true`.

- [ ] **Step 3: Implement shared UI**

Implement:

- `TerminalButton`
- `DenseDataTable`
- `StatusPill`
- `EmptyStatePanel`
- `ProbabilityChart`
- `OrderBookSummary`

`ProbabilityChart` must use `lightweight-charts`.

- [ ] **Step 4: Add tests for API fallback and route-safe UI**

Test:

- API client returns mock data on failed fetch.
- `DenseDataTable` renders empty state.
- `ProbabilityChart` renders non-empty container.

- [ ] **Step 5: Run tests/build**

Run:

```powershell
npm test --prefix web/polymarket-terminal
npm run build --prefix web/polymarket-terminal
```

Expected: both pass.

- [ ] **Step 6: Commit**

```powershell
git add web/polymarket-terminal/src
git commit -m "feat: add terminal data and ui primitives"
```

---

### Task 7: Implement Overview and Audit Pages

**Files:**
- Create/modify: `OverviewPage.tsx`
- Create/modify: `AuditPage.tsx`
- API endpoints from Task 3.

- [ ] **Step 1: Write page tests**

Test:

- Overview displays paper mode, live disabled, PnL, positions, and recent skips.
- Audit displays control actions and proposal transitions.

- [ ] **Step 2: Implement Overview**

Sections:

- Bot status header.
- Paper/live mode display with live disabled.
- PnL and exposure metrics.
- Open positions table.
- Pending proposals preview.
- Recent signals/fills/skips.
- Agent composer placeholder.

- [ ] **Step 3: Implement Audit**

Sections:

- Filters for deployment/action/result.
- Audit event list.
- Trades/signals/proposals tabs.
- Append-only warning.

- [ ] **Step 4: Run tests/build**

Run frontend and Python API tests.

- [ ] **Step 5: Commit**

```powershell
git add web/polymarket-terminal/src fincept-qt/scripts/polymarket_web_api
git commit -m "feat: add overview and audit pages"
```

---

### Task 8: Implement Markets, Signals, and Risk Pages

**Files:**
- Modify: `MarketsPage.tsx`
- Modify: `SignalsPage.tsx`
- Modify: `RiskPage.tsx`
- Create/modify API endpoints for candidates/signals/proposals.

- [ ] **Step 1: Write page tests**

Test:

- Markets renders candidates, selected market detail, chart, and order book.
- Signals renders edge, confidence, reason, and skip rows.
- Risk renders proposal statuses: proposed, approved, rejected, expired, cancelled, filled, failed.

- [ ] **Step 2: Implement Markets**

Use Fincept-style dense layout:

- Filter strip.
- Candidate table.
- Selected market detail.
- Probability chart.
- Order book summary.

- [ ] **Step 3: Implement Signals**

Use:

- Signal table.
- Feature contribution panel.
- Advisory evidence panel.
- Source freshness badges.

- [ ] **Step 4: Implement Risk**

Use:

- Risk limits summary.
- Proposal approval queue.
- Explicit approve/reject confirmation.
- Kill switch confirmation.
- Skip/reject history.

Approve/reject calls must write audit events through API.

- [ ] **Step 5: Run tests/build**

Run:

```powershell
npm test --prefix web/polymarket-terminal
npm run build --prefix web/polymarket-terminal
python -m pytest fincept-qt/scripts/algo_trading/tests fincept-qt/scripts/polymarket_web_api/tests -q --basetemp .pytest_tmp
```

Expected: all pass.

- [ ] **Step 6: Commit**

```powershell
git add web/polymarket-terminal/src fincept-qt/scripts/polymarket_web_api
git commit -m "feat: add markets signals and risk pages"
```

---

### Task 9: Implement Support Pages and Right Rail

**Files:**
- Modify: `NewsPage.tsx`
- Modify: `DataPage.tsx`
- Modify: `AgentsPage.tsx`
- Create support pages.
- Modify: `RightRail.tsx`

- [ ] **Step 1: Write tests**

Test:

- News/Data/Agents pages render functional placeholder/advisory states.
- Support route entries render placeholder/disabled behavior.
- Right rail failure state does not block main page.

- [ ] **Step 2: Implement News**

Use mock/adapted feed data:

- Dense news list.
- Impact tags.
- Source freshness.

- [ ] **Step 3: Implement Data**

Show:

- Polymarket source status.
- OpenBB/public-apis/Sherlock adapter placeholders.
- Cache health.
- Dataroom disabled placeholder.

- [ ] **Step 4: Implement Agents**

Show:

- Event sentinels.
- Research cycles.
- Findings/dissent/confidence.
- TradingAgents/dexter/MiroFish placeholders.

- [ ] **Step 5: Implement RightRail**

Sections:

- Live News.
- Watchlist.
- Most Active.
- Risk Alerts.

Each section must support empty/error state.

- [ ] **Step 6: Run tests/build and commit**

```powershell
npm test --prefix web/polymarket-terminal
npm run build --prefix web/polymarket-terminal
git add web/polymarket-terminal/src
git commit -m "feat: add support pages and right rail"
```

---

### Task 10: Add Playwright Visual Verification

**Files:**
- Create: `web/polymarket-terminal/playwright.config.ts`
- Create: `web/polymarket-terminal/tests/polymarket-terminal.spec.ts`

- [ ] **Step 1: Write Playwright tests**

Test:

- Desktop `1700 x 900` loads shell.
- Mobile `390 x 844` loads drawer.
- No horizontal overflow on both viewports.
- Pressing F1-F8 changes route page title.
- Right rail is present on desktop and absent/collapsed on mobile.

- [ ] **Step 2: Start services on non-default ports**

Check ports:

```powershell
Get-NetTCPConnection -LocalPort 4177,8765 -ErrorAction SilentlyContinue
```

Start API:

```powershell
$env:PYTHONPATH = "fincept-qt/scripts;fincept-qt/scripts/algo_trading"
$env:POLYMARKET_WEB_DB = ".polymarket-web.sqlite"
python -m uvicorn polymarket_web_api.app:create_app --factory --host 127.0.0.1 --port 8765
```

Start frontend:

```powershell
npm run dev --prefix web/polymarket-terminal
```

If either port is occupied, stop the known project process or use explicit alternate ports and update test config.

- [ ] **Step 3: Run Playwright**

Run:

```powershell
npm run test:e2e --prefix web/polymarket-terminal
```

Expected: PASS.

- [ ] **Step 4: Commit**

```powershell
git add web/polymarket-terminal
git commit -m "test: add polymarket terminal visual verification"
```

---

### Task 11: Final Verification and Documentation

**Files:**
- Modify: `README.md` or create `web/polymarket-terminal/README.md`
- Modify: `docs/superpowers/specs/2026-05-06-polymarket-web-research-architecture-design.md` only if implementation discoveries require spec updates.

- [ ] **Step 1: Document local run commands**

Create `web/polymarket-terminal/README.md` with:

- Install command.
- API start command on port `8765`, including `PYTHONPATH` for `fincept-qt/scripts` and `fincept-qt/scripts/algo_trading`.
- Frontend start command on port `4177`.
- Test commands.
- Paper-only safety note.

- [ ] **Step 2: Run full verification**

Run:

```powershell
python -m pytest fincept-qt/scripts/algo_trading/tests fincept-qt/scripts/polymarket_web_api/tests -q --basetemp .pytest_tmp
npm test --prefix web/polymarket-terminal
npm run build --prefix web/polymarket-terminal
npm run test:e2e --prefix web/polymarket-terminal
```

Expected:

- Python tests pass.
- Vitest tests pass.
- Frontend build passes.
- Playwright passes.

- [ ] **Step 3: Review git diff**

Run:

```powershell
git status --short
git diff --stat
```

Expected: only intentional implementation files are modified.

- [ ] **Step 4: Commit docs**

```powershell
git add web/polymarket-terminal/README.md
git commit -m "docs: add polymarket web terminal runbook"
```

---

## Execution Notes

- Keep each task as a separate commit.
- Do not add live trading.
- Do not add secrets or credential forms.
- Do not hardcode scraped real-time prices or account details.
- Keep `manual_approval` as the Web default.
- When starting the API from the repo root, set `PYTHONPATH` to include `fincept-qt/scripts` and `fincept-qt/scripts/algo_trading`.
- If a dependency version has changed, use current official package documentation and update this plan before implementing that task.
- If frontend visual changes are made, verify in the browser at `1700 x 900` and `390 x 844`.
