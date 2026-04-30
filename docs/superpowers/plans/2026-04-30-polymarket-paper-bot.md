# Polymarket Paper Bot Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a paper-only Polymarket automatic trading bot inside the existing native Qt Algo Trading workflow, with official-source market data, conservative paper fills, risk controls, and automated verification.

**Architecture:** Keep the feature as a `market_type = "polymarket"` extension to the existing Algo Trading service and Python runner. Python owns scanning, edge calculation, risk, paper fills, and runner state; C++ owns strategy/deployment orchestration and native Qt display. The bot must not call authenticated Polymarket live order paths.

**Tech Stack:** C++20, Qt6 Widgets/Test, Python 3.11+, SQLite, `requests`, optional `websocket-client` for a later candidate stream slice, pytest-style Python tests.

---

## Required Skills

- Use @superpowers:test-driven-development for implementation tasks.
- Use @superpowers:systematic-debugging for any failing test or unexpected runtime behavior.
- Use @superpowers:verification-before-completion before claiming completion.
- Use @superpowers:subagent-driven-development if the harness allows subagents; otherwise use @superpowers:executing-plans.

## Scope Boundaries

- Paper mode only.
- No private-key handling.
- No CLOB API credential derivation.
- No calls to `fincept-qt/scripts/prediction_polymarket.py place_order`.
- No web UI.
- No Kalshi support in this implementation slice.
- No profitability claims.

## Shared Bot Config Contract

All Python and Qt code must use the same `bot_config` keys. Missing keys must be filled from defaults in Python, and Qt should write explicit values when a user saves a Polymarket strategy.

Required default keys:

```json
{
  "strategy_mode": "auto_scan",
  "scan_interval_sec": 60,
  "max_candidates": 20,
  "sort_by": "volume",
  "min_volume": 1000.0,
  "min_liquidity": 500.0,
  "max_spread": 0.05,
  "min_depth": 10.0,
  "min_price": 0.05,
  "max_price": 0.95,
  "excluded_categories": [],
  "excluded_tags": [],
  "min_time_to_expiry_hours": 24,
  "freshness_ttl_sec": 30,
  "min_edge": 0.04,
  "confidence_threshold": 0.55,
  "momentum_weight": 0.20,
  "volatility_penalty": 0.15,
  "imbalance_weight": 0.20,
  "liquidity_weight": 0.10,
  "spread_penalty": 0.20,
  "paper_order_size": 10.0,
  "max_order_usdc": 25.0,
  "max_total_exposure": 100.0,
  "daily_loss_limit": 25.0,
  "max_positions": 5,
  "cooldown_minutes": 10,
  "stop_loss_pct": 30.0,
  "take_profit_pct": 50.0,
  "trailing_stop_pct": 0.0
}
```

Implementation rule:

- Python must centralize defaults in `polymarket_config.py`.
- Qt must serialize the same keys into `AlgoStrategy::bot_config`.
- Runner tests must assert defaulting, stale-data TTL, risk limits, and edge weights use this contract.

## File Structure

Create:

- `fincept-qt/scripts/algo_trading/polymarket_config.py`
  Shared default `bot_config` contract and validation/defaulting helpers.
- `fincept-qt/scripts/algo_trading/polymarket_models.py`
  Small dataclasses and JSON helpers for markets, order books, candidates, signals, risk config, paper fills, and paper positions.
- `fincept-qt/scripts/algo_trading/polymarket_sources.py`
  Official Polymarket REST source client and fixture-loading seam. Implements Gamma market fetch and CLOB order-book fetch. All returned market data carries `source_api`, `fetched_at`, and payload hash where practical.
- `fincept-qt/scripts/algo_trading/polymarket_scanner.py`
  Candidate filtering and skipped-reason logic.
- `fincept-qt/scripts/algo_trading/polymarket_edge.py`
  Heuristic probability, confidence, edge, and explainable feature contributions.
- `fincept-qt/scripts/algo_trading/polymarket_risk.py`
  Conservative risk checks for max order value, exposure, loss, max positions, cooldown, spread, depth, and price range.
- `fincept-qt/scripts/algo_trading/polymarket_paper.py`
  Top-of-book paper fills, position updates, realized/unrealized PnL.
- `fincept-qt/scripts/algo_trading/polymarket_store.py`
  SQLite schema and persistence for candidates, signals, skipped reasons, paper trades, paper positions, and metrics summaries.
- `fincept-qt/scripts/algo_trading/polymarket_runner.py`
  One bounded paper-bot cycle plus a loop wrapper used by `algo_live_runner.py`.
- `fincept-qt/scripts/algo_trading/tests/fixtures/polymarket_gamma_markets.json`
  Official-shape Gamma fixture with `source_api` and `fetched_at`.
- `fincept-qt/scripts/algo_trading/tests/fixtures/polymarket_clob_book_yes.json`
  Official-shape CLOB order-book fixture with `source_api` and `fetched_at`.
- `fincept-qt/scripts/algo_trading/tests/fixtures/polymarket_clob_book_stale.json`
  Same shape as the CLOB fixture, but with an old `fetched_at` timestamp for stale-data tests.
