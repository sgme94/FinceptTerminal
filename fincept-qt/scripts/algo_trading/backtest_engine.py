"""
Backtest Engine — Walk-forward strategy backtester

Fetches historical data via yfinance or from local candle_cache (Fyers),
walks through candles bar-by-bar, evaluates entry/exit conditions at each bar,
and computes performance metrics.

Usage:
    python backtest_engine.py \
        --symbol RELIANCE \
        --entry-conditions '[{"indicator":"RSI","params":{"period":14},"field":"value","operator":"crosses_below","value":30}]' \
        --exit-conditions '[{"indicator":"RSI","params":{"period":14},"field":"value","operator":"crosses_above","value":70}]' \
        --timeframe 1d \
        --period 1y \
        --stop-loss 3 \
        --take-profit 5 \
        --initial-capital 100000 \
        --provider fyers \
        --db /path/to/db

Output:
    JSON with trades, equity curve, and performance metrics
"""

import json
import sys
import argparse
import math
import os
import sqlite3
import traceback
from typing import Optional

# Debug log collector
DEBUG_LOG = []

def debug(msg):
    """Add a debug message to the log."""
    DEBUG_LOG.append(f"[py:backtest] {msg}")

debug("Script starting...")
debug(f"Python version: {sys.version}")
debug(f"Working directory: {os.getcwd()}")
debug(f"Script location: {os.path.abspath(__file__)}")

try:
    import pandas as pd
    debug(f"pandas version: {pd.__version__}")
except ImportError as e:
    debug(f"ERROR: pandas not installed: {e}")
    print(json.dumps({
        'success': False,
        'error': f'pandas not installed: {e}',
        'debug': DEBUG_LOG
    }))
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
debug(f"Added to sys.path: {os.path.dirname(os.path.abspath(__file__))}")

try:
    from condition_evaluator import evaluate_condition_group
    debug("condition_evaluator imported successfully")
except ImportError as e:
    debug(f"ERROR: Failed to import condition_evaluator: {e}")
    print(json.dumps({
        'success': False,
        'error': f'Failed to import condition_evaluator: {e}',
        'debug': DEBUG_LOG
    }))
    sys.exit(1)

# Minimum candles needed before we start evaluating (for indicator warmup)
WARMUP_BARS = 50
POLYMARKET_CLOB_API = "https://clob.polymarket.com"


def fetch_from_yfinance(symbol: str, period: str, interval: str):
    """Fetch OHLCV data via yfinance."""
    debug(f"fetch_from_yfinance: symbol={symbol}, period={period}, interval={interval}")
    try:
        import yfinance as yf
        debug(f"yfinance version: {yf.__version__}")
        ticker = yf.Ticker(symbol)
        debug(f"Created ticker object for {symbol}")
        df = ticker.history(period=period, interval=interval)
        debug(f"history() returned DataFrame with shape: {df.shape if df is not None else 'None'}")
        if df.empty:
            debug("DataFrame is empty")
            return None, "No data returned from yfinance"
        # Normalize column names
        df.columns = [c.lower() for c in df.columns]
        debug(f"Columns after lowercasing: {list(df.columns)}")
        # Ensure we have needed columns
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col not in df.columns:
                debug(f"Missing column: {col}")
                return None, f"Missing column: {col}"
        df = df[['open', 'high', 'low', 'close', 'volume']].reset_index(drop=True)
        debug(f"Final DataFrame shape: {df.shape}, first row: {df.iloc[0].to_dict() if len(df) > 0 else 'empty'}")
        return df, None
    except ImportError as e:
        debug(f"yfinance ImportError: {e}")
        return None, "yfinance not installed. Install with: pip install yfinance"
    except Exception as e:
        debug(f"yfinance Exception: {e}\n{traceback.format_exc()}")
        return None, f"yfinance error: {e}"


