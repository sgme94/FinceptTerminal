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

## File Structure

Create:

- `fincept-qt/scripts/algo_trading/polymarket_models.py`
  Small dataclasses and JSON helpers for markets, order books, candidates, signals, risk config, paper fills, and paper positions.
- `fincept-qt/scripts/algo_trading/polymarket_sources.py`
  Official Polymarket REST source client and fixture-loading seam. All returned market data carries `source_api` and `fetched_at`.
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
- `fincept-qt/scripts/algo_trading/tests/test_polymarket_sources.py`
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

### Task 1: Python Test Fixtures And Import Harness

**Files:**
- Create: `fincept-qt/scripts/algo_trading/tests/fixtures/polymarket_gamma_markets.json`
- Create: `fincept-qt/scripts/algo_trading/tests/fixtures/polymarket_clob_book_yes.json`
- Create: `fincept-qt/scripts/algo_trading/tests/test_polymarket_sources.py`
- Create: `fincept-qt/scripts/algo_trading/polymarket_sources.py`

- [ ] **Step 1: Write the failing source authenticity tests**

Add tests that load fixture JSON and assert every payload has official source metadata.

```python
def test_fixture_requires_source_metadata():
    payload = load_fixture("polymarket_gamma_markets.json")
    assert payload["source_api"] == "https://gamma-api.polymarket.com"
    assert payload["fetched_at"]
    assert isinstance(payload["data"], list)

def test_unlabeled_market_data_is_rejected():
    with pytest.raises(ValueError, match="source_api"):
        validate_source_payload({"data": []}, allowed_api="https://gamma-api.polymarket.com")
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `python -m pytest fincept-qt/scripts/algo_trading/tests/test_polymarket_sources.py -q`

Expected: FAIL because `polymarket_sources.py` and helpers do not exist.

- [ ] **Step 3: Add official-source helpers**

In `polymarket_sources.py`, implement:

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
```

- [ ] **Step 4: Run the test and verify it passes**

Run: `python -m pytest fincept-qt/scripts/algo_trading/tests/test_polymarket_sources.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add fincept-qt/scripts/algo_trading/polymarket_sources.py fincept-qt/scripts/algo_trading/tests
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
def test_scanner_filters_closed_and_low_liquidity_markets(gamma_fixture):
    result = scan_markets(
        gamma_fixture["data"],
        config={"min_volume": 1000, "min_liquidity": 500, "min_price": 0.05, "max_price": 0.95},
        fetched_at=gamma_fixture["fetched_at"],
    )
    assert [c.asset_id for c in result.candidates] == ["yes-token-1", "no-token-1"]
    assert any(s.reason == "closed" for s in result.skipped)
    assert any(s.reason == "low_liquidity" for s in result.skipped)
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
    decision = compute_edge_signal(candidate, book, {"min_edge": 0.04})
    assert decision.estimated_probability > 0.42
    assert decision.edge == pytest.approx(decision.estimated_probability - 0.42)

def test_edge_rejects_insufficient_inputs():
    decision = compute_edge_signal(make_candidate(), None, {"min_edge": 0.04})
    assert decision.action == "skip"
    assert decision.reason == "missing_orderbook"
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
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `python -m pytest fincept-qt/scripts/algo_trading/tests/test_polymarket_paper.py -q`

Expected: FAIL because `polymarket_paper.py` does not exist.

- [ ] **Step 3: Implement top-of-book fill engine**

Implement:

- `simulate_entry_fill`
- `simulate_exit_fill`
- `apply_fill_to_position`
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
3. fetch or accept injected order books
4. compute signal
5. check risk
6. simulate paper fill
7. persist candidate/signal/fill/position/metrics
8. return JSON-serializable summary

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

- [ ] **Step 5: Extend deployment listing**

In `algo_manager.py`, left join aggregate Polymarket paper tables by deployment id and include:

- `poly_candidate_count`
- `poly_signal_count`
- `poly_skipped_count`
- `poly_position_count`
- `poly_latest_signal`

- [ ] **Step 6: Run tests**

Run: `python -m pytest fincept-qt/scripts/algo_trading/tests -q`

Expected: PASS.

- [ ] **Step 7: Commit**

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

- [ ] **Step 4: Save and parse fields**

In `AlgoTradingService.cpp`:

- include `bot_config` in save JSON
- parse `bot_config` in `parse_strategies`
- parse Polymarket deployment summary fields in `parse_deployments`

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

- scan interval
- max candidates
- min volume
- min liquidity
- max spread
- min depth
- min/max price
- min edge
- confidence threshold
- max order USDC
- max exposure
- daily loss limit
- max positions
- cooldown minutes

Keep the section hidden unless `market_type_combo_` is `polymarket`.

- [ ] **Step 3: Serialize controls to `bot_config`**

In `on_save()`, add:

```cpp
if (strategy.market_type == "polymarket") {
    strategy.bot_config = gather_polymarket_bot_config();
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

- candidates
- signals
- skipped
- active paper positions
- latest signal

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
- `latest_signal`
- `edge`
- `estimated_probability`
- `position_size`
- `updated_at`
- `source_api`

- [ ] **Step 2: Render a native Qt Overview section**

In the overview page, add a small section titled `PAPER BOT` with status, signal, edge, position, and freshness.

- [ ] **Step 3: Query stored observation on market selection**

In `PolymarketScreen::select_market`, query the SQLite store through a small local helper or existing DB access pattern. Match by `condition_id` or `asset_id`.

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