- `fincept-qt/scripts/algo_trading/tests/test_polymarket_sources.py`
- `fincept-qt/scripts/algo_trading/tests/test_polymarket_config.py`
- `fincept-qt/scripts/algo_trading/tests/test_polymarket_scanner.py`
- `fincept-qt/scripts/algo_trading/tests/test_polymarket_edge.py`
- `fincept-qt/scripts/algo_trading/tests/test_polymarket_risk.py`
- `fincept-qt/scripts/algo_trading/tests/test_polymarket_paper.py`
- `fincept-qt/scripts/algo_trading/tests/test_polymarket_runner_smoke.py`
- `fincept-qt/tests/algo_trading/test_algo_polymarket_config.cpp`
  Minimal Qt Test for C++ save/load parsing and config preservation if linking remains small.

Modify:

- `fincept-qt/scripts/algo_trading/backtest_engine.py`
  Extend strategy schema with `bot_config` JSON and ensure save/list preserves it.
- `fincept-qt/scripts/algo_trading/algo_live_runner.py`
  Dispatch `market_type = polymarket` to `polymarket_runner.py`; keep existing non-Polymarket logic unchanged.
- `fincept-qt/scripts/algo_trading/algo_manager.py`
  Include Polymarket paper metrics and skipped counts in `list_deployments`.
- `fincept-qt/src/services/algo_trading/AlgoTradingTypes.h`
  Add `QJsonObject bot_config` and Polymarket deployment summary fields.
- `fincept-qt/src/services/algo_trading/AlgoTradingService.cpp`
  Save/list `bot_config`; parse Polymarket deployment summary fields.
- `fincept-qt/src/screens/algo_trading/StrategyBuilderPanel.h`
  Add Polymarket scan/edge/risk controls as private members.
- `fincept-qt/src/screens/algo_trading/StrategyBuilderPanel.cpp`
  Serialize and load `bot_config`; show Polymarket controls only when market type is Polymarket.
- `fincept-qt/src/screens/algo_trading/DeploymentDashboard.h`
  Add helper declarations for Polymarket summary rendering if needed.
- `fincept-qt/src/screens/algo_trading/DeploymentDashboard.cpp`
  Show candidate count, skipped count, active paper positions, and latest signal summary for Polymarket deployments.
- `fincept-qt/src/screens/polymarket/PolymarketDetailPanel.h`
  Add a setter for bot observations.
- `fincept-qt/src/screens/polymarket/PolymarketDetailPanel.cpp`
  Render a compact native Qt bot observation section on the Overview page.
- `fincept-qt/src/screens/polymarket/PolymarketScreen.cpp`
  Query latest stored bot observation for selected market and pass it to the detail panel.
- `fincept-qt/tests/CMakeLists.txt`
  Add the optional C++ Qt Test target only if the target can link without pulling the full application.

## Implementation Tasks

### Task 1: Python Test Fixtures, Config Contract, And Official Source Client

**Files:**
- Create: `fincept-qt/scripts/algo_trading/polymarket_config.py`
- Create: `fincept-qt/scripts/algo_trading/tests/fixtures/polymarket_gamma_markets.json`
- Create: `fincept-qt/scripts/algo_trading/tests/fixtures/polymarket_clob_book_yes.json`
- Create: `fincept-qt/scripts/algo_trading/tests/fixtures/polymarket_clob_book_stale.json`
- Create: `fincept-qt/scripts/algo_trading/tests/test_polymarket_sources.py`
- Create: `fincept-qt/scripts/algo_trading/tests/test_polymarket_config.py`
- Create: `fincept-qt/scripts/algo_trading/polymarket_sources.py`

- [ ] **Step 1: Write the failing config and source authenticity tests**

Add tests that load fixture JSON, assert every payload has official source metadata, and verify the shared default `bot_config`.

```python
def test_default_bot_config_contains_required_controls():
    cfg = default_bot_config()
    assert cfg["strategy_mode"] == "auto_scan"
    assert cfg["sort_by"] == "volume"
    assert cfg["min_time_to_expiry_hours"] == 24
    assert cfg["freshness_ttl_sec"] == 30
    assert cfg["stop_loss_pct"] == 30.0
    assert cfg["take_profit_pct"] == 50.0
    assert "momentum_weight" in cfg

def test_fixture_requires_source_metadata():
    payload = load_fixture("polymarket_gamma_markets.json")
    assert payload["source_api"] == "https://gamma-api.polymarket.com"
    assert payload["fetched_at"]
    assert isinstance(payload["data"], list)

def test_unlabeled_market_data_is_rejected():
    with pytest.raises(ValueError, match="source_api"):
        validate_source_payload({"data": []}, allowed_api="https://gamma-api.polymarket.com")

def test_rest_source_wraps_gamma_markets_with_metadata(monkeypatch):
    source = PolymarketRestSource(now=lambda: "2026-04-30T00:00:00Z")
    monkeypatch.setattr(source.session, "get", fake_gamma_response)
    payload = source.fetch_gamma_markets(limit=10, sort_by="volume")
    assert payload["source_api"] == "https://gamma-api.polymarket.com"
    assert payload["fetched_at"] == "2026-04-30T00:00:00Z"
    assert payload["source_payload_hash"]
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `python -m pytest fincept-qt/scripts/algo_trading/tests/test_polymarket_config.py fincept-qt/scripts/algo_trading/tests/test_polymarket_sources.py -q`

Expected: FAIL because `polymarket_config.py`, `polymarket_sources.py`, and helpers do not exist.

- [ ] **Step 3: Add config defaults and official-source helpers**

In `polymarket_config.py`, implement:

```python
DEFAULT_BOT_CONFIG = {...}  # exact keys from Shared Bot Config Contract

