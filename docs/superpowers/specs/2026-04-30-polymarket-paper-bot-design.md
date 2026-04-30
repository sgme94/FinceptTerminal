# Polymarket Paper Bot Design

Date: 2026-04-30

## Scope

Build a Polymarket automatic trading bot inside Fincept Terminal as a paper-trading feature. The first version must not place live CLOB orders, read private keys, derive Polymarket API credentials, or call the live `prediction_polymarket.py place_order` path.

Fincept Terminal is a native Qt6/C++20 desktop application, distributed on Windows as `FinceptTerminal.exe`. This design must reuse the existing desktop UI and must not introduce a separate web frontend.

The user-facing goal is to let non-technical users run a conservative Polymarket paper bot from the existing Algo Trading workflow, while letting future AI agents develop and verify the feature through automated tests rather than manual user acceptance.

## User Decisions

- Mode: paper trading only.
- Product entry: existing `Algo Trading` screen.
- Signal style: minimal combined support for indicator conditions and heuristic edge.
- Market selection: automatic scan of popular active Polymarket markets.
- Paper fill model: top-of-book conservative execution.
- Future fill model: document upgrade path to multi-level depth simulation.
- Risk controls: conservative defaults with strategy-level overrides.
- Result visibility: `Algo Trading` is the control surface; `Prediction Markets` shows related bot observations for the selected market.
- Runtime style: REST scan plus WebSocket updates for candidates.
- Edge model: lightweight heuristic probability, not particle-filter/Bayesian in v1.
- UI implementation: reuse native Qt desktop pages and existing widgets where practical.
- Upstream compatibility: keep changes narrow so the fork can continue receiving upstream updates.

## Existing Architecture

Relevant existing modules:

- `fincept-qt/src/services/algo_trading/*`
  Strategy CRUD, deployment lifecycle, backtesting, scanning, and Python runner orchestration.
- `fincept-qt/scripts/algo_trading/*`
  Python strategy evaluation, backtest engine, scanner, deployment runner, and deployment manager.
- `fincept-qt/src/services/polymarket/*`
  Polymarket Gamma/CLOB/Data API reads and CLOB WebSocket integration.
- `fincept-qt/src/services/prediction/*`
  Unified prediction-market model and adapters for Polymarket/Kalshi.
- `fincept-qt/scripts/prediction_polymarket.py`
  Existing authenticated Polymarket trading bridge. This remains out of scope for v1 paper mode.
- `fincept-qt/src/screens/algo_trading/*`
  Native Qt Algo Trading screens.
- `fincept-qt/src/screens/polymarket/*`
  Native Qt Prediction Markets screens.

## Architecture

Implement the bot as a `market_type = "polymarket"` extension to the existing Algo Trading system. Do not create a new top-level product module.

Primary control surface:

- `Algo Trading`
  Create/configure strategies, deploy/stop the paper bot, and inspect deployments, signals, positions, fills, and PnL.

Secondary observation surface:

- `Prediction Markets`
  For the currently selected market, show whether the bot is tracking it, latest signal state, paper position, recent paper trades, and data freshness.

Python owns trading decisions:

- Add Polymarket-specific Python modules under `fincept-qt/scripts/algo_trading/`.
- Extend `algo_live_runner.py` to detect `market_type = "polymarket"` and run the Polymarket paper-bot loop.
- Keep C++ focused on strategy configuration, process orchestration, persistence access, and native UI display.

Suggested Python modules:

- `polymarket_scanner.py`
  Fetch and filter active markets.
- `polymarket_edge.py`
  Compute heuristic probability, confidence, and edge.
- `polymarket_risk.py`
  Enforce paper-bot risk controls.
- `polymarket_paper.py`
  Simulate paper fills, positions, realized/unrealized PnL, and skipped trade reasons.

Important process boundary:

- The existing DataHub is an in-process C++ pub/sub layer. The Python runner must not assume it can directly subscribe to C++ DataHub topics.
- V1 market-data access for the bot runner should go through an explicit Python data source abstraction:
  - REST reads from official Polymarket APIs are required.
  - Candidate WebSocket updates may be implemented with a Python-side CLOB WebSocket client.
  - If the C++ Polymarket WebSocket/DataHub path is reused for the bot, it must be via an explicit bridge, such as writing candidate price/order-book snapshots into SQLite with freshness metadata.
- The Qt DataHub path remains useful for desktop UI updates, but it is not by itself a cross-process runner feed.

## Data Authenticity

The bot must never generate market data with AI. AI/LLM components may explain bot output, but cannot create, repair, interpolate, or replace prices, order books, volumes, trades, or market status.

Allowed live data sources:

- `https://gamma-api.polymarket.com`
  Markets, events, outcomes, tags, and metadata.
- `https://clob.polymarket.com`
  Order books, price history, CLOB market data, and WebSocket market channel data.
- `https://data-api.polymarket.com`
  Trades, activity, positions, holders, leaderboard, and related public data.
- Local SQLite/cache rows that were previously fetched from those official sources.

Required metadata for cached or persisted source data:

- `source_api`
- `fetched_at`
- `condition_id` and/or `asset_id`
- `market_id` where available
- `source_payload_hash` where practical for fixtures or snapshots

Failure behavior:

- Missing data: skip.
- Stale data: skip.
- Empty order book: skip.
- Invalid JSON/API response: skip and record the error.
- AI-created or unlabeled data: reject in tests and do not trade.

Official documentation references:

- Polymarket API introduction: `https://docs.polymarket.com/api-reference/introduction`
- CLOB authentication: `https://docs.polymarket.com/developers/CLOB/authentication`
- CLOB market WebSocket channel: `https://docs.polymarket.com/developers/CLOB/websocket/market-channel`
- Order book endpoint: `https://docs.polymarket.com/api-reference/market-data/get-order-book`
- Rate limits: `https://docs.polymarket.com/quickstart/introduction/rate-limits`

## Runtime Data Flow

Deployment start:

1. User saves an Algo Trading strategy with `market_type = "polymarket"`.
2. `AlgoTradingService::deploy_strategy(...)` creates a deployment id and starts `algo_live_runner.py`.
3. Runner loads the strategy and enters Polymarket mode.

REST scan layer:

1. Every configured interval, fetch active, unclosed Polymarket markets.
2. Sort by volume or liquidity.
3. Filter markets and outcomes by:
   - active/closed status
   - minimum volume
   - minimum liquidity
   - price range
   - maximum spread
   - minimum top-of-book depth
   - minimum time to expiry
   - excluded categories/tags
4. Persist candidate state and skipped reasons.

Candidate real-time layer:

1. Subscribe to candidate tokens through a Python-side official CLOB WebSocket client, or through an explicit C++ to SQLite bridge if one is added.
2. Maintain a short rolling state per `asset_id`:
   - latest price
   - best bid
   - best ask
   - spread
   - top-of-book bid/ask depth
   - recent price window
   - momentum
   - realized volatility
   - order-book imbalance
3. If WebSocket support is not available in the first implementation slice, use bounded REST polling for candidate order books while keeping the data-source interface stable.
4. If WebSocket or REST candidate data is stale, fall back to the next REST scan; do not trade on stale quotes.

Signal computation:

- Indicator signal:
  Use Polymarket token price history normalized to OHLCV shape and pass it through the existing condition evaluation flow.
- Edge signal:
  `polymarket_edge.py` estimates `estimated_probability` from a heuristic model.
  - YES edge: `estimated_probability - best_ask`
  - NO edge: `(1 - estimated_probability) - best_ask`
- A paper entry requires:
  - scan filters pass
  - risk controls pass
  - edge threshold passes
  - optional indicator entry conditions pass
  - order book can support a conservative paper fill

Exit computation:

- Exit when edge disappears or reverses.
- Exit when configured indicator exit conditions pass.
- Exit on stop loss, take profit, or trailing stop.
- Exit or mark `closed_unsettled` when a market becomes inactive/closed.

## Heuristic Edge Model

V1 must be lightweight and explainable. It should not use `polymarket_quant_bot.py` particle-filter/Bayesian logic yet.

Inputs:

- recent price momentum
- realized volatility
- order-book imbalance
- spread
- liquidity
- top-of-book depth
- recent trade/activity count where available

Outputs:

- `estimated_probability`
- `confidence`
- `edge`
- `reason`
- per-feature contribution fields for debugging and UI explanation

The heuristic must clamp probabilities to valid ranges and must avoid producing a signal when inputs are insufficient.

Future enhancement:

- Replace or augment the heuristic with the existing `polymarket_quant_bot.py` particle-filter/Bayesian engine after the paper-bot architecture and tests are stable.

## Paper Fill Model

V1 execution is conservative top-of-book simulation:

- Buy fills at `best_ask`.
- Sell/exit fills at `best_bid`.
- Reject if there is no best bid/ask.
- Reject if spread exceeds configured maximum.
- Reject if top-of-book depth is less than requested size.
- Record every rejection with `skipped_reason`.
- Never call authenticated Polymarket order placement code.

Persisted fill fields:

- deployment id
- strategy id
- market id / condition id
- asset id
- question
- outcome
- side
- size
- fill price
- best bid
- best ask
- spread
- top-of-book depth
- estimated probability
- edge
- signal reason
- source timestamps
- paper/live mode

Future fill upgrade:

- Add a multi-level depth fill engine:
  - walk order-book levels
  - compute weighted average fill
  - simulate slippage
  - allow partial fill or rejection
  - record level-by-level fill details
- Keep the scanner, edge, risk, and UI interfaces stable so this can replace only the fill engine.

## Risk Controls

V1 uses conservative defaults with strategy-level overrides:

- max order value in USDC
- max total paper exposure
- daily loss limit
- max simultaneous positions
- cooldown per market/outcome/direction
- minimum market volume
- minimum liquidity
- maximum bid/ask spread
- minimum top-of-book depth
- price range filter, default skipping near-zero and near-one contracts
- minimum time to expiry
- stop loss
- take profit
- trailing stop
- no repeated same-outcome add-on positions unless pyramiding is explicitly added later

Risk failures must not be silent. Persist skipped reasons and expose aggregate skipped counts in the deployment UI.

