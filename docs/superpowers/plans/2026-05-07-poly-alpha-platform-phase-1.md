# Poly Alpha Platform Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Poly Alpha Phase 1 as an opportunity-lifecycle-first, paper-only alpha discovery and validation layer inside the existing Polymarket Web Terminal.

**Architecture:** Add focused Poly Alpha modules under `fincept-qt/scripts/algo_trading/`, expose them through the existing FastAPI facade under `fincept-qt/scripts/polymarket_web_api/`, and surface the lifecycle in the existing React terminal pages. Phase 1 uses deterministic opportunity discovery and evidence packs before agent review, records first-class no-trade attribution, validates shadow signals, promotes only gate-passing signals into the existing manual approval paper proposal flow, and keeps all live trading paths absent.

**Tech Stack:** Python 3, SQLite, FastAPI, Pydantic, pytest, Vite, React, TypeScript, Vitest, Playwright.

---

## References

- Spec: `docs/superpowers/specs/2026-05-07-poly-alpha-platform-phase-1-design.md`
- Existing API facade: `fincept-qt/scripts/polymarket_web_api/`
- Existing paper bot store/runner: `fincept-qt/scripts/algo_trading/polymarket_*.py`
- Existing frontend: `web/polymarket-terminal/`
- Required ports when running services: Web `4177`, API `8765`

## Scope Check

The spec is broad but plannable as vertical slices. Do not try to implement all future multi-market adapters. Phase 1 implements the generic model and a Polymarket-focused adapter surface, with `cross_market_probability` as the primary execution path. `event_lag` and `resolution_rules` are supported as stored strategy families and evidence fields, but they do not need standalone full validation engines in Phase 1.

Non-negotiable constraints:

- Paper-only.
- No private keys.
- No API secrets.
- No authenticated CLOB order clients.
- No real CLOB order endpoint.
- No live trading mode toggle.
- F1-F8 stay full-page route shortcuts.

## File Structure

### Python Core

- Create: `fincept-qt/scripts/algo_trading/poly_alpha_config.py`
  - Versioned default config values and constants.
- Create: `fincept-qt/scripts/algo_trading/poly_alpha_models.py`
  - Dataclasses/enums and lifecycle transition helpers.
- Create: `fincept-qt/scripts/algo_trading/poly_alpha_store.py`
  - SQLite schema, CRUD helpers, and query helpers.
- Create: `fincept-qt/scripts/algo_trading/poly_alpha_scanner.py`
  - Deterministic scan result, opportunity, evidence pack, snapshot, and exploration-gate helpers.
- Create: `fincept-qt/scripts/algo_trading/poly_alpha_agents.py`
  - Evidence-pack-bounded agent finding validation and mock adapter interface.
- Create: `fincept-qt/scripts/algo_trading/poly_alpha_validation.py`
  - Signal-level validation, event-time check, exit template calculations, missing snapshot behavior.
- Create: `fincept-qt/scripts/algo_trading/poly_alpha_promotion.py`
  - Prediction/trading quality gate, promotion decisions, and paper proposal bridge.

### Python Tests

- Create: `fincept-qt/scripts/algo_trading/tests/test_poly_alpha_config_models.py`
- Create: `fincept-qt/scripts/algo_trading/tests/test_poly_alpha_store.py`
- Create: `fincept-qt/scripts/algo_trading/tests/test_poly_alpha_scanner.py`
- Create: `fincept-qt/scripts/algo_trading/tests/test_poly_alpha_agents.py`
- Create: `fincept-qt/scripts/algo_trading/tests/test_poly_alpha_validation.py`
- Create: `fincept-qt/scripts/algo_trading/tests/test_poly_alpha_promotion.py`

### API

- Modify: `fincept-qt/scripts/polymarket_web_api/repository.py`
  - Add Poly Alpha repository methods or delegate to a new internal helper class.
- Modify: `fincept-qt/scripts/polymarket_web_api/schemas.py`
  - Add response/request schemas for Poly Alpha routes.
- Modify: `fincept-qt/scripts/polymarket_web_api/app.py`
  - Add `/api/poly-alpha/*` routes.
- Test: `fincept-qt/scripts/polymarket_web_api/tests/test_api_routes.py`

### Frontend

- Modify: `web/polymarket-terminal/src/api/types.ts`
  - Add Poly Alpha types.
- Modify: `web/polymarket-terminal/src/api/client.ts`
  - Add Poly Alpha fetchers/mappers.
- Modify: `web/polymarket-terminal/src/data/mockTerminalData.ts`
  - Add mock Poly Alpha lifecycle data.
- Modify: `web/polymarket-terminal/src/pages/AgentsPage.tsx`
  - Make F7 the Poly Alpha Cockpit.
- Modify: `web/polymarket-terminal/src/pages/SignalsPage.tsx`
  - Add opportunity/shadow/promotion filters and metrics.
- Modify: `web/polymarket-terminal/src/pages/NewsPage.tsx`
  - Add evidence pack and scan run sections.
