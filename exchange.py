"""Binance market-data client.

Uses only PUBLIC endpoints for paper trading (no API key needed).
Has multiple hosts because api.binance.com is geo-blocked in some regions;
data-api.binance.vision serves the same public data without restrictions.

Every attempt is logged so any network problem (DNS, blocks, timeouts) is
visible in the bot log / Render logs instead of hanging silently.
"""
import time
import hmac
import hashlib
import requests

from config import Config

PUBLIC_HOSTS = [
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api1.binance.com",
]


def _log(msg):
    print(f"[exchange] {msg}", flush=True)


def _get(path: str, params: dict = None):
    """Try each host until one works. Logs each attempt."""
    last_err = None
    for host in PUBLIC_HOSTS:
        try:
            _log(f"fetching {host}{path} params={params or {}}")
            session = requests.Session()  # fresh session each attempt — avoids
                                          # stale/hung connection reuse
            r = session.get(host + path, params=params or {},
                            timeout=(5, 15))  # 5s connect, 15s read
            if r.status_code == 200:
                _log(f"OK from {host} ({len(r.content)} bytes)")
                return r.json()
            last_err = f"{host} -> HTTP {r.status_code}"
            _log(last_err)
            if r.status_code == 451:
                _log("HTTP 451 = geo-blocked. Trying next host...")
        except requests.RequestException as e:
            last_err = f"{host} -> {e}"
            _log(last_err)
    raise RuntimeError(f"All Binance hosts failed. Last error: {last_err}")


def get_klines(symbol: str, interval: str, limit: int = 200):
    """Return list of candles: [{open_time, open, high, low, close, volume}, ...]"""
    data = _get("/api/v3/klines", {
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
    })
    return [
        {
            "open_time": k[0],
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
            "close_time": k[6],
        }
        for k in data
    ]


def get_price(symbol: str) -> float:
    data = _get("/api/v3/ticker/price", {"symbol": symbol})
    return float(data["price"])


# ---------------------------------------------------------------------------
# SIGNED requests — only used when LIVE_TRADING=true. Paper mode never touches
# these, so you can run the bot with zero keys.
# ---------------------------------------------------------------------------

def _signed_request(method: str, path: str, params: dict) -> dict:
    if not (Config.BINANCE_API_KEY and Config.BINANCE_API_SECRET):
        raise RuntimeError("LIVE_TRADING=true but API key/secret are not set.")
    params = dict(params)
    params["timestamp"] = int(time.time() * 1000)
    params["recvWindow"] = 5000
    query = "&".join(f"{k}={v}" for k, v in params.items())
    signature = hmac.new(
        Config.BINANCE_API_SECRET.encode(), query.encode(), hashlib.sha256
    ).hexdigest()
    url = "https://api.binance.com" + path + "?" + query + "&signature=" + signature
    r = requests.request(
        method, url, timeout=15, headers={"X-MBX-APIKEY": Config.BINANCE_API_KEY}
    )
    if r.status_code != 200:
        raise RuntimeError(f"Binance error ({r.status_code}): {r.text}")
    return r.json()


def live_market_buy(symbol: str, quote_amount: float) -> dict:
    """Market buy spending `quote_amount` USDT."""
    return _signed_request("POST", "/api/v3/order", {
        "symbol": symbol, "side": "BUY", "type": "MARKET",
        "quoteOrderQty": round(quote_amount, 2),
    })


def live_market_sell(symbol: str, base_amount: float) -> dict:
    """Market sell `base_amount` of the asset."""
    return _signed_request("POST", "/api/v3/order", {
        "symbol": symbol, "side": "SELL", "type": "MARKET",
        "quantity": round(base_amount, 6),
    })