def default_bot_config(overrides: dict | None = None) -> dict:
    cfg = dict(DEFAULT_BOT_CONFIG)
    if overrides:
        cfg.update(overrides)
    return cfg
```

In `polymarket_sources.py`, implement validation plus live REST source methods:

```python
ALLOWED_APIS = {
    "gamma": "https://gamma-api.polymarket.com",
    "clob": "https://clob.polymarket.com",
    "data": "https://data-api.polymarket.com",
}

def validate_source_payload(payload: dict, allowed_api: str) -> dict:
    if payload.get("source_api") != allowed_api:
        raise ValueError("source_api is required and must be official Polymarket API")
    if not payload.get("fetched_at"):
        raise ValueError("fetched_at is required")
    if "data" not in payload:
        raise ValueError("data is required")
    return payload

class PolymarketRestSource:
    def fetch_gamma_markets(self, *, limit: int, sort_by: str) -> dict: ...
    def fetch_clob_order_book(self, token_id: str) -> dict: ...
```

`fetch_gamma_markets` must call `https://gamma-api.polymarket.com/markets` with active/open filters. `fetch_clob_order_book` must call `https://clob.polymarket.com/book`. Both wrap response JSON as `{source_api, fetched_at, data, source_payload_hash}`.

- [ ] **Step 4: Run the test and verify it passes**

Run: `python -m pytest fincept-qt/scripts/algo_trading/tests/test_polymarket_config.py fincept-qt/scripts/algo_trading/tests/test_polymarket_sources.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add fincept-qt/scripts/algo_trading/polymarket_config.py fincept-qt/scripts/algo_trading/polymarket_sources.py fincept-qt/scripts/algo_trading/tests
git commit -m "test: add polymarket source authenticity fixtures"
```

### Task 2: Shared Polymarket Bot Models

**Files:**
- Create: `fincept-qt/scripts/algo_trading/polymarket_models.py`
- Test: `fincept-qt/scripts/algo_trading/tests/test_polymarket_scanner.py`

- [ ] **Step 1: Write failing model normalization tests**

```python
def test_order_book_best_prices_parse_string_numbers():
    book = OrderBook.from_clob({
        "asset_id": "123",
        "bids": [{"price": "0.41", "size": "100"}],
        "asks": [{"price": "0.43", "size": "80"}],
    }, source_api="https://clob.polymarket.com", fetched_at="2026-04-30T00:00:00Z")
    assert book.best_bid == 0.41
    assert book.best_ask == 0.43
    assert book.spread == 0.02
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `python -m pytest fincept-qt/scripts/algo_trading/tests/test_polymarket_scanner.py -q`

Expected: FAIL because `OrderBook` does not exist.

- [ ] **Step 3: Implement dataclasses**

Implement focused dataclasses:

```python
@dataclass
class OrderLevel:
    price: float
    size: float

@dataclass
class OrderBook:
    asset_id: str
    bids: list[OrderLevel]
    asks: list[OrderLevel]
    source_api: str
    fetched_at: str

    @property
    def best_bid(self) -> float | None: ...
    @property
    def best_ask(self) -> float | None: ...
    @property
    def spread(self) -> float | None: ...
```

Also add `MarketCandidate`, `SignalDecision`, `RiskConfig`, `PaperFill`, and `PaperPosition`.

- [ ] **Step 4: Run model tests**

Run: `python -m pytest fincept-qt/scripts/algo_trading/tests/test_polymarket_scanner.py -q`

Expected: PASS for model tests.

- [ ] **Step 5: Commit**

```bash
git add fincept-qt/scripts/algo_trading/polymarket_models.py fincept-qt/scripts/algo_trading/tests/test_polymarket_scanner.py
git commit -m "feat: add polymarket paper bot models"
```

### Task 3: Candidate Scanner

**Files:**
- Create: `fincept-qt/scripts/algo_trading/polymarket_scanner.py`
- Modify: `fincept-qt/scripts/algo_trading/tests/test_polymarket_scanner.py`

- [ ] **Step 1: Write failing scanner tests**

Cover active/closed filtering, price bounds, volume/liquidity thresholds, and skipped reasons.

```python
def test_scanner_filters_closed_low_liquidity_tags_and_expiry(gamma_fixture):
    result = scan_markets(
        gamma_fixture["data"],
        config={
            "min_volume": 1000,
            "min_liquidity": 500,
            "min_price": 0.05,
            "max_price": 0.95,
            "excluded_tags": ["sports"],
            "min_time_to_expiry_hours": 24,
            "sort_by": "volume",
        },
        fetched_at=gamma_fixture["fetched_at"],
    )
    assert [c.asset_id for c in result.candidates] == ["yes-token-1", "no-token-1"]
    assert any(s.reason == "closed" for s in result.skipped)
    assert any(s.reason == "low_liquidity" for s in result.skipped)
    assert any(s.reason == "excluded_tag" for s in result.skipped)
    assert any(s.reason == "near_expiry" for s in result.skipped)
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `python -m pytest fincept-qt/scripts/algo_trading/tests/test_polymarket_scanner.py -q`

Expected: FAIL because `scan_markets` does not exist.