- Modify: `web/polymarket-terminal/src/pages/RiskPage.tsx`
  - Show `source: poly_alpha`, evidence links, and promoted-only behavior.
- Modify: `web/polymarket-terminal/src/pages/AuditPage.tsx`
  - Show Poly Alpha lineage and `paper_fill_skipped`.

### Frontend Tests

- Modify or create:
  - `web/polymarket-terminal/src/api/client.test.ts`
  - `web/polymarket-terminal/src/pages/AgentsPage.test.tsx`
  - `web/polymarket-terminal/src/pages/SignalsPage.test.tsx`
  - `web/polymarket-terminal/src/pages/NewsPage.test.tsx`
  - `web/polymarket-terminal/src/pages/RiskPage.test.tsx`
  - `web/polymarket-terminal/src/pages/AuditPage.test.tsx`
  - `web/polymarket-terminal/tests/polymarket-terminal.spec.ts`

---

### Task 1: Poly Alpha Config, Enums, and Lifecycle

**Files:**
- Create: `fincept-qt/scripts/algo_trading/poly_alpha_config.py`
- Create: `fincept-qt/scripts/algo_trading/poly_alpha_models.py`
- Test: `fincept-qt/scripts/algo_trading/tests/test_poly_alpha_config_models.py`

- [ ] **Step 1: Write failing tests for default config**

Add tests asserting:

```python
from poly_alpha_config import default_poly_alpha_config

def test_default_config_has_phase_1_gate_values():
    cfg = default_poly_alpha_config()
    assert cfg["validation_freshness_window_sec"] == 300
    assert cfg["min_exploration_samples"] == 10
    assert cfg["min_promotion_samples"] == 30
    assert cfg["min_promotion_history_days"] == 90
    assert cfg["max_drawdown_threshold"] == -0.20
    assert cfg["min_hit_rate"] == 0.52
    assert cfg["min_payoff_ratio"] == 1.10
    assert cfg["min_capacity_multiple"] == 2.0
```

- [ ] **Step 2: Write failing tests for lifecycle transitions**

Add tests asserting exact transition behavior from the spec:

```python
from poly_alpha_models import apply_opportunity_transition

def test_promotion_watch_keeps_validated_status():
    state = apply_opportunity_transition("promotion_watch")
    assert state.opportunity_status == "validated"
    assert state.shadow_signal_status == "validated"
    assert state.promotion_decision == "watch"

def test_post_approval_skip_is_first_class():
    state = apply_opportunity_transition("paper_fill_skipped")
    assert state.opportunity_status == "skipped"
    assert state.shadow_signal_status == "promoted"
    assert state.promotion_decision == "promote"
```

Also add a table-driven test for every required transition:

```python
@pytest.mark.parametrize(
    ("event", "opportunity_status", "shadow_signal_status", "promotion_decision"),
    [
        ("scanner_ignore", None, None, None),
        ("opportunity_discovered", "watch", None, None),
        ("exploration_pass", "watch", None, None),
        ("exploration_watch", "watch", None, None),
        ("exploration_reject", "rejected", None, None),
        ("shadow_signal_created", "shadow", "shadow", None),
        ("validation_pass", "validated", "validated", None),
        ("validation_fail", "rejected", "rejected", None),
        ("promotion_watch", "validated", "validated", "watch"),
        ("promotion_reject", "rejected", "rejected", "reject"),
        ("promotion_promote", "promoted", "promoted", "promote"),
        ("proposal_created", "proposed", "promoted", "promote"),
        ("proposal_rejected", "rejected", "promoted", "promote"),
        ("proposal_approved", "approved", "promoted", "promote"),
        ("paper_fill_skipped", "skipped", "promoted", "promote"),
        ("paper_fill_recorded", "filled", "promoted", "promote"),
        ("signal_ttl_expired", "expired", "expired", None),
        ("proposal_ttl_expired", "expired", "promoted", "promote"),
    ],
)
def test_lifecycle_transition_table(event, opportunity_status, shadow_signal_status, promotion_decision):
    state = apply_opportunity_transition(event)
    assert state.opportunity_status == opportunity_status
    assert state.shadow_signal_status == shadow_signal_status
    assert state.promotion_decision == promotion_decision
```

Add explicit previous-state tests for TTL behavior:

```python
def test_proposal_ttl_expired_does_not_expire_promoted_signal_state():
    state = apply_opportunity_transition(
        "proposal_ttl_expired",
        previous_shadow_signal_status="promoted",
        previous_promotion_decision="promote",
    )
    assert state.opportunity_status == "expired"
    assert state.shadow_signal_status == "promoted"
    assert state.promotion_decision == "promote"

def test_signal_ttl_expired_preserves_existing_promotion_decision():
    state = apply_opportunity_transition(
        "signal_ttl_expired",
        previous_shadow_signal_status="promoted",
        previous_promotion_decision="promote",
    )
    assert state.opportunity_status == "expired"
    assert state.shadow_signal_status == "expired"
    assert state.promotion_decision == "promote"

def test_watch_opportunity_ttl_expired_preserves_missing_signal_state():
    state = apply_opportunity_transition(
        "opportunity_ttl_expired",
        previous_shadow_signal_status=None,
        previous_promotion_decision=None,
    )
    assert state.opportunity_status == "expired"
    assert state.shadow_signal_status is None
    assert state.promotion_decision is None
```

