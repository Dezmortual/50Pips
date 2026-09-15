"""Main trading loop. Runs in a background thread alongside the Flask app.

The loop can be paused/resumed from the dashboard (Start/Stop buttons)
without restarting the service — see `stop_bot()` / `start_bot()`.
"""
import time
import traceback
import threading
from datetime import datetime, timezone

import exchange
import strategy
from config import Config
from paper import PaperBroker

broker = PaperBroker(Config.STATE_FILE, Config.SYMBOL, Config.STARTING_CASH)

_log_lines = []   # recent log lines for the dashboard
_lock = threading.Lock()
_running = threading.Event()   # controls whether the bot actively trades


def log(msg: str):
    line = f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}"
    with _lock:
        _log_lines.append(line)
        del _log_lines[:-100]
    print(line, flush=True)


def get_recent_log():
    with _lock:
        return list(reversed(_log_lines))


def is_running() -> bool:
    return _running.is_set()


def start_bot():
    if not _running.is_set():
        _running.set()
        log("▶ Bot RESUMED from dashboard")


def stop_bot():
    if _running.is_set():
        _running.clear()
        log("⏸ Bot PAUSED from dashboard — no new trades until resumed")


def run_cycle():
    """One iteration: fetch data -> run the 50-Pips-A-Day strategy -> act."""
    # need enough history for a 200 EMA + slope lookback + swing detection
    candles = exchange.get_klines(Config.SYMBOL, Config.INTERVAL, limit=1000)
    price = candles[-1]["close"]

    decision = strategy.decide(candles, broker.position, Config)
    action = decision["action"]

    if action == "ENTER_LONG":
        result = broker.enter_long(
            price, decision["stop_loss"], decision["take_profit"],
            Config.RISK_PER_TRADE_PCT,
        )
        log(f"{Config.SYMBOL} @ {price:.4f} -> ENTER_LONG "
            f"(SL {decision['stop_loss']:.4f}, TP {decision['take_profit']:.4f}) "
            f"-> {result.get('status')}")

    elif action == "EXIT":
        result = broker.exit_position(price, decision["reason"])
        log(f"{Config.SYMBOL} @ {price:.4f} -> EXIT ({decision['reason']}) "
            f"-> {result.get('status')} P&L {result.get('realized_pnl', '—')}")

    elif action == "TRAIL_STOP":
        broker.trail_stop(decision["stop_loss"])
        log(f"{Config.SYMBOL} @ {price:.4f} -> trailing stop to {decision['stop_loss']:.4f}")

    else:
        reason = decision.get("reason", "")
        pos = broker.position
        pos_txt = (f"in position (entry {pos['entry']:.4f}, SL {pos['stop_loss']:.4f}, "
                   f"TP {pos['take_profit']:.4f})") if pos else "flat"
        log(f"{Config.SYMBOL} @ {price:.4f} -> HOLD [{reason}] ({pos_txt}), "
            f"equity {broker.equity(price):.2f}")

    broker.snapshot_equity(price)
    broker.save()


def loop_forever():
    log(f"Bot starting — 50 Pips A Day strategy on {Config.SYMBOL} {Config.INTERVAL} candles, "
        f"poll every {Config.POLL_SECONDS}s, LIVE_TRADING={Config.LIVE_TRADING}")
    _running.set()  # starts running by default
    while True:
        try:
            if _running.is_set():
                run_cycle()
            else:
                log("... paused ...")
        except Exception:
            log("ERROR: " + traceback.format_exc().strip().replace("\n", " | "))
        time.sleep(Config.POLL_SECONDS)


def start_background():
    t = threading.Thread(target=loop_forever, daemon=True)
    t.start()
    return t