- [ ] **Step 3: Implement scanner**

Implement `scan_markets(markets: list[dict], config: dict, fetched_at: str) -> ScanResult`.

Rules:

- require active and not closed
- parse `outcomes`, `outcomePrices`, `clobTokenIds` whether JSON strings or arrays
- create one candidate per outcome token
- skip missing token, price out of range, low volume, low liquidity
- skip excluded categories/tags
- skip markets with less than `min_time_to_expiry_hours`
- sort candidates by configured `sort_by`

- [ ] **Step 4: Run scanner tests**

Run: `python -m pytest fincept-qt/scripts/algo_trading/tests/test_polymarket_scanner.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add fincept-qt/scripts/algo_trading/polymarket_scanner.py fincept-qt/scripts/algo_trading/tests/test_polymarket_scanner.py
git commit -m "feat: scan polymarket paper bot candidates"
```

### Task 4: Heuristic Edge Engine

**Files:**
- Create: `fincept-qt/scripts/algo_trading/polymarket_edge.py`
- Create: `fincept-qt/scripts/algo_trading/tests/test_polymarket_edge.py`

- [ ] **Step 1: Write failing edge tests**

```python
def test_edge_uses_best_ask_for_buyable_yes_signal():
    candidate = make_candidate(outcome="Yes", price=0.40)
    book = make_book(best_bid=0.39, best_ask=0.42, bid_depth=200, ask_depth=200)
    decision = compute_edge_signal(candidate, book, {"min_edge": 0.04, "momentum_weight": 0.2, "imbalance_weight": 0.2})
    assert decision.estimated_probability > 0.42
    assert decision.edge == pytest.approx(decision.estimated_probability - 0.42)

def test_edge_rejects_insufficient_inputs():
    decision = compute_edge_signal(make_candidate(), None, {"min_edge": 0.04})
    assert decision.action == "skip"
    assert decision.reason == "missing_orderbook"

def test_edge_applies_weighted_spread_and_volatility_penalties():
    decision = compute_edge_signal(
        make_candidate(outcome="Yes", price=0.40, momentum=0.03, volatility=0.20),
        make_book(best_bid=0.35, best_ask=0.45, bid_depth=50, ask_depth=50),
        {"spread_penalty": 0.5, "volatility_penalty": 0.5},
    )
    assert decision.features["spread_penalty"] < 0
    assert decision.features["volatility_penalty"] < 0
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `python -m pytest fincept-qt/scripts/algo_trading/tests/test_polymarket_edge.py -q`

Expected: FAIL because `polymarket_edge.py` does not exist.

- [ ] **Step 3: Implement heuristic**

Implement:

```python
def compute_edge_signal(candidate: MarketCandidate, book: OrderBook | None, config: dict) -> SignalDecision:
    # base probability from latest candidate price
    # add bounded momentum contribution
    # add bounded order-book imbalance contribution
    # subtract volatility/spread penalties
    # clamp to [0.01, 0.99]
    # edge uses best ask for entry
    # use configured weights: momentum, volatility penalty, imbalance, liquidity, spread penalty
    # reject if confidence is below threshold
```

Keep it deterministic and explainable. Include `features` in the output.

- [ ] **Step 4: Run edge tests**

Run: `python -m pytest fincept-qt/scripts/algo_trading/tests/test_polymarket_edge.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add fincept-qt/scripts/algo_trading/polymarket_edge.py fincept-qt/scripts/algo_trading/tests/test_polymarket_edge.py
git commit -m "feat: add polymarket heuristic edge engine"
```

### Task 5: Risk Controls

**Files:**
- Create: `fincept-qt/scripts/algo_trading/polymarket_risk.py`
- Create: `fincept-qt/scripts/algo_trading/tests/test_polymarket_risk.py`

- [ ] **Step 1: Write failing risk tests**

```python
def test_risk_rejects_order_above_max_usdc():
    cfg = RiskConfig(max_order_usdc=25)
    result = check_entry_risk(signal=buy_signal(price=0.50, size=100), portfolio=empty_portfolio(), config=cfg)
    assert not result.ok
    assert result.reason == "max_order_usdc"

def test_risk_rejects_cooldown_same_market_direction():
    result = check_entry_risk(signal=buy_signal(), portfolio=portfolio_with_recent_trade(), config=RiskConfig(cooldown_minutes=10))
    assert not result.ok
    assert result.reason == "cooldown"

def test_risk_rejects_near_expiry_candidate():
    result = check_entry_risk(signal=buy_signal(hours_to_expiry=2), portfolio=empty_portfolio(), config=RiskConfig(min_time_to_expiry_hours=24))
    assert not result.ok
    assert result.reason == "near_expiry"
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `python -m pytest fincept-qt/scripts/algo_trading/tests/test_polymarket_risk.py -q`

Expected: FAIL because `polymarket_risk.py` does not exist.

- [ ] **Step 3: Implement risk checks**

Implement:

- max order USDC
- max total exposure
- daily loss limit
- max positions
- cooldown
- price range
- max spread
- minimum top-of-book depth
- minimum time to expiry
- stop loss, take profit, and trailing stop thresholds exposed for exit checks

- [ ] **Step 4: Run risk tests**