- [ ] **Step 3: Run the failing model tests**

Run:

```powershell
python -m pytest fincept-qt/scripts/algo_trading/tests/test_poly_alpha_config_models.py -q --basetemp .pytest_tmp
```

Expected: fail with missing modules/functions.

- [ ] **Step 4: Implement config and lifecycle helpers**

Implement:

- `DEFAULT_POLY_ALPHA_CONFIG`
- `default_poly_alpha_config(overrides: dict | None = None) -> dict`
- status/reason constants
- `LifecycleState` dataclass
- `apply_opportunity_transition(event: str, previous_shadow_signal_status: str | None = None, previous_promotion_decision: str | None = None) -> LifecycleState`

Keep this file deterministic and dependency-free.

- [ ] **Step 5: Run tests to pass**

Run:

```powershell
python -m pytest fincept-qt/scripts/algo_trading/tests/test_poly_alpha_config_models.py -q --basetemp .pytest_tmp
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add fincept-qt/scripts/algo_trading/poly_alpha_config.py fincept-qt/scripts/algo_trading/poly_alpha_models.py fincept-qt/scripts/algo_trading/tests/test_poly_alpha_config_models.py
git commit -m "feat: add poly alpha lifecycle config"
```

---

### Task 2: Poly Alpha SQLite Store

**Files:**
- Create: `fincept-qt/scripts/algo_trading/poly_alpha_store.py`
- Test: `fincept-qt/scripts/algo_trading/tests/test_poly_alpha_store.py`

- [ ] **Step 1: Write failing schema tests**

Test that `ensure_poly_alpha_schema(conn)` creates all Phase 1 tables:

```python
def test_ensure_poly_alpha_schema_creates_phase_1_tables(tmp_path):
    conn = sqlite3.connect(tmp_path / "poly.db")
    ensure_poly_alpha_schema(conn)
    names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "poly_alpha_config_versions" in names
    assert "poly_alpha_source_sets" in names
    assert "poly_alpha_strategy_versions" in names
    assert "poly_alpha_documents" in names
    assert "poly_alpha_events" in names
    assert "poly_alpha_event_market_links" in names
    assert "poly_alpha_research_runs" in names
    assert "poly_alpha_scan_runs" in names
    assert "poly_alpha_scan_results" in names
    assert "poly_alpha_opportunities" in names
    assert "poly_alpha_evidence_packs" in names
    assert "poly_alpha_exploration_decisions" in names
    assert "poly_alpha_market_snapshots" in names
    assert "poly_alpha_agent_findings" in names
    assert "poly_alpha_shadow_signals" in names
    assert "poly_alpha_validation_results" in names
    assert "poly_alpha_promotion_decisions" in names
```

- [ ] **Step 2: Write failing CRUD tests for scan runs and no-trade attribution**

Assert:

- `record_scan_run()` returns a scan run ID.
- `record_scan_result(decision="ignore", reason="wide_spread")` persists the no-trade reason.
- `list_scan_runs()` includes summary counts.
- creating an opportunity writes or can expose `opportunity_discovered`.
- recording a document writes or can expose `document_ingested`.
- recording an evidence pack writes or can expose `evidence_pack_created`.

- [ ] **Step 3: Write failing CRUD tests for evidence and lifecycle**

Assert:

- documents deduplicate by payload hash.
- events persist event type, assets, and status.
- event-market links use generic venue identifiers and adapter metadata.
- research runs carry opportunity, evidence pack, strategy, model config, and status.
- evidence packs cite documents and snapshots.
- exploration decisions update status expectations.
- exploration decisions map to `exploration_passed`, `exploration_watch`, or `exploration_rejected`.
- lifecycle event names map to audit action names through a documented helper, for example `exploration_pass` -> `exploration_passed`, `validation_pass` -> `validation_completed`, `promotion_promote` -> `promotion_approved`, `promotion_reject` -> `promotion_rejected`, `promotion_watch` -> `promotion_watch`, and TTL events -> `expired`.
- shadow signals use allowed status values.
- shadow signal creation maps to `shadow_signal_created`.
- `paper_fill_skipped` can update opportunity status and write audit-compatible output.
- all record helpers that represent lifecycle actions can optionally write matching Poly Alpha audit actions.

- [ ] **Step 4: Run failing store tests**

```powershell
python -m pytest fincept-qt/scripts/algo_trading/tests/test_poly_alpha_store.py -q --basetemp .pytest_tmp
```

