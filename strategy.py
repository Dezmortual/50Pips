"""
50 Pips A Day Forex Strategy (Laurentiu Damir) — adapted for spot crypto.

Original rules (from the PDF):
  1. TREND: use the 200 EMA. Price above a rising 200EMA = uptrend,
     price below a falling 200EMA = downtrend. No other indicators.
  2. LEVEL: find a support/resistance level (diagonal trendline or
     horizontal zone) that goes AGAINST the current trend.
  3. RETEST: wait for price to come back and touch/retest that level.
  4. CONFIRMATION: enter only after a big-body candle, bigger than the
     preceding few candles, closing near its high (buy) or low (sell),
     confirming the trend is resuming.
  5. RISK: stop loss just beyond where the retest ended; take profit
     needs reward >= risk (book targets 1:2 to 1:3); trail stop manually
     above/below new swing points as the trade moves in your favor.

Adaptation notes (spot crypto, no manual chart drawing possible):
  - "Pips" -> we just use price distance directly (works for any pair).
  - Diagonal trendlines drawn by eye -> approximated with detected swing
    highs/lows (fractals). This is the biggest simplification vs. the book.
  - The book trades both directions. Spot has no shorting, so this bot is
    LONG-ONLY: it buys retests of support in an uptrend, and simply exits
    (does not short) when the trend flips down. Add futures/margin later
    if you want the short side too.
  - Risk-reward defaults to 1:3 like the book's example (RISK_REWARD in config).
"""

# ---------------------------------------------------------------------------
# Basic indicators
# ---------------------------------------------------------------------------

def ema(values, period):
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    e = sum(values[:period]) / period
    for v in values[period:]:
        e = v * k + e * (1 - k)
    return e


def ema_series(values, period):
    """Full EMA series (None for the warm-up window) — needed to read the slope."""
    if len(values) < period:
        return [None] * len(values)
    out = [None] * (period - 1)
    k = 2 / (period + 1)
    e = sum(values[:period]) / period
    out.append(e)
    for v in values[period:]:
        e = v * k + e * (1 - k)
        out.append(e)
    return out


# ---------------------------------------------------------------------------
# Trend (rule #1 — 200 EMA slope + price position)
# ---------------------------------------------------------------------------

def get_trend(candles, ema_period=200, slope_lookback=10):
    closes = [c["close"] for c in candles]
    series = ema_series(closes, ema_period)
    if series[-1] is None or series[-1 - slope_lookback] is None:
        return None  # not enough data yet
    current_ema = series[-1]
    past_ema = series[-1 - slope_lookback]
    price = closes[-1]
    if price > current_ema and current_ema > past_ema:
        return "up"
    if price < current_ema and current_ema < past_ema:
        return "down"
    return None  # no clear trend — book says stay out


# ---------------------------------------------------------------------------
# Swing points (approximates the book's hand-drawn support/resistance)
# ---------------------------------------------------------------------------

def find_swing_lows(candles, left=3, right=3):
    """Fractal swing lows: a low that's the lowest point within [left, right] bars."""
    lows = [c["low"] for c in candles]
    swings = []
    for i in range(left, len(candles) - right):
        window = lows[i - left:i + right + 1]
        if lows[i] == min(window):
            swings.append({"index": i, "price": lows[i]})
    return swings


def find_swing_highs(candles, left=3, right=3):
    highs = [c["high"] for c in candles]
    swings = []
    for i in range(left, len(candles) - right):
        window = highs[i - left:i + right + 1]
        if highs[i] == max(window):
            swings.append({"index": i, "price": highs[i]})
    return swings


# ---------------------------------------------------------------------------
# Retest + confirmation candle (rules #3 and #4)
# ---------------------------------------------------------------------------

def body(c):
    return abs(c["close"] - c["open"])


def is_bullish_confirmation(candles, body_mult=1.3, wick_max_pct=0.25):
    """Last CLOSED candle: big green body, closing near its high."""
    last = candles[-1]
    prev = candles[-4:-1]
    if last["close"] <= last["open"]:
        return False
    rng = last["high"] - last["low"]
    if rng <= 0:
        return False
    upper_wick = last["high"] - last["close"]
    if upper_wick / rng > wick_max_pct:
        return False
    if not prev:
        return False
    avg_prev_body = sum(body(c) for c in prev) / len(prev)
    if avg_prev_body <= 0:
        return False
    return body(last) >= body_mult * avg_prev_body