Run: `python -m pytest fincept-qt/scripts/algo_trading/tests/test_polymarket_risk.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add fincept-qt/scripts/algo_trading/polymarket_risk.py fincept-qt/scripts/algo_trading/tests/test_polymarket_risk.py
git commit -m "feat: enforce polymarket paper bot risk controls"
```

### Task 6: Paper Fill And Position Engine

**Files:**
- Create: `fincept-qt/scripts/algo_trading/polymarket_paper.py`
- Create: `fincept-qt/scripts/algo_trading/tests/test_polymarket_paper.py`

- [ ] **Step 1: Write failing paper-fill tests**

```python
def test_buy_fills_at_best_ask():
    fill = simulate_entry_fill(signal=buy_signal(size=10), book=make_book(best_bid=0.40, best_ask=0.42, ask_depth=20))
    assert fill.ok
    assert fill.price == 0.42
    assert fill.size == 10

def test_sell_fills_at_best_bid_and_realizes_pnl():
    pos = PaperPosition(asset_id="yes-token", size=10, avg_price=0.42)
    fill = simulate_exit_fill(pos, book=make_book(best_bid=0.55, best_ask=0.57, bid_depth=20), reason="take_profit")
    assert fill.price == 0.55
    assert fill.realized_pnl == pytest.approx(1.30)

def test_exit_reason_stop_loss_is_preserved():
    pos = PaperPosition(asset_id="yes-token", size=10, avg_price=0.60)
    fill = simulate_exit_fill(pos, book=make_book(best_bid=0.40, best_ask=0.42, bid_depth=20), reason="stop_loss")
    assert fill.reason == "stop_loss"
    assert fill.realized_pnl < 0
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `python -m pytest fincept-qt/scripts/algo_trading/tests/test_polymarket_paper.py -q`

Expected: FAIL because `polymarket_paper.py` does not exist.

- [ ] **Step 3: Implement top-of-book fill engine**

Implement:

- `simulate_entry_fill`
- `simulate_exit_fill`
- `apply_fill_to_position`
- `should_exit_position` for edge reversal/disappearance, stop loss, take profit, trailing stop, and closed/inactive markets
- skip when top-of-book depth is insufficient
- skip when bid/ask missing

- [ ] **Step 4: Run paper tests**

Run: `python -m pytest fincept-qt/scripts/algo_trading/tests/test_polymarket_paper.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add fincept-qt/scripts/algo_trading/polymarket_paper.py fincept-qt/scripts/algo_trading/tests/test_polymarket_paper.py
git commit -m "feat: simulate polymarket paper fills"
```

### Task 7: SQLite Store And Runner Smoke Test

**Files:**
- Create: `fincept-qt/scripts/algo_trading/polymarket_store.py`
- Create: `fincept-qt/scripts/algo_trading/polymarket_runner.py`
- Create: `fincept-qt/scripts/algo_trading/tests/test_polymarket_runner_smoke.py`

- [ ] **Step 1: Write failing bounded-cycle smoke test**

```python
def test_runner_one_cycle_writes_signal_and_paper_fill(tmp_path, gamma_fixture, book_fixture):
    db = tmp_path / "fincept.db"
    seed_strategy(db, market_type="polymarket", bot_config={"max_candidates": 2, "min_edge": 0.01})
    result = run_polymarket_cycle(
        db_path=str(db),
        deployment_id="dep-1",
        strategy_id="strat-1",
        market_payload=gamma_fixture,
        order_books={"yes-token-1": book_fixture},
        now="2026-04-30T00:00:00Z",
    )
    assert result["success"] is True
    assert count_rows(db, "algo_polymarket_signals") >= 1
    assert count_rows(db, "algo_polymarket_paper_trades") >= 1

def test_runner_skips_stale_orderbook(tmp_path, gamma_fixture, stale_book_fixture):
    db = tmp_path / "fincept.db"
    seed_strategy(db, market_type="polymarket", bot_config={"freshness_ttl_sec": 30})
    result = run_polymarket_cycle(
        db_path=str(db),
        deployment_id="dep-1",
        strategy_id="strat-1",
        market_payload=gamma_fixture,
        order_books={"yes-token-1": stale_book_fixture},
        now="2026-04-30T00:10:00Z",
    )
    assert result["fills"] == 0
    assert latest_skip_reason(db) == "stale_orderbook"

def test_runner_exits_existing_position_on_edge_reversal(tmp_path, gamma_fixture, book_fixture):
    db = tmp_path / "fincept.db"
    seed_strategy(db, market_type="polymarket", bot_config={"min_edge": 0.04})
    seed_position(db, deployment_id="dep-1", asset_id="yes-token-1", size=10, avg_price=0.60)
    result = run_polymarket_cycle(
        db_path=str(db),
        deployment_id="dep-1",
        strategy_id="strat-1",
        market_payload=gamma_fixture,
        order_books={"yes-token-1": book_fixture},
        edge_overrides={"yes-token-1": {"action": "exit", "reason": "edge_reversal"}},
        now="2026-04-30T00:00:00Z",
    )
    assert result["exits"] == 1
    assert latest_trade_side(db) == "SELL"