Expected: fail with missing module/functions.

- [ ] **Step 5: Implement schema and minimal CRUD**

Implement focused helpers:

- `ensure_poly_alpha_schema(conn)`
- `record_config_version(conn, ...)`
- `record_source_set(conn, ...)`
- `record_strategy_version(conn, ...)`
- `record_document(conn, ...)`
- `record_event(conn, ...)`
- `record_event_market_link(conn, ...)`
- `record_research_run(conn, ...)`
- `record_scan_run(conn, ...)`
- `record_scan_result(conn, ...)`
- `record_opportunity(conn, ...)`
- `update_opportunity_status(conn, ...)`
- `record_market_snapshot(conn, ...)`
- `record_evidence_pack(conn, ...)`
- `record_exploration_decision(conn, ...)`
- `record_agent_finding(conn, ...)`
- `record_shadow_signal(conn, ...)`
- `record_validation_result(conn, ...)`
- `record_promotion_decision(conn, ...)`
- `audit_action_for_lifecycle_event(event: str) -> str`
- list helpers used by API.

Use JSON strings for `*_json` fields, matching existing `polymarket_store.py` style.

- [ ] **Step 6: Run store tests to pass**

```powershell
python -m pytest fincept-qt/scripts/algo_trading/tests/test_poly_alpha_store.py -q --basetemp .pytest_tmp
```

Expected: pass.

- [ ] **Step 7: Commit**

```powershell
git add fincept-qt/scripts/algo_trading/poly_alpha_store.py fincept-qt/scripts/algo_trading/tests/test_poly_alpha_store.py
git commit -m "feat: add poly alpha persistence"
```

---

### Task 3: Deterministic Scan, Evidence Pack, and Exploration Gate

**Files:**
- Create: `fincept-qt/scripts/algo_trading/poly_alpha_scanner.py`
- Test: `fincept-qt/scripts/algo_trading/tests/test_poly_alpha_scanner.py`

- [ ] **Step 1: Write failing tests for scan run grouping**

Test that scheduled scan creates:

- one scan run
- scan results attached to the scan run
- market snapshots
- opportunity for qualifying candidate
- ignored scan result for wide spread or low liquidity.

- [ ] **Step 2: Write failing tests for evidence pack creation**

Assert:

- evidence pack includes document IDs and snapshot IDs.
- evidence pack has `latest_published_at`, `latest_fetched_at`, `latest_observed_at`.
- agents have enough references to cite the pack later.

- [ ] **Step 3: Write failing tests for Exploration Gate**

Assert:

- `pass` only when `historical_sample_count >= config["min_exploration_samples"]` and the Phase 1 default minimum is `10`.
- `pass` only when evidence pack has source metadata, fetched timestamps, payload hashes, and at least one current snapshot.
- `pass` only when event-market link confidence is recorded.
- `pass` only when current market probability, spread, depth, and liquidity metrics are recorded.
- `pass` only when deterministic evidence completeness metrics are recorded.
- `watch` keeps opportunity status `watch`.
- `reject` sets opportunity status `rejected`.
- no agent findings are required for Exploration Gate.

- [ ] **Step 4: Run failing scanner tests**

```powershell
python -m pytest fincept-qt/scripts/algo_trading/tests/test_poly_alpha_scanner.py -q --basetemp .pytest_tmp
```

Expected: fail.

- [ ] **Step 5: Implement deterministic helpers**

Implement:

- `run_deterministic_scan(conn, strategy_version_id, config, source_documents, market_snapshots, now)`
- `build_evidence_pack(conn, opportunity_id, document_ids, snapshot_ids, event_ids, now)`
- `decide_exploration(conn, opportunity_id, evidence_pack_id, config, now)`

`decide_exploration(...)` must evaluate the same deterministic fields the tests assert: sample count, source metadata, current snapshot presence, event-market link confidence, market probability/spread/depth/liquidity metrics, and evidence completeness metrics. It must not require agent findings, profitability, or external LLM output.

No network calls in this module. Tests should pass fixtures/data dictionaries.

- [ ] **Step 6: Run scanner tests to pass**

```powershell
python -m pytest fincept-qt/scripts/algo_trading/tests/test_poly_alpha_scanner.py -q --basetemp .pytest_tmp
```

Expected: pass.

- [ ] **Step 7: Commit**

```powershell
git add fincept-qt/scripts/algo_trading/poly_alpha_scanner.py fincept-qt/scripts/algo_trading/tests/test_poly_alpha_scanner.py
git commit -m "feat: add poly alpha opportunity scanner"
```

---

### Task 4: Evidence-Bounded Agent Findings

**Files:**
- Create: `fincept-qt/scripts/algo_trading/poly_alpha_agents.py`
- Test: `fincept-qt/scripts/algo_trading/tests/test_poly_alpha_agents.py`

- [ ] **Step 1: Write failing tests for finding validation**

Assert:

- Researcher/Critic/Risk findings require `evidence_pack_id`.
- finding evidence IDs must be a subset of the evidence pack document IDs.
- uncaptured facts fail validation.
- Phase 1 mock adapter can produce deterministic findings for tests.

- [ ] **Step 2: Run failing agent tests**

```powershell
python -m pytest fincept-qt/scripts/algo_trading/tests/test_poly_alpha_agents.py -q --basetemp .pytest_tmp
```

Expected: fail.

- [ ] **Step 3: Implement agent finding validation and mock adapter**

Implement:

- `validate_agent_finding(finding, evidence_pack) -> None`
- `build_mock_agent_findings(evidence_pack, market_probability, estimated_probability) -> list[dict]`

Do not call external LLMs in Phase 1 implementation. Keep model/provider integration as a later extension.

- [ ] **Step 4: Run agent tests to pass**

```powershell
python -m pytest fincept-qt/scripts/algo_trading/tests/test_poly_alpha_agents.py -q --basetemp .pytest_tmp
```

Expected: pass.

- [ ] **Step 5: Commit**

```powershell
git add fincept-qt/scripts/algo_trading/poly_alpha_agents.py fincept-qt/scripts/algo_trading/tests/test_poly_alpha_agents.py
git commit -m "feat: validate poly alpha agent findings"
```

---

### Task 5: Shadow Signal Validation Engine

**Files:**
- Create: `fincept-qt/scripts/algo_trading/poly_alpha_validation.py`
- Test: `fincept-qt/scripts/algo_trading/tests/test_poly_alpha_validation.py`

- [ ] **Step 1: Write failing test for missing market snapshot**

Assert validation fails with `missing_market_snapshot` when no snapshot exists at or before `shadow_signal.created_at` within 300 seconds.

- [ ] **Step 2: Write failing event-time check tests**

Assert validation computes:

- `information_lag_sec`
- `fetch_lag_sec`
- `market_move_before_signal`
- `market_move_after_signal`
- `late_information` reason when most of the cited information move happened before `shadow_signal.created_at`.

- [ ] **Step 3: Write failing exit template tests**

Assert separate rows/results for:

- `fixed_horizon`
- `target_stop`
- `resolution_expiry`

Include CLV, Brier/calibration where resolved, and edge decay where unresolved.

- [ ] **Step 4: Run failing validation tests**

```powershell
python -m pytest fincept-qt/scripts/algo_trading/tests/test_poly_alpha_validation.py -q --basetemp .pytest_tmp
```

Expected: fail.

- [ ] **Step 5: Implement validation engine**

Implement:

- `select_entry_snapshot(snapshots, signal_created_at, freshness_sec)`
- `run_signal_validation(conn, shadow_signal_id, config, now)`
- `calculate_event_time_metrics(...)`
- `calculate_template_result(...)`

Prefer simple deterministic calculations. Do not introduce a strategy optimizer.

- [ ] **Step 6: Run validation tests to pass**

```powershell
python -m pytest fincept-qt/scripts/algo_trading/tests/test_poly_alpha_validation.py -q --basetemp .pytest_tmp
```

Expected: pass.

- [ ] **Step 7: Commit**

```powershell
git add fincept-qt/scripts/algo_trading/poly_alpha_validation.py fincept-qt/scripts/algo_trading/tests/test_poly_alpha_validation.py
git commit -m "feat: add poly alpha signal validation"
```

---

### Task 6: Promotion Gate and Paper Proposal Bridge

**Files:**
- Create: `fincept-qt/scripts/algo_trading/poly_alpha_promotion.py`
- Modify: `fincept-qt/scripts/algo_trading/poly_alpha_store.py`
- Test: `fincept-qt/scripts/algo_trading/tests/test_poly_alpha_promotion.py`

- [ ] **Step 1: Write failing tests for prediction and trading gates**

Assert promotion requires:

- cost-adjusted net return > 0
- positive median CLV after costs
- max drawdown above threshold
- capacity >= 2x paper order size
- no unresolved Critic blocker
- Risk Reviewer approval.
- event-time validation does not have a blocking `late_information` reason.

- [ ] **Step 2: Write failing tests for watch/reject/promote lifecycle**

Assert:

- `watch` leaves opportunity/shadow as validated.
- `reject` sets opportunity/shadow rejected.
- `promote` sets opportunity/shadow promoted.

- [ ] **Step 3: Write failing paper proposal bridge tests**

Assert:

- proposal creation only happens after promotion.
- proposal has `source: poly_alpha` in features/metadata.
- proposal creation writes or exposes `proposal_created`.
- manual approval/rejection continues to write `proposal_approved` / `proposal_rejected`.
- paper fill records `paper_fill_recorded`.
- post-approval skip updates opportunity to `skipped` and writes `paper_fill_skipped`.
- no live trading fields are accepted.

- [ ] **Step 4: Run failing promotion tests**

```powershell
python -m pytest fincept-qt/scripts/algo_trading/tests/test_poly_alpha_promotion.py -q --basetemp .pytest_tmp
```