## Native Qt UI

Do not introduce a web UI. Use the existing Qt desktop app.

`Algo Trading` changes:

- Add `Polymarket` as a `Market Type`.
- Add an `Auto Scan` strategy mode for Polymarket.
- Add Polymarket scan settings:
  - scan interval
  - max candidates
  - sort by volume/liquidity
  - min volume
  - min liquidity
  - max spread
  - min top-of-book depth
  - price range
  - excluded categories/tags
  - min time to expiry
- Add edge settings:
  - minimum edge
  - confidence threshold
  - momentum weight
  - volatility penalty
  - imbalance weight
  - liquidity/spread penalty
- Add risk settings:
  - max order USDC
  - max total exposure
  - daily loss limit
  - max positions
  - cooldown minutes
  - stop loss / take profit / trailing stop

`Algo Trading > Deployments` should show:

- bot state: scanning, subscribed, trading, paused, stopped, error
- scanned markets count
- candidate count
- active paper positions
- realized/unrealized PnL
- skipped trade count
- top skipped reasons
- recent paper fills
- latest signals with market, outcome, price, estimated probability, edge, action, and reason

`Prediction Markets` detail additions:

- whether the selected market is in the bot candidate pool
- latest bot signal for each relevant outcome
- latest heuristic probability and edge
- current paper position
- recent paper trades
- data freshness timestamps
- source labels such as `Source: Polymarket Gamma/CLOB/Data API`

The UI should be understandable for non-technical users. It should show plain status, risk state, and paper PnL without requiring users to understand quantitative strategy internals.

## Persistence

Prefer small additive schema changes. Reuse existing tables where the shape already fits, but avoid overloading generic fields when Polymarket-specific data is needed for debugging and testability.

Required persisted concepts:

- deployment status and metrics
- paper positions
- paper trades/fills
- latest signals
- candidate market snapshots
- skipped trade reasons
- source/freshness metadata

Keep a clear `mode = "paper"` field now so future live trading cannot be confused with paper records.

## Error Handling

- API error: skip the affected scan/update and persist context.
- Stale data: skip trading on that market.
- Empty/invalid order book: skip.
- Excessive spread/depth failure: skip.
- Indicator failure: skip, do not use default computed values.
- DB failure: mark deployment `error`.
- Closed/inactive market: stop new entries and close/mark existing paper positions.
- Runner crash: deployment dashboard must show error state.

## Automated Verification

The feature must be designed so AI agents can verify functionality without a non-technical user manually inspecting behavior.

Python unit tests:

- scanner filtering, sorting, and skipped reasons
- heuristic probability and edge calculation
- risk controls
- top-of-book paper fills
- PnL calculation
- stale data rejection
- invalid/missing data rejection

Fixture tests:

- Use fixed Gamma/CLOB/Data API JSON samples.
- Fixtures must include `source_api` and `fetched_at`.
- Tests must reject unlabeled or AI-created market data.
- Tests must not require live network access.

Runner smoke test:

- Create a temporary SQLite DB.
- Insert a Polymarket paper strategy.
- Run one bounded paper-bot cycle.
- Assert signals, skipped reasons, paper fills, positions, and metrics are written correctly.

C++/Qt service smoke tests:

- Strategy save/load preserves `market_type = "polymarket"` and bot config.
- Deployment startup passes the expected arguments/config to the Python runner.
- Existing non-Polymarket strategy paths are unaffected.

Not an acceptance criterion:

- Profitability.
- Any claim that the strategy is financially optimal.
- Any AI-generated assessment that live trading is safe.

## Upstream Compatibility

This repository is a fork at `https://github.com/sgme94/FinceptTerminal`, forked from `Fincept-Corporation/FinceptTerminal`.

Recommended repo setup:

```bash
git remote add upstream https://github.com/Fincept-Corporation/FinceptTerminal.git
git fetch upstream
```

Design constraints for easier upstream merges:

- Keep most new logic in new Python files under `fincept-qt/scripts/algo_trading/`.
- Keep C++ changes narrow and additive.
- Reuse existing Qt screens instead of redesigning navigation or the app shell.
- Avoid global style/theme changes.
- Avoid changing build system unless required for tests.
- Preserve existing equity/crypto algo trading behavior.
- Add tests so future upstream merge conflicts can be resolved with automated confidence.

## Out of Scope

- Live Polymarket trading.
- Private key handling for the bot.
- CLOB API credential derivation for bot execution.
- Live order placement or cancellation.
- Settlement/final-resolution accounting beyond `closed_unsettled` marking.
- New web frontend.
- Kalshi support in this bot version.
- Strategy profitability guarantees.

## Future Work

- Upgrade fill model to multi-level order-book depth simulation.
- Add particle-filter/Bayesian edge engine from `polymarket_quant_bot.py`.
- Add settlement-aware paper accounting for resolved markets.
- Add strategy templates for common prediction-market patterns.
- Design live trading separately with explicit approval, private-key safety, kill switch, order cancellation, and audit logging.
- Generalize the bot to the unified `PredictionExchangeAdapter` layer after Polymarket paper mode is stable.