```

- [ ] **Step 2: Run the smoke test and verify it fails**

Run: `python -m pytest fincept-qt/scripts/algo_trading/tests/test_polymarket_runner_smoke.py -q`

Expected: FAIL because store/runner do not exist.

- [ ] **Step 3: Implement additive SQLite schema**

Create tables:

- `algo_polymarket_candidates`
- `algo_polymarket_signals`
- `algo_polymarket_skips`
- `algo_polymarket_paper_trades`
- `algo_polymarket_paper_positions`

Use `CREATE TABLE IF NOT EXISTS`. Do not modify existing migrations for this slice unless C++ needs startup schema guarantees.

- [ ] **Step 4: Implement one bounded cycle**

`run_polymarket_cycle(...)` should:

1. load strategy config
2. scan fixture/live markets
3. fetch order books from `PolymarketRestSource` or accept injected order books in tests
4. reject stale market or order-book data using `freshness_ttl_sec`
5. evaluate existing open positions for exits before new entries
6. compute edge signal
7. evaluate existing indicator entry/exit conditions when configured
8. check risk
9. simulate paper entry or exit fills
10. persist candidate/signal/skip/fill/position/metrics
11. return JSON-serializable summary

- [ ] **Step 5: Run all Python Polymarket tests**

Run: `python -m pytest fincept-qt/scripts/algo_trading/tests -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add fincept-qt/scripts/algo_trading/polymarket_store.py fincept-qt/scripts/algo_trading/polymarket_runner.py fincept-qt/scripts/algo_trading/tests/test_polymarket_runner_smoke.py
git commit -m "feat: persist polymarket paper bot cycle"
```

### Task 8: Integrate Polymarket Mode Into `algo_live_runner.py`

**Files:**
- Modify: `fincept-qt/scripts/algo_trading/algo_live_runner.py`
- Modify: `fincept-qt/scripts/algo_trading/backtest_engine.py`
- Modify: `fincept-qt/scripts/algo_trading/algo_manager.py`
- Modify: `fincept-qt/scripts/algo_trading/tests/test_polymarket_runner_smoke.py`

- [ ] **Step 1: Write failing dispatch/schema tests**

Add tests that:

- save a strategy with `bot_config`
- load it back with `bot_config`
- call a bounded runner entry point for Polymarket mode
- verify configured entry conditions are evaluated before entry
- verify configured exit conditions are evaluated before exit

- [ ] **Step 2: Run tests and verify failure**

Run: `python -m pytest fincept-qt/scripts/algo_trading/tests/test_polymarket_runner_smoke.py -q`

Expected: FAIL because `bot_config` is not persisted and runner does not dispatch.

- [ ] **Step 3: Extend strategy schema**

In `backtest_engine.py`:

- add `bot_config TEXT DEFAULT '{}'`
- alter existing DBs to add `bot_config`
- save `params.get("bot_config", {})`
- list strategies with parsed `bot_config`

- [ ] **Step 4: Add runner dispatch**

In `algo_live_runner.py`, after loading strategy:

```python
if strategy.get("market_type") == "polymarket":
    from polymarket_runner import run_polymarket_loop
    return run_polymarket_loop(args=args, strategy=strategy)
```

Make sure the existing non-Polymarket path is unchanged.

- [ ] **Step 5: Add indicator-condition integration**

In `polymarket_runner.py`, normalize recent Polymarket prices into the same OHLCV shape used by `condition_evaluator.py`. Reuse `evaluate_condition_group` for:

- entry conditions before a new paper entry
- exit conditions before a paper exit

If there are no configured entry conditions, edge-only entry is allowed. If indicator data is insufficient, skip with `indicator_data_insufficient`.

- [ ] **Step 6: Extend deployment listing**

In `algo_manager.py`, left join aggregate Polymarket paper tables by deployment id and include:

- `poly_candidate_count`
- `poly_signal_count`
- `poly_skipped_count`
- `poly_position_count`
- `poly_latest_signal`
- `poly_bot_state`
- `poly_scanned_count`
- `poly_realized_pnl`
- `poly_unrealized_pnl`
- `poly_top_skipped_reasons`
- `poly_recent_fills`
- `poly_latest_signal_details`

- [ ] **Step 7: Run tests**

Run: `python -m pytest fincept-qt/scripts/algo_trading/tests -q`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add fincept-qt/scripts/algo_trading/algo_live_runner.py fincept-qt/scripts/algo_trading/backtest_engine.py fincept-qt/scripts/algo_trading/algo_manager.py fincept-qt/scripts/algo_trading/tests
git commit -m "feat: run polymarket paper bot deployments"
```

### Task 9: C++ Service Types And Parsing

**Files:**
- Modify: `fincept-qt/src/services/algo_trading/AlgoTradingTypes.h`
- Modify: `fincept-qt/src/services/algo_trading/AlgoTradingService.cpp`
- Optional Create: `fincept-qt/tests/algo_trading/test_algo_polymarket_config.cpp`
- Optional Modify: `fincept-qt/tests/CMakeLists.txt`

- [ ] **Step 1: Write failing C++ parsing test if lightweight linking is possible**

Test that a JSON strategy with `bot_config` parses into `AlgoStrategy::bot_config` and a deployment summary parses Polymarket counts.

If direct C++ test linkage is too heavy, document that this slice is covered by Python integration and manual service-level review, then proceed.

- [ ] **Step 2: Run C++ test and verify failure**

Configure if needed:

```bash
cmake -S fincept-qt -B fincept-qt/build/tests -DFINCEPT_BUILD_TESTS=ON
cmake --build fincept-qt/build/tests --target test_algo_polymarket_config
ctest --test-dir fincept-qt/build/tests -R algo_polymarket_config --output-on-failure
```