Expected: fail.

- [ ] **Step 5: Implement promotion and bridge helpers**

Implement:

- `evaluate_promotion(conn, shadow_signal_id, config, now)`
- `create_paper_proposal_from_promotion(conn, promotion_id, deployment_id, now)`
- `record_post_approval_skip(conn, opportunity_id, proposal_id, reason, now)`

Reuse existing `record_trade_proposal()` and `record_audit_event()` where practical.

Ensure Poly Alpha audit lineage can be listed by F8 through either `algo_polymarket_audit_events` or a unified API/view.

- [ ] **Step 6: Run promotion tests to pass**

```powershell
python -m pytest fincept-qt/scripts/algo_trading/tests/test_poly_alpha_promotion.py -q --basetemp .pytest_tmp
```

Expected: pass.

- [ ] **Step 7: Commit**

```powershell
git add fincept-qt/scripts/algo_trading/poly_alpha_promotion.py fincept-qt/scripts/algo_trading/poly_alpha_store.py fincept-qt/scripts/algo_trading/tests/test_poly_alpha_promotion.py
git commit -m "feat: add poly alpha promotion gate"
```

---

### Task 7: FastAPI Poly Alpha Endpoints

**Files:**
- Modify: `fincept-qt/scripts/polymarket_web_api/repository.py`
- Modify: `fincept-qt/scripts/polymarket_web_api/schemas.py`
- Modify: `fincept-qt/scripts/polymarket_web_api/app.py`
- Test: `fincept-qt/scripts/polymarket_web_api/tests/test_api_routes.py`

- [ ] **Step 1: Write failing API route tests**

Add tests for:

- `GET /api/poly-alpha/config-versions`
- `GET /api/poly-alpha/source-sets`
- `GET /api/poly-alpha/strategy-versions`
- `GET /api/poly-alpha/documents`
- `GET /api/poly-alpha/events`
- `GET /api/poly-alpha/links`
- `GET /api/poly-alpha/research-runs`
- `GET /api/poly-alpha/findings`
- `GET /api/poly-alpha/scan-runs`
- `GET /api/poly-alpha/scan-results`
- `GET /api/poly-alpha/opportunities`
- `GET /api/poly-alpha/evidence-packs`
- `GET /api/poly-alpha/exploration-decisions`
- `GET /api/poly-alpha/market-snapshots`
- `GET /api/poly-alpha/shadow-signals`
- `GET /api/poly-alpha/validations`
- `GET /api/poly-alpha/promotions`

- [ ] **Step 2: Write failing control route tests**

Add tests for:

- manual research task trigger, for example `POST /api/poly-alpha/research-runs/manual`
- deterministic scan trigger
- evidence pack build
- exploration decision
- signal validation
- promotion decision
- paper proposal creation from promoted signal.

Assert no request schema accepts private key, API secret, live order mode, or real CLOB order fields.

Assert Poly Alpha audit events can be read through F8's audit path or a unified Poly Alpha audit response, including `document_ingested`, `evidence_pack_created`, `research_started`, `research_completed`, `validation_completed`, `promotion_approved`, `promotion_rejected`, `promotion_watch`, and `paper_fill_skipped`.

- [ ] **Step 3: Run failing API tests**

```powershell
python -m pytest fincept-qt/scripts/polymarket_web_api/tests/test_api_routes.py -q --basetemp .pytest_tmp
```

Expected: fail on missing routes/schemas.

- [ ] **Step 4: Implement repository methods and schemas**

Add Pydantic schemas with minimal fields needed by frontend and tests. Keep `extra="forbid"` on control request schemas that could otherwise accept live trading fields.

- [ ] **Step 5: Add routes in `app.py`**

Follow existing route style. Use the existing repository instance.

- [ ] **Step 6: Run API tests to pass**

```powershell
python -m pytest fincept-qt/scripts/polymarket_web_api/tests/test_api_routes.py -q --basetemp .pytest_tmp
```

Expected: pass.

- [ ] **Step 7: Run combined Python tests**

```powershell
python -m pytest fincept-qt/scripts/algo_trading/tests fincept-qt/scripts/polymarket_web_api/tests -q --basetemp .pytest_tmp
```

Expected: pass.

- [ ] **Step 8: Commit**

```powershell
git add fincept-qt/scripts/polymarket_web_api/repository.py fincept-qt/scripts/polymarket_web_api/schemas.py fincept-qt/scripts/polymarket_web_api/app.py fincept-qt/scripts/polymarket_web_api/tests/test_api_routes.py
git commit -m "feat: expose poly alpha API"
```

---

### Task 8: Frontend API Client and Types

**Files:**
- Modify: `web/polymarket-terminal/src/api/types.ts`
- Modify: `web/polymarket-terminal/src/api/client.ts`
- Modify: `web/polymarket-terminal/src/api/client.test.ts`
- Modify: `web/polymarket-terminal/src/data/mockTerminalData.ts`

