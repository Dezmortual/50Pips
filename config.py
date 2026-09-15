"""Environment-driven configuration."""
import os


class Config:
    # --- Trading ---
    SYMBOL = os.environ.get("SYMBOL", "BTCUSDT")          # market to trade
    INTERVAL = os.environ.get("INTERVAL", "4h")           # book recommends 4h/daily
    POLL_SECONDS = int(os.environ.get("POLL_SECONDS", "300"))  # loop delay
    STARTING_CASH = float(os.environ.get("STARTING_CASH", "10000"))  # paper USDT

    # --- 50 Pips A Day strategy params ---
    EMA_PERIOD = int(os.environ.get("EMA_PERIOD", "200"))          # trend filter
    SLOPE_LOOKBACK = int(os.environ.get("SLOPE_LOOKBACK", "10"))   # bars back to confirm EMA slope
    RETEST_TOLERANCE_PCT = float(os.environ.get("RETEST_TOLERANCE_PCT", "0.003"))  # 0.3% "touch" zone
    CONFIRMATION_BODY_MULT = float(os.environ.get("CONFIRMATION_BODY_MULT", "1.3"))  # signal candle size
    STOP_BUFFER_PCT = float(os.environ.get("STOP_BUFFER_PCT", "0.002"))  # stop just beyond the swing
    RISK_REWARD = float(os.environ.get("RISK_REWARD", "3.0"))       # book's 1:3 example
    RISK_PER_TRADE_PCT = float(os.environ.get("RISK_PER_TRADE_PCT", "0.02"))  # book's 2% rule

    # --- Live trading (off by default — paper only until you flip this) ---
    LIVE_TRADING = os.environ.get("LIVE_TRADING", "false").lower() == "true"
    BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY", "")
    BINANCE_API_SECRET = os.environ.get("BINANCE_API_SECRET", "")

    # --- Web server ---
    PORT = int(os.environ.get("PORT", "10000"))

    # --- Files ---
    STATE_FILE = os.environ.get("STATE_FILE", "data/state.json")