def is_bearish_confirmation(candles, body_mult=1.3, wick_max_pct=0.25):
    last = candles[-1]
    prev = candles[-4:-1]
    if last["close"] >= last["open"]:
        return False
    rng = last["high"] - last["low"]
    if rng <= 0:
        return False
    lower_wick = last["close"] - last["low"]
    if lower_wick / rng > wick_max_pct:
        return False
    if not prev:
        return False
    avg_prev_body = sum(body(c) for c in prev) / len(prev)
    if avg_prev_body <= 0:
        return False
    return body(last) >= body_mult * avg_prev_body


def nearest_support_being_retested(candles, cfg):
    """Most recent swing low that current price is now touching/near (uptrend case)."""
    swings = find_swing_lows(candles[:-1], left=3, right=3)  # exclude the live candle
    if not swings:
        return None
    price = candles[-1]["close"]
    tolerance = price * cfg.RETEST_TOLERANCE_PCT
    # look at the most recent few swing lows below current trend, closest one first
    swings = sorted(swings, key=lambda s: s["index"], reverse=True)[:5]
    for s in swings:
        if abs(price - s["price"]) <= tolerance and price >= s["price"] - tolerance:
            return s
    return None


def nearest_resistance_being_retested(candles, cfg):
    swings = find_swing_highs(candles[:-1], left=3, right=3)
    if not swings:
        return None
    price = candles[-1]["close"]
    tolerance = price * cfg.RETEST_TOLERANCE_PCT
    swings = sorted(swings, key=lambda s: s["index"], reverse=True)[:5]
    for s in swings:
        if abs(price - s["price"]) <= tolerance and price <= s["price"] + tolerance:
            return s
    return None


# ---------------------------------------------------------------------------
# Main decision function
# ---------------------------------------------------------------------------

def decide(candles, position, cfg):
    """
    position: None if flat, else {"entry": float, "stop_loss": float, "take_profit": float}
    Returns a dict:
      {"action": "ENTER_LONG", "stop_loss": .., "take_profit": ..}
      {"action": "EXIT", "reason": ".."}
      {"action": "TRAIL_STOP", "stop_loss": ..}
      {"action": "HOLD"}
    """
    if len(candles) < cfg.EMA_PERIOD + cfg.SLOPE_LOOKBACK + 5:
        return {"action": "HOLD", "reason": "warming up"}

    price = candles[-1]["close"]
    trend = get_trend(candles, cfg.EMA_PERIOD, cfg.SLOPE_LOOKBACK)

    # --- Manage an open long position: stop/target checks + manual trailing ---
    if position:
        if price <= position["stop_loss"]:
            return {"action": "EXIT", "reason": "stop_loss_hit"}
        if price >= position["take_profit"]:
            return {"action": "EXIT", "reason": "take_profit_hit"}
        if trend == "down":
            return {"action": "EXIT", "reason": "trend_flipped"}

        # Trail stop manually above new swing lows, like the book instructs
        swings = find_swing_lows(candles[:-1], left=3, right=3)
        if swings:
            latest_swing = swings[-1]["price"]
            if latest_swing > position["stop_loss"]:
                return {"action": "TRAIL_STOP", "stop_loss": latest_swing}
        return {"action": "HOLD"}

    # --- Flat: look for a new long entry (book's uptrend / support-retest setup) ---
    if trend != "up":
        return {"action": "HOLD", "reason": "no clear uptrend"}

    support = nearest_support_being_retested(candles, cfg)
    if not support:
        return {"action": "HOLD", "reason": "no retest in progress"}

    if not is_bullish_confirmation(candles, cfg.CONFIRMATION_BODY_MULT):
        return {"action": "HOLD", "reason": "waiting for confirmation candle"}

    stop_loss = support["price"] * (1 - cfg.STOP_BUFFER_PCT)
    risk = price - stop_loss
    if risk <= 0:
        return {"action": "HOLD", "reason": "invalid stop"}

    take_profit = price + risk * cfg.RISK_REWARD

    return {
        "action": "ENTER_LONG",
        "entry": price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
    }