- [ ] **Step 1: Write failing client tests**

Assert:

- `fetchPolyAlphaOpportunities()` calls `/api/poly-alpha/opportunities`.
- `fetchPolyAlphaScanRuns()` calls `/api/poly-alpha/scan-runs`.
- `fetchPolyAlphaMarketSnapshots()` calls `/api/poly-alpha/market-snapshots`.
- `fetchPolyAlphaDocuments()` calls `/api/poly-alpha/documents`.
- `fetchPolyAlphaEvents()` calls `/api/poly-alpha/events`.
- `fetchPolyAlphaLinks()` calls `/api/poly-alpha/links`.
- `fetchPolyAlphaResearchRuns()` calls `/api/poly-alpha/research-runs`.
- `fetchPolyAlphaFindings()` calls `/api/poly-alpha/findings`.
- `fetchPolyAlphaCockpit()` or equivalent aggregator combines opportunities, scan runs, shadow signals, validations, and promotions.
- F3 filters keep shadow signal status and promotion decision separate.

- [ ] **Step 2: Run failing frontend client tests**

```powershell
npm test --prefix web/polymarket-terminal -- src/api/client.test.ts
```

Expected: fail.

- [ ] **Step 3: Add types and API mappers**

Add:

- `PolyAlphaOpportunity`
- `PolyAlphaScanRun`
- `PolyAlphaScanResult`
- `PolyAlphaDocument`
- `PolyAlphaEvent`
- `PolyAlphaEventMarketLink`
- `PolyAlphaResearchRun`
- `PolyAlphaAgentFinding`
- `PolyAlphaEvidencePack`
- `PolyAlphaMarketSnapshot`
- `PolyAlphaShadowSignal`
- `PolyAlphaValidationResult`
- `PolyAlphaPromotionDecision`

Map missing values conservatively and mark mock rows with `source: "mock"` if following existing frontend pattern.

- [ ] **Step 4: Add mock data**

Add realistic mock rows for Cockpit, Signals, News, Risk, and Audit tests.

- [ ] **Step 5: Run frontend client tests to pass**

```powershell
npm test --prefix web/polymarket-terminal -- src/api/client.test.ts
```

Expected: pass.

- [ ] **Step 6: Commit**

```powershell
git add web/polymarket-terminal/src/api/types.ts web/polymarket-terminal/src/api/client.ts web/polymarket-terminal/src/api/client.test.ts web/polymarket-terminal/src/data/mockTerminalData.ts
git commit -m "feat: add poly alpha frontend client"
```

---

### Task 9: F7 Cockpit and Page Integrations

**Files:**
- Modify: `web/polymarket-terminal/src/pages/MarketsPage.tsx`
- Modify: `web/polymarket-terminal/src/pages/MarketsPage.test.tsx`
- Modify: `web/polymarket-terminal/src/pages/AgentsPage.tsx`
- Modify: `web/polymarket-terminal/src/pages/AgentsPage.test.tsx`
- Modify: `web/polymarket-terminal/src/pages/SignalsPage.tsx`
- Modify: `web/polymarket-terminal/src/pages/SignalsPage.test.tsx`
- Modify: `web/polymarket-terminal/src/pages/NewsPage.tsx`
- Modify: `web/polymarket-terminal/src/pages/NewsPage.test.tsx`
- Modify: `web/polymarket-terminal/src/pages/RiskPage.tsx`
- Modify: `web/polymarket-terminal/src/pages/RiskPage.test.tsx`
- Modify: `web/polymarket-terminal/src/pages/AuditPage.tsx`
- Modify: `web/polymarket-terminal/src/pages/AuditPage.test.tsx`

- [ ] **Step 1: Write failing Cockpit tests**

Assert F7 displays:

- Today's opportunities
- Needs research
- Shadow performance
- Ready for promotion
- Risk queue candidates
- Failed and why
- scheduled scan runs.

- [ ] **Step 2: Write failing F2 Markets tests**

Assert F2 displays:

- linked event count
- latest evidence timestamp
- market probability versus estimated probability
- liquidity, spread, and order book freshness
- link confidence
- action affordance to send market to research/Cockpit.

- [ ] **Step 3: Write failing F3 tests**

Assert:

- F3 displays strategy version, opportunity status, CLV, Brier/calibration where available.
- status filters and promotion decision filters are separate.
- `watch` is only a promotion decision filter.

- [ ] **Step 4: Write failing F5/F8/Risk tests**

Assert:

- F5 shows evidence packs and scan runs.
- F8 shows evidence chain including exploration decision and `paper_fill_skipped`.
- F4 Risk only shows promoted proposals.
- Risk page does not show raw shadow signals.

- [ ] **Step 5: Run failing page tests**

```powershell
npm test --prefix web/polymarket-terminal -- src/pages/MarketsPage.test.tsx src/pages/AgentsPage.test.tsx src/pages/SignalsPage.test.tsx src/pages/NewsPage.test.tsx src/pages/RiskPage.test.tsx src/pages/AuditPage.test.tsx
```

