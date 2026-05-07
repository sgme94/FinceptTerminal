# Polymarket Web Terminal

Run these commands from the repository root unless noted otherwise.

## Install

```powershell
npm ci --prefix web/polymarket-terminal
```

The Python API uses the existing repository modules. Make sure the environment already has the project test/runtime dependencies installed, including `pytest`, `fastapi`, and `uvicorn`.

## Port Check

The web terminal does not use default service ports. Check the required ports before starting the API, frontend, or e2e tests:

```powershell
Get-NetTCPConnection -LocalPort 4177,8765 -ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort,State,OwningProcess
```

If this command returns any listener for `4177` or `8765`, stop and resolve the conflict before starting services.

## Start API on Port 8765

```powershell
$env:PYTHONPATH = "fincept-qt/scripts;fincept-qt/scripts/algo_trading"
$env:POLYMARKET_WEB_DB = ".polymarket-web.sqlite"
python -m uvicorn polymarket_web_api.app:create_app --factory --host 127.0.0.1 --port 8765
```

## Start Frontend on Port 4177

In a second shell:

```powershell
$env:VITE_POLYMARKET_API_BASE = "http://127.0.0.1:8765"
npm run dev --prefix web/polymarket-terminal -- --host 127.0.0.1 --port 4177
```

Open `http://127.0.0.1:4177`.

## Test

```powershell
python -m pytest fincept-qt/scripts/algo_trading/tests fincept-qt/scripts/polymarket_web_api/tests -q --basetemp .pytest_tmp
npm test --prefix web/polymarket-terminal
npm run build --prefix web/polymarket-terminal
Get-NetTCPConnection -LocalPort 4177,8765 -ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort,State,OwningProcess
npm run test:e2e --prefix web/polymarket-terminal
```

The e2e command starts its own API and frontend web servers on `8765` and `4177`, so the port check must be empty before running it.

## Paper-Only Safety

This MVP is paper-only. Do not add or configure live trading, private keys, API secrets, or real CLOB order placement paths for this terminal. Manual approval is only a paper workflow: approving a proposal records the approval state/audit trail and may produce paper fills, but it must not submit a real order.