Expected: FAIL before fields exist.

- [ ] **Step 3: Add C++ fields**

In `AlgoStrategy`:

- `QJsonObject bot_config`

In `AlgoDeployment`:

- `int poly_candidate_count = 0`
- `int poly_signal_count = 0`
- `int poly_skipped_count = 0`
- `int poly_position_count = 0`
- `QString poly_latest_signal`
- `QString poly_bot_state`
- `int poly_scanned_count = 0`
- `double poly_realized_pnl = 0.0`
- `double poly_unrealized_pnl = 0.0`
- `QString poly_top_skipped_reasons`
- `QString poly_recent_fills`
- `QString poly_latest_signal_details`

- [ ] **Step 4: Save and parse fields**

In `AlgoTradingService.cpp`:

- include `bot_config` in save JSON
- parse `bot_config` in `parse_strategies`
- parse Polymarket deployment summary fields in `parse_deployments`, including bot state, scanned count, realized/unrealized PnL, top skipped reasons, recent fills, and latest signal details

- [ ] **Step 5: Run verification**

Run Python regression:

`python -m pytest fincept-qt/scripts/algo_trading/tests -q`

Run C++ test if added:

`ctest --test-dir fincept-qt/build/tests -R algo_polymarket_config --output-on-failure`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add fincept-qt/src/services/algo_trading/AlgoTradingTypes.h fincept-qt/src/services/algo_trading/AlgoTradingService.cpp fincept-qt/tests
git commit -m "feat: carry polymarket bot config through algo service"
```

### Task 10: Strategy Builder Native Qt Controls

**Files:**
- Modify: `fincept-qt/src/screens/algo_trading/StrategyBuilderPanel.h`
- Modify: `fincept-qt/src/screens/algo_trading/StrategyBuilderPanel.cpp`

- [ ] **Step 1: Identify existing save/load methods**

Read `on_save()`, `on_backtest()`, and `load_strategy()` in `StrategyBuilderPanel.cpp`.

- [ ] **Step 2: Add controls in a hidden Polymarket section**

Add native Qt controls for:

- market type option `Polymarket` if it is not already present
- strategy mode option `Auto Scan`
- scan interval
- max candidates
- sort mode
- min volume
- min liquidity
- max spread
- min depth
- min/max price
- excluded categories/tags
- min time to expiry
- min edge
- confidence threshold
- momentum weight
- volatility penalty
- imbalance weight
- liquidity weight
- spread penalty
- paper order size
- max order USDC
- max exposure
- daily loss limit
- max positions
- cooldown minutes
- stop loss / take profit / trailing stop

Keep the section hidden unless `market_type_combo_` is `polymarket`.

- [ ] **Step 3: Serialize controls to `bot_config`**

In `on_save()`, add:

```cpp
if (strategy.market_type == "polymarket") {
    strategy.bot_config = gather_polymarket_bot_config();
    strategy.bot_config["strategy_mode"] = "auto_scan";
}
```

- [ ] **Step 4: Load controls from `bot_config`**

In `load_strategy()`, populate controls with defaults when keys are missing.

- [ ] **Step 5: Build-check touched C++**

Run the smallest available build target. If full app build is the only option:

`cmake --build fincept-qt/build --target FinceptTerminal --config Release`

Expected: build succeeds.

- [ ] **Step 6: Commit**

```bash
git add fincept-qt/src/screens/algo_trading/StrategyBuilderPanel.h fincept-qt/src/screens/algo_trading/StrategyBuilderPanel.cpp
git commit -m "feat: configure polymarket paper bot strategies"
```

### Task 11: Deployment Dashboard Observability

**Files:**
- Modify: `fincept-qt/src/screens/algo_trading/DeploymentDashboard.h`
- Modify: `fincept-qt/src/screens/algo_trading/DeploymentDashboard.cpp`

- [ ] **Step 1: Add Polymarket summary render helper**

Add a helper such as:

```cpp
QWidget* build_polymarket_summary(const AlgoDeployment& d, QWidget* parent);
```

- [ ] **Step 2: Render summary only for Polymarket deployments**

Use `d.symbol`, `d.mode`, and new `poly_*` fields to show:

- bot state: scanning, subscribed, trading, paused, stopped, error
- scanned markets count
- candidates
- signals
- skipped
- top skipped reasons
- active paper positions
- realized PnL
- unrealized PnL
- recent paper fills
- latest signal
- latest signal details: market, outcome, price, estimated probability, edge, action, and reason

- [ ] **Step 3: Preserve existing deployment cards**

Verify non-Polymarket cards still render the same metrics as before.

- [ ] **Step 4: Build-check**

Run:

`cmake --build fincept-qt/build --target FinceptTerminal --config Release`

Expected: build succeeds.

- [ ] **Step 5: Commit**

```bash
git add fincept-qt/src/screens/algo_trading/DeploymentDashboard.h fincept-qt/src/screens/algo_trading/DeploymentDashboard.cpp
git commit -m "feat: show polymarket paper bot deployment status"
```

### Task 12: Prediction Markets Observation Section

**Files:**
- Modify: `fincept-qt/src/screens/polymarket/PolymarketDetailPanel.h`
- Modify: `fincept-qt/src/screens/polymarket/PolymarketDetailPanel.cpp`
- Modify: `fincept-qt/src/screens/polymarket/PolymarketScreen.cpp`

- [ ] **Step 1: Add a compact observation model**

Prefer a `QVariantMap` setter to avoid adding a new service type:

```cpp
void set_bot_observation(const QVariantMap& observation);
```

Expected keys:

- `tracked`
- `outcome_signals`: array of `{outcome, asset_id, latest_signal, edge, estimated_probability, price, reason, updated_at, source_api}`
- `recent_trades`: array of recent paper fills with `{side, outcome, size, price, realized_pnl, reason, created_at}`
- `positions`: array of current paper positions with `{outcome, asset_id, size, avg_price, unrealized_pnl}`
- `freshness`: object with `last_market_fetch`, `last_orderbook_update`, `last_signal_update`
- `source_labels`: array such as `["Polymarket Gamma API", "Polymarket CLOB API"]`

- [ ] **Step 2: Render a native Qt Overview section**

In the overview page, add a small section titled `PAPER BOT` with:

- one row per relevant outcome signal
- current paper positions
- recent paper trades
- freshness timestamps
- source labels

- [ ] **Step 3: Query stored observation on market selection**

In `PolymarketScreen::select_market`, query the SQLite store through a small local helper or existing DB access pattern. Match by `condition_id` or `asset_id`.

The query contract must return multiple outcome signals and recent paper trades for the selected market, not just a single latest signal.

- [ ] **Step 4: Handle no observation**

If no record exists, show `Not tracked by paper bot`.

- [ ] **Step 5: Build-check**

Run:

`cmake --build fincept-qt/build --target FinceptTerminal --config Release`

Expected: build succeeds.

- [ ] **Step 6: Commit**

```bash
git add fincept-qt/src/screens/polymarket/PolymarketDetailPanel.h fincept-qt/src/screens/polymarket/PolymarketDetailPanel.cpp fincept-qt/src/screens/polymarket/PolymarketScreen.cpp
git commit -m "feat: show polymarket paper bot market observations"
```

### Task 13: End-To-End Verification Script

**Files:**
- Create: `fincept-qt/scripts/algo_trading/tests/test_polymarket_runner_smoke.py` if not already complete
- Optional Create: `fincept-qt/scripts/algo_trading/run_polymarket_paper_smoke.py`

- [ ] **Step 1: Add a command-line smoke path**

Allow a bounded one-cycle run without live network:

```bash
python fincept-qt/scripts/algo_trading/polymarket_runner.py smoke --fixture-dir fincept-qt/scripts/algo_trading/tests/fixtures --db <tmp-db>
```

- [ ] **Step 2: Verify it writes expected JSON**

Expected stdout contains:

```json
{"success": true, "scanned": 1, "signals": 1}
```

- [ ] **Step 3: Add test assertion around CLI**

Use `subprocess.run` in pytest to ensure the smoke command exits 0 and writes rows.

- [ ] **Step 4: Run full Python tests**

Run:

`python -m pytest fincept-qt/scripts/algo_trading/tests -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add fincept-qt/scripts/algo_trading/polymarket_runner.py fincept-qt/scripts/algo_trading/tests/test_polymarket_runner_smoke.py
git commit -m "test: add polymarket paper bot smoke command"
```

### Task 14: Final Regression And Documentation Notes

**Files:**
- Modify: `docs/superpowers/specs/2026-04-30-polymarket-paper-bot-design.md` only if implementation discovers a spec correction.
- Optional Modify: `fincept-qt/docs/polymarket_api_links.txt` only if adding missing official references.

- [ ] **Step 1: Run all Python Polymarket tests**

Run:

`python -m pytest fincept-qt/scripts/algo_trading/tests -q`

Expected: PASS.

- [ ] **Step 2: Run C++ tests if configured**

Run:

`ctest --test-dir fincept-qt/build/tests --output-on-failure`

Expected: PASS, or document why local Qt test build is unavailable.

- [ ] **Step 3: Build the app**

Run the repo's established build command for the current machine. Prefer an existing configured build directory:

`cmake --build fincept-qt/build --target FinceptTerminal --config Release`

Expected: build succeeds.

- [ ] **Step 4: Confirm live trading remains unreachable**

Search:

`rg -n "prediction_polymarket.py|place_order|derive_api_creds|private_key" fincept-qt/scripts/algo_trading fincept-qt/src/services/algo_trading fincept-qt/src/screens/algo_trading`

Expected:

- no paper-bot code calls live `place_order`
- no paper-bot UI asks for private keys
- any result is documentation or unrelated existing adapter code

- [ ] **Step 5: Confirm Git state**

Run:

`git status --short`

Expected: clean except intentionally untracked local build artifacts.

- [ ] **Step 6: Final commit if needed**

```bash
git add <remaining intended files>
git commit -m "chore: finalize polymarket paper bot verification"
```

## Execution Notes

- Keep commits small and task-scoped.
- Do not refactor unrelated Qt screens.
- Do not change global theme or navigation.
- Do not add a web server or web UI.
- Use fixed fixtures for automated acceptance; live Polymarket network calls are useful for manual diagnostics but not required for tests.
- If a test fails, stop and use @superpowers:systematic-debugging before changing code.
- Before final completion, use @superpowers:verification-before-completion and include exact commands and outcomes.