Expected: fail.

- [ ] **Step 6: Implement UI changes**

Use existing terminal components:

- `DenseDataTable`
- `StatusPill`
- `TerminalButton`
- `EmptyStatePanel`

Keep layout dense and work-focused. Do not create a marketing or landing page. Keep F1-F8 route behavior unchanged.

- [ ] **Step 7: Run page tests to pass**

```powershell
npm test --prefix web/polymarket-terminal -- src/pages/MarketsPage.test.tsx src/pages/AgentsPage.test.tsx src/pages/SignalsPage.test.tsx src/pages/NewsPage.test.tsx src/pages/RiskPage.test.tsx src/pages/AuditPage.test.tsx
```

Expected: pass.

- [ ] **Step 8: Commit**

```powershell
git add web/polymarket-terminal/src/pages/MarketsPage.tsx web/polymarket-terminal/src/pages/MarketsPage.test.tsx web/polymarket-terminal/src/pages/AgentsPage.tsx web/polymarket-terminal/src/pages/AgentsPage.test.tsx web/polymarket-terminal/src/pages/SignalsPage.tsx web/polymarket-terminal/src/pages/SignalsPage.test.tsx web/polymarket-terminal/src/pages/NewsPage.tsx web/polymarket-terminal/src/pages/NewsPage.test.tsx web/polymarket-terminal/src/pages/RiskPage.tsx web/polymarket-terminal/src/pages/RiskPage.test.tsx web/polymarket-terminal/src/pages/AuditPage.tsx web/polymarket-terminal/src/pages/AuditPage.test.tsx
git commit -m "feat: add poly alpha cockpit UI"
```

---

### Task 10: E2E, Runbook, and Final Verification

**Files:**
- Modify: `web/polymarket-terminal/tests/polymarket-terminal.spec.ts`
- Modify: `web/polymarket-terminal/README.md`
- Optional modify: `docs/superpowers/specs/2026-05-07-poly-alpha-platform-phase-1-design.md` only if implementation reveals a spec correction.

- [ ] **Step 1: Write failing E2E happy path**

Add flow:

```text
manual research task
  -> opportunity
  -> evidence pack
  -> exploration pass
  -> mocked agent findings
  -> shadow signal
  -> event-time check
  -> validation
  -> promotion
  -> Risk queue proposal
  -> manual approve
  -> paper fill
  -> F8 evidence chain
```

- [ ] **Step 2: Write failing E2E negative path**

Add flow:

```text
opportunity with unresolved Critic blocker
  -> validation/review
  -> promotion rejected
  -> no Risk queue proposal
  -> audit records rejection
```

- [ ] **Step 3: Check ports before running E2E**

```powershell
Get-NetTCPConnection -LocalPort 4177,8765 -ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort,State,OwningProcess
```

Expected: no listeners. If any listener exists, stop and resolve before running E2E.

- [ ] **Step 4: Run failing E2E**

```powershell
npm run test:e2e --prefix web/polymarket-terminal
```

Expected: fail until routes/UI/mocks are complete.

- [ ] **Step 5: Implement E2E support**

Update test fixtures/mocks only as needed. Do not add live trading behavior.

- [ ] **Step 6: Run full verification**

```powershell
python -m pytest fincept-qt/scripts/algo_trading/tests fincept-qt/scripts/polymarket_web_api/tests -q --basetemp .pytest_tmp
npm test --prefix web/polymarket-terminal
npm run lint --prefix web/polymarket-terminal
npm run build --prefix web/polymarket-terminal
Get-NetTCPConnection -LocalPort 4177,8765 -ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort,State,OwningProcess
npm run test:e2e --prefix web/polymarket-terminal
Get-NetTCPConnection -LocalPort 4177,8765 -ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort,State,OwningProcess
```

Expected:

- Python tests pass.
- Frontend tests pass.
- TypeScript lint passes.
- Build passes.
- E2E passes.
- Ports `4177/8765` are not left occupied after E2E.

- [ ] **Step 7: Update runbook**

Update `web/polymarket-terminal/README.md` with Poly Alpha endpoints, paper-only reminder, and the same port-check workflow.

- [ ] **Step 8: Commit**

```powershell
git add web/polymarket-terminal/tests/polymarket-terminal.spec.ts web/polymarket-terminal/README.md
git commit -m "test: add poly alpha terminal verification"
```

---

## Final Review Checkpoint

Before claiming completion:

- Use `superpowers:verification-before-completion`.
- Run the full verification commands in Task 10.
- Confirm `git status --short`.
- Request code review using `superpowers:requesting-code-review`.
- Fix review blockers before finishing.

## Finishing

When implementation and review are complete:

- Use `superpowers:finishing-a-development-branch`.
- Present the standard options.
- If user chooses PR, push the branch and create/update PR.