def fetch_from_candle_cache(db_path: str, symbol: str, timeframe: str, limit: int = 500):
    """Fetch OHLCV data from local candle_cache (populated by Fyers/broker)."""
    debug(f"fetch_from_candle_cache: db_path={db_path}, symbol={symbol}, timeframe={timeframe}, limit={limit}")
    try:
        if not os.path.exists(db_path):
            debug(f"Database file does not exist: {db_path}")
            return None, f"Database not found: {db_path}"

        debug(f"Database file exists, size: {os.path.getsize(db_path)} bytes")
        conn = sqlite3.connect(db_path)

        # First check if table exists
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='candle_cache'")
        tables = cursor.fetchall()
        debug(f"candle_cache table exists: {len(tables) > 0}")

        if len(tables) == 0:
            conn.close()
            return None, "candle_cache table does not exist in database"

        # Check what data exists for this symbol
        cursor = conn.execute(
            "SELECT COUNT(*), MIN(open_time), MAX(open_time) FROM candle_cache WHERE symbol = ? AND timeframe = ?",
            (symbol, timeframe)
        )
        row = cursor.fetchone()
        debug(f"Data for {symbol}/{timeframe}: count={row[0]}, min_time={row[1]}, max_time={row[2]}")

        # Also try without timeframe filter to see what's available
        cursor = conn.execute(
            "SELECT DISTINCT symbol, timeframe, COUNT(*) as cnt FROM candle_cache GROUP BY symbol, timeframe LIMIT 20"
        )
        available = cursor.fetchall()
        debug(f"Available data in candle_cache: {available[:10]}")  # Show first 10

        query = """
            SELECT open_time, o, h, l, c, volume
            FROM candle_cache
            WHERE symbol = ? AND timeframe = ? AND is_closed = 1
            ORDER BY open_time ASC
            LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=(symbol, timeframe, limit))
        conn.close()

        debug(f"Query returned {len(df)} rows")

        if df.empty:
            return None, f"No data in candle_cache for {symbol} ({timeframe}). Run a scan first to fetch data."

        df.rename(columns={'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close'}, inplace=True)
        df = df[['open', 'high', 'low', 'close', 'volume']].reset_index(drop=True)
        debug(f"Final DataFrame shape: {df.shape}, first row: {df.iloc[0].to_dict() if len(df) > 0 else 'empty'}")
        return df, None
    except Exception as e:
        debug(f"Database error: {e}\n{traceback.format_exc()}")
        return None, f"Database error: {e}"


def fetch_polymarket_history(token_id: str, interval: str = '1d', fidelity: int = 5,
                             start_date: Optional[str] = None, end_date: Optional[str] = None):
    """Fetch Polymarket price history and normalize to OHLCV shape."""
    debug(f"fetch_polymarket_history: token_id={token_id}, interval={interval}, fidelity={fidelity}, start={start_date}, end={end_date}")
    try:
        import requests

        response = requests.get(
            f"{POLYMARKET_CLOB_API}/prices-history",
            params={"market": token_id, "interval": interval, "fidelity": fidelity},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        history = payload.get('history', [])
        if not history:
            return None, f"No price history for token {token_id}"

        start_ts = None
        end_ts = None
        if start_date:
            start_ts = int(pd.Timestamp(f"{start_date} 00:00:00", tz='UTC').timestamp())
        if end_date:
            end_ts = int(pd.Timestamp(f"{end_date} 23:59:59", tz='UTC').timestamp())

        rows = []
        prev_price = None
        for point in history:
            ts = int(point.get('t', 0) or 0)
            if start_ts is not None and ts < start_ts:
                continue
            if end_ts is not None and ts > end_ts:
                continue

            price = float(point.get('p', 0) or 0)
            if price <= 0:
                continue
            open_price = prev_price if prev_price is not None else price
            rows.append({
                'open': open_price,
                'high': max(open_price, price),
                'low': min(open_price, price),
                'close': price,
                'volume': 0.0,
            })
            prev_price = price

        if not rows:
            return None, f"No usable price points for token {token_id} in selected range"

        df = pd.DataFrame(rows)
        debug(f"fetch_polymarket_history success: {len(df)} rows")
        return df[['open', 'high', 'low', 'close', 'volume']].reset_index(drop=True), None
    except Exception as e:
        debug(f"fetch_polymarket_history error: {e}\n{traceback.format_exc()}")
        return None, f"Polymarket history error: {e}"


def fetch_historical_data(symbol: str, period: str, interval: str, provider: str = 'yfinance', db_path: str = None,
                          start_date: Optional[str] = None, end_date: Optional[str] = None):
    """Fetch OHLCV data from the specified provider."""
    debug(f"fetch_historical_data: symbol={symbol}, period={period}, interval={interval}, provider={provider}, db_path={db_path}")

    if provider == 'polymarket':
        interval_map = {
            'live': ('1h', 1),
            '1m': ('1h', 1),
            '3m': ('1h', 1),
            '5m': ('1h', 1),
            '10m': ('1h', 1),
            '15m': ('1h', 1),
            '30m': ('1h', 1),
            '1h': ('1h', 1),
            '4h': ('6h', 1),
            '1d': ('1d', 5),
            '1w': ('1w', 30),
            '1mth': ('1m', 60),
        }
        poly_interval, fidelity = interval_map.get(interval, ('1d', 5))
        return fetch_polymarket_history(
            symbol,
            poly_interval,
            fidelity,
            start_date=start_date,
            end_date=end_date,
        )
    if provider == 'fyers' or provider == 'candle_cache':
        if not db_path:
            # Try default path
            db_path = os.path.join(os.environ.get('APPDATA', ''), 'fincept-terminal', 'fincept_terminal.db')
            debug(f"Using default db_path: {db_path}")

        # Map period to limit
        period_to_limit = {
            '1mo': 30, '3mo': 90, '6mo': 180,
            '1y': 365, '2y': 730, '5y': 1825,
        }
        limit = period_to_limit.get(period, 365)
        debug(f"Period {period} -> limit {limit}")

        df, error = fetch_from_candle_cache(db_path, symbol, interval, limit)
        if error:
            debug(f"fetch_from_candle_cache error: {error}")
            return None, error
        debug(f"fetch_from_candle_cache success: {len(df)} rows")
        return df, None
    else:
        # Default to yfinance
        debug("Using yfinance provider")
        return fetch_from_yfinance(symbol, period, interval)


def run_backtest(
    df,
    entry_conditions: list,
    exit_conditions: list,
    stop_loss_pct: float = 0,
    take_profit_pct: float = 0,
    initial_capital: float = 100000,
    timeframe: str = '1d',
):
    """
    Walk forward through candle data and generate trades.
    Uses proper position sizing based on available capital.

    Returns dict with trades, equity curve, and metrics.
    """
    trades = []
    equity_curve = []
    in_position = False
    entry_price = 0.0
    entry_bar = 0
    position_shares = 0
    capital = initial_capital
    peak_capital = initial_capital
    max_drawdown = 0.0

    for i in range(WARMUP_BARS, len(df)):
        # Use candles up to and including bar i
        window = df.iloc[:i + 1].copy()
        current_price = window['close'].iloc[-1]
        current_bar = i

        if not in_position:
            # Check entry conditions
            result = evaluate_condition_group(entry_conditions, window)
            if result['result']:
                in_position = True
                entry_price = current_price
                entry_bar = current_bar
                # Position sizing: invest all available capital
                position_shares = math.floor(capital / entry_price) if entry_price > 0 else 0
                if position_shares <= 0:
                    in_position = False  # Can't afford even 1 share
                    continue
                capital -= position_shares * entry_price
        else:
            # Check risk management first
            pnl_pct = ((current_price - entry_price) / entry_price) * 100

            # Stop loss
            if stop_loss_pct > 0 and pnl_pct <= -stop_loss_pct:
                exit_price = current_price
                pnl = (exit_price - entry_price) * position_shares
                capital += position_shares * exit_price
                trades.append({
                    'entry_bar': entry_bar,
                    'exit_bar': current_bar,
                    'entry_price': round(entry_price, 2),
                    'exit_price': round(exit_price, 2),
                    'shares': position_shares,
                    'pnl': round(pnl, 2),
                    'pnl_pct': round(pnl_pct, 2),
                    'reason': 'stop_loss',
                    'bars_held': current_bar - entry_bar,
                })
                in_position = False
                position_shares = 0
                continue

            # Take profit
            if take_profit_pct > 0 and pnl_pct >= take_profit_pct:
                exit_price = current_price
                pnl = (exit_price - entry_price) * position_shares
                capital += position_shares * exit_price
                trades.append({
                    'entry_bar': entry_bar,
                    'exit_bar': current_bar,
                    'entry_price': round(entry_price, 2),
                    'exit_price': round(exit_price, 2),
                    'shares': position_shares,
                    'pnl': round(pnl, 2),
                    'pnl_pct': round(pnl_pct, 2),
                    'reason': 'take_profit',
                    'bars_held': current_bar - entry_bar,
                })
                in_position = False
                position_shares = 0
                continue

            # Check exit conditions
            result = evaluate_condition_group(exit_conditions, window)
            if result['result']:
                exit_price = current_price
                pnl = (exit_price - entry_price) * position_shares
                capital += position_shares * exit_price
                trades.append({
                    'entry_bar': entry_bar,
                    'exit_bar': current_bar,
                    'entry_price': round(entry_price, 2),
                    'exit_price': round(exit_price, 2),
                    'shares': position_shares,
                    'pnl': round(pnl, 2),
                    'pnl_pct': round(pnl_pct, 2),
                    'reason': 'exit_signal',
                    'bars_held': current_bar - entry_bar,
                })
                in_position = False
                position_shares = 0

        # Track equity curve
        unrealized = (current_price - entry_price) * position_shares if in_position else 0
        current_equity = capital + (position_shares * current_price if in_position else 0)
        equity_curve.append(round(current_equity, 2))

        if current_equity > peak_capital:
            peak_capital = current_equity
        dd = ((peak_capital - current_equity) / peak_capital) * 100 if peak_capital > 0 else 0
        if dd > max_drawdown:
            max_drawdown = dd

    # Close any open position at last bar
    if in_position and len(df) > 0:
        exit_price = df['close'].iloc[-1]
        pnl = (exit_price - entry_price) * position_shares
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        capital += position_shares * exit_price
        trades.append({
            'entry_bar': entry_bar,
            'exit_bar': len(df) - 1,
            'entry_price': round(entry_price, 2),
            'exit_price': round(exit_price, 2),
            'shares': position_shares,
            'pnl': round(pnl, 2),
            'pnl_pct': round(pnl_pct, 2),
            'reason': 'end_of_data',
            'bars_held': len(df) - 1 - entry_bar,
        })

    # Compute metrics
    total_trades = len(trades)
    if total_trades == 0:
        return {
            'trades': [],
            'equity_curve': equity_curve,
            'metrics': {
                'total_trades': 0,
                'win_rate': 0,
                'total_return': 0,
                'total_return_pct': 0,
                'max_drawdown': round(max_drawdown, 2),
                'avg_pnl': 0,
                'avg_bars_held': 0,
                'profit_factor': 0,
                'sharpe': 0,
            },
        }

    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    win_rate = (len(wins) / total_trades) * 100

    total_return = capital - initial_capital
    total_return_pct = (total_return / initial_capital) * 100

    avg_pnl = sum(t['pnl'] for t in trades) / total_trades
    avg_bars_held = sum(t['bars_held'] for t in trades) / total_trades

    gross_profit = sum(t['pnl'] for t in wins) if wins else 0
    gross_loss = abs(sum(t['pnl'] for t in losses)) if losses else 0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf') if gross_profit > 0 else 0

    # Annualization factor based on timeframe (bars per year)
    BARS_PER_YEAR = {
        '1m': 252 * 390, '3m': 252 * 130, '5m': 252 * 78, '10m': 252 * 39,
        '15m': 252 * 26, '30m': 252 * 13, '1h': int(252 * 6.5), '4h': int(252 * 1.625),
        '1d': 252, '1D': 252, 'D': 252, '1w': 52, '1W': 52, '1M': 12,
    }
    ann_factor = BARS_PER_YEAR.get(timeframe, 252)

    # Sharpe ratio (annualized using timeframe-aware factor)
    if len(equity_curve) > 1:
        returns = []
        for i in range(1, len(equity_curve)):
            if equity_curve[i - 1] != 0:
                returns.append((equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1])
        if returns:
            mean_ret = sum(returns) / len(returns)
            std_ret = (sum((r - mean_ret) ** 2 for r in returns) / len(returns)) ** 0.5
            sharpe = (mean_ret / std_ret) * (ann_factor ** 0.5) if std_ret > 0 else 0
        else:
            sharpe = 0
    else:
        sharpe = 0

    # Cap profit_factor for JSON serialization
    if math.isinf(profit_factor):
        profit_factor = 999.99

    # Downsample equity curve if too large (keep full shape visible)
    if len(equity_curve) > 500:
        step = len(equity_curve) // 500
        equity_curve_out = equity_curve[::step]
        # Ensure the last point is always included
        if equity_curve_out[-1] != equity_curve[-1]:
            equity_curve_out.append(equity_curve[-1])
    else:
        equity_curve_out = equity_curve

    return {
        'trades': trades,
        'equity_curve': equity_curve_out,
        'metrics': {
            'total_trades': total_trades,
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': round(win_rate, 1),
            'total_return': round(total_return, 2),
            'total_return_pct': round(total_return_pct, 2),
            'max_drawdown': round(max_drawdown, 2),
            'avg_pnl': round(avg_pnl, 2),
            'avg_bars_held': round(avg_bars_held, 1),
            'profit_factor': round(profit_factor, 2),
            'sharpe': round(sharpe, 2),
        },
    }


def get_db_path(arg_db: str) -> str:
    """Resolve DB path from arg or fallback to AppData location."""
    if arg_db and os.path.exists(arg_db):
        return arg_db
    appdata = os.environ.get('APPDATA', '')
    if appdata:
        candidate = os.path.join(appdata, 'Fincept', 'FinceptTerminal', 'fincept.db')
        if os.path.exists(candidate):
            return candidate
    return arg_db or ''


def open_db(db_path: str):
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def ensure_algo_strategies_schema(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS algo_strategies (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            market_type TEXT DEFAULT 'equity',
            market_id TEXT DEFAULT '',
            symbol TEXT DEFAULT '',
            timeframe TEXT DEFAULT '1d',
            entry_conditions TEXT DEFAULT '[]',
            exit_conditions TEXT DEFAULT '[]',
            entry_logic TEXT DEFAULT 'AND',
            exit_logic TEXT DEFAULT 'AND',
            stop_loss REAL DEFAULT 0,
            take_profit REAL DEFAULT 0,
            trailing_stop REAL DEFAULT 0,
            trailing_stop_type TEXT DEFAULT 'percent',
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    existing_columns = {
        row['name'] for row in conn.execute("PRAGMA table_info(algo_strategies)").fetchall()
    }
    for column, definition in (
        ('market_type', "TEXT DEFAULT 'equity'"),
        ('market_id', "TEXT DEFAULT ''"),
        ('symbol', "TEXT DEFAULT ''"),
    ):
        if column not in existing_columns:
            conn.execute(f"ALTER TABLE algo_strategies ADD COLUMN {column} {definition}")


def cmd_save_strategy(params: dict, db_path: str):
    """Insert or replace a strategy in algo_strategies table."""
    try:
        conn = open_db(db_path)
        ensure_algo_strategies_schema(conn)
        conn.execute("""
            INSERT INTO algo_strategies
                (id, name, description, market_type, market_id, symbol, timeframe,
                 entry_conditions, exit_conditions, entry_logic, exit_logic,
                 stop_loss, take_profit, trailing_stop, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                description = excluded.description,
                market_type = excluded.market_type,
                market_id = excluded.market_id,
                symbol = excluded.symbol,
                timeframe = excluded.timeframe,
                entry_conditions = excluded.entry_conditions,
                exit_conditions = excluded.exit_conditions,
                entry_logic = excluded.entry_logic,
                exit_logic = excluded.exit_logic,
                stop_loss = excluded.stop_loss,
                take_profit = excluded.take_profit,
                trailing_stop = excluded.trailing_stop,
                updated_at = CURRENT_TIMESTAMP
        """, (
            params['id'],
            params.get('name', ''),
            params.get('description', ''),
            params.get('market_type', 'equity') or 'equity',
            params.get('market_id', ''),
            params.get('symbol', ''),
            params.get('timeframe', '1d'),
            json.dumps(params.get('entry_conditions', [])),
            json.dumps(params.get('exit_conditions', [])),
            params.get('entry_logic', 'AND'),
            params.get('exit_logic', 'AND'),
            params.get('stop_loss', 0),
            params.get('take_profit', 0),
            params.get('trailing_stop', 0),
        ))
        conn.commit()
        conn.close()
        print(json.dumps({'success': True, 'id': params['id']}))
    except Exception as e:
        print(json.dumps({'success': False, 'error': str(e)}))


def cmd_list_strategies(db_path: str):
    """Return all strategies from DB."""
    try:
        conn = open_db(db_path)
        ensure_algo_strategies_schema(conn)
        rows = conn.execute("""
            SELECT id, name, description, market_type, market_id, symbol, timeframe,
                   entry_conditions, exit_conditions, entry_logic, exit_logic,
                   stop_loss, take_profit, trailing_stop,
                   is_active, created_at, updated_at
            FROM algo_strategies
            WHERE is_active = 1
            ORDER BY created_at DESC
        """).fetchall()
        conn.close()
        strategies = []
        for r in rows:
            s = dict(r)
            # Parse JSON arrays stored as text
            try:
                s['entry_conditions'] = json.loads(s['entry_conditions'] or '[]')
            except Exception:
                s['entry_conditions'] = []
            try:
                s['exit_conditions'] = json.loads(s['exit_conditions'] or '[]')
            except Exception:
                s['exit_conditions'] = []
            strategies.append(s)
        print(json.dumps({'success': True, 'strategies': strategies}))
    except sqlite3.OperationalError as e:
        if 'no such table' in str(e).lower():
            print(json.dumps({'success': True, 'strategies': []}))
        else:
            print(json.dumps({'success': False, 'error': str(e), 'strategies': []}))
    except Exception as e:
        print(json.dumps({'success': False, 'error': str(e), 'strategies': []}))


def cmd_list_registry():
    """Return all strategies from the strategies/_registry.py index."""
    try:
        import importlib.util
        registry_path = os.path.join(os.path.dirname(__file__), '..', 'strategies', '_registry.py')
        registry_path = os.path.normpath(registry_path)
        spec = importlib.util.spec_from_file_location('_registry', registry_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        reg = mod.STRATEGY_REGISTRY  # dict: id -> {name, category, path}
        strategies = []
        for fct_id, meta in reg.items():
            strategies.append({
                'id':               fct_id,
                'name':             meta.get('name', fct_id),
                'description':      meta.get('category', ''),
                'timeframe':        '1d',
                'entry_conditions': [],
                'exit_conditions':  [],
                'entry_logic':      'AND',
                'exit_logic':       'AND',
                'stop_loss':        0,
                'take_profit':      0,
                'trailing_stop':    0,
                'is_active':        1,
                'created_at':       '',
                'updated_at':       '',
                'script_path':      meta.get('path', ''),
            })
        print(json.dumps({'success': True, 'strategies': strategies}))
    except Exception as e:
        print(json.dumps({'success': False, 'error': str(e), 'strategies': []}))


def cmd_delete_strategy(strategy_id: str, db_path: str):
    """Soft-delete a strategy (set is_active=0)."""
    try:
        conn = open_db(db_path)
        conn.execute(
            "UPDATE algo_strategies SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (strategy_id,)
        )
        conn.commit()
        conn.close()
        print(json.dumps({'success': True, 'id': strategy_id}))
    except Exception as e:
        print(json.dumps({'success': False, 'error': str(e)}))


def _flatten_conditions(conditions: list, logic: str) -> list:
    items = conditions or []
    if any(isinstance(item, str) for item in items):
        return items

    condition_items = [c for c in items if isinstance(c, dict)]
    if not condition_items:
        return []

    flat = [condition_items[0]]
    for cond in condition_items[1:]:
        flat.append(logic)
        flat.append(cond)
    return flat


def cmd_run_backtest(params: dict, db_path: str):
    """Run walk-forward backtest for a saved or unsaved strategy payload."""
    debug("cmd_run_backtest started")
    strategy_id = params.get('strategy_id', '')
    start_date = params.get('start_date', '2024-01-01')
    end_date = params.get('end_date', '2025-01-01')
    initial_capital = float(params.get('initial_capital', 100000))

    entry_conditions = params.get('entry_conditions', []) or []
    exit_conditions = params.get('exit_conditions', []) or []
    entry_logic = params.get('entry_logic', 'AND') or 'AND'
    exit_logic = params.get('exit_logic', 'AND') or 'AND'
    stop_loss_pct = float(params.get('stop_loss', 0) or 0)
    take_profit_pct = float(params.get('take_profit', 0) or 0)
    timeframe = params.get('timeframe', '1d') or '1d'
    market_type = params.get('market_type', 'equity') or 'equity'
    market_id = params.get('market_id', '') or ''
    symbol = params.get('symbol', '') or ''

    if db_path and os.path.exists(db_path) and strategy_id:
        try:
            conn = open_db(db_path)
            ensure_algo_strategies_schema(conn)
            row = conn.execute(
                "SELECT market_type, market_id, symbol, timeframe, entry_conditions, exit_conditions, "
                "entry_logic, exit_logic, stop_loss, take_profit FROM algo_strategies WHERE id = ?",
                (strategy_id,)
            ).fetchone()
            conn.close()
            if row:
                if not params.get('entry_conditions'):
                    entry_conditions = json.loads(row['entry_conditions'] or '[]')
                if not params.get('exit_conditions'):
                    exit_conditions = json.loads(row['exit_conditions'] or '[]')
                if 'entry_logic' not in params:
                    entry_logic = row['entry_logic'] or 'AND'
                if 'exit_logic' not in params:
                    exit_logic = row['exit_logic'] or 'AND'
                if 'stop_loss' not in params:
                    stop_loss_pct = row['stop_loss'] or 0.0
                if 'take_profit' not in params:
                    take_profit_pct = row['take_profit'] or 0.0
                if not params.get('timeframe'):
                    timeframe = row['timeframe'] or '1d'
                if not params.get('market_type'):
                    market_type = row['market_type'] or 'equity'
                if not params.get('market_id'):
                    market_id = row['market_id'] or ''
                if not params.get('symbol'):
                    symbol = row['symbol'] or ''
                debug(f"Strategy loaded from DB: {len(entry_conditions)} entry, {len(exit_conditions)} exit conditions")
            else:
                debug(f"Strategy {strategy_id} not found in DB, using request payload")
        except Exception as e:
            debug(f"Failed to load strategy from DB: {e}")

    data_symbol = symbol if market_type == 'polymarket' else symbol
    provider = 'polymarket' if market_type == 'polymarket' else 'yfinance'

    if market_type == 'polymarket' and not symbol:
        print(json.dumps({
            'success': False,
            'error': 'Missing Polymarket token ID for backtest.',
            'debug': DEBUG_LOG,
        }))
        return

    if not data_symbol:
        print(json.dumps({
            'success': False,
            'error': 'Missing symbol for backtest.',
            'debug': DEBUG_LOG,
        }))
        return

    entry_conditions = _flatten_conditions(entry_conditions, entry_logic)
    exit_conditions = _flatten_conditions(exit_conditions, exit_logic)

    try:
        from datetime import datetime as dt
        d1 = dt.strptime(start_date, '%Y-%m-%d')
        d2 = dt.strptime(end_date, '%Y-%m-%d')
        days = (d2 - d1).days
        if days <= 90:
            period = '3mo'
        elif days <= 180:
            period = '6mo'
        elif days <= 370:
            period = '1y'
        elif days <= 740:
            period = '2y'
        else:
            period = '5y'
    except Exception:
        period = '1y'

    debug(f"Fetching data: symbol={data_symbol}, period={period}, timeframe={timeframe}, provider={provider}")
    try:
        df, error = fetch_historical_data(
            data_symbol,
            period,
            timeframe,
            provider=provider,
            db_path=db_path,
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as e:
        debug(f"Exception fetching data: {e}\n{traceback.format_exc()}")
        print(json.dumps({'success': False, 'error': f'Exception fetching data: {e}', 'debug': DEBUG_LOG}))
        return

    if error or df is None or (hasattr(df, 'empty') and df.empty):
        response = {
            'success': False,
            'error': error or f'No historical data for {data_symbol}',
            'debug': DEBUG_LOG,
        }
        if provider == 'yfinance':
            response['hint'] = 'Use .NS suffix for NSE stocks (e.g. RELIANCE.NS) for yfinance.'
        print(json.dumps(response))
        return

    if len(df) < WARMUP_BARS + 10:
        print(json.dumps({
            'success': False,
            'error': f'Insufficient data ({len(df)} bars, need >= {WARMUP_BARS + 10})',
            'debug': DEBUG_LOG,
        }))
        return

    try:
        result = run_backtest(
            df=df,
            entry_conditions=entry_conditions,
            exit_conditions=exit_conditions,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
            initial_capital=initial_capital,
            timeframe=timeframe,
        )
    except Exception as e:
        debug(f"Exception in run_backtest: {e}\n{traceback.format_exc()}")
        print(json.dumps({'success': False, 'error': f'Backtest error: {e}', 'debug': DEBUG_LOG}))
        return

    metrics = result.get('metrics', {})
    final_value = initial_capital + metrics.get('total_return', 0)
    print(json.dumps({
        'success': True,
        'symbol': symbol,
        'market_id': market_id,
        'market_type': market_type,
        'timeframe': timeframe,
        'total_bars': len(df),
        'total_return': metrics.get('total_return_pct', 0),
        'total_return_abs': metrics.get('total_return', 0),
        'final_value': round(final_value, 2),
        'sharpe_ratio': metrics.get('sharpe', 0),
        'max_drawdown': metrics.get('max_drawdown', 0),
        'total_trades': metrics.get('total_trades', 0),
        'win_rate': metrics.get('win_rate', 0),
        'profit_factor': metrics.get('profit_factor', 0),
        'debug': DEBUG_LOG,
        **result,
    }))


def main():
    debug("main() started")
    debug(f"sys.argv: {sys.argv}")

    parser = argparse.ArgumentParser(description='Backtest Engine')
    parser.add_argument('command', choices=['save_strategy', 'list_strategies', 'list_registry', 'delete_strategy', 'run_backtest'],
                        help='Subcommand to execute')
    parser.add_argument('payload', nargs='?', default=None,
                        help='JSON payload or ID depending on command')
    parser.add_argument('--db', default=None, help='SQLite database path')

    try:
        args = parser.parse_args()
        debug(f"command={args.command}, payload_len={len(args.payload or '')}, db={args.db}")
    except Exception as e:
        debug(f"Argument parsing error: {e}")
        print(json.dumps({'success': False, 'error': f'Argument parsing error: {e}', 'debug': DEBUG_LOG}))
        sys.exit(1)

    db_path = get_db_path(args.db)
    debug(f"Resolved db_path={db_path}")

    if args.command == 'save_strategy':
        try:
            params = json.loads(args.payload or '{}')
        except json.JSONDecodeError as e:
            print(json.dumps({'success': False, 'error': f'Invalid JSON: {e}', 'debug': DEBUG_LOG}))
            sys.exit(1)
        cmd_save_strategy(params, db_path)

    elif args.command == 'list_strategies':
        cmd_list_strategies(db_path)

    elif args.command == 'list_registry':
        cmd_list_registry()

    elif args.command == 'delete_strategy':
        if not args.payload:
            print(json.dumps({'success': False, 'error': 'strategy_id required', 'debug': DEBUG_LOG}))
            sys.exit(1)
        cmd_delete_strategy(args.payload, db_path)

    elif args.command == 'run_backtest':
        try:
            params = json.loads(args.payload or '{}')
        except json.JSONDecodeError as e:
            print(json.dumps({'success': False, 'error': f'Invalid JSON: {e}', 'debug': DEBUG_LOG}))
            sys.exit(1)
        cmd_run_backtest(params, db_path)


if __name__ == '__main__':
    main()
