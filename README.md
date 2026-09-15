# 🤖 Crypto Paper-Trading Bot (Binance)

A Python trading bot that runs 24/7 on [Render](https://render.com), pulls live
Binance market data, and **paper-trades** your strategy — simulated money, zero
risk. It exposes a small dashboard so you can watch equity, trades, and logs in
your browser.

> ⚠️ **Paper mode by default.** Live trading with real funds is possible but
> off until you explicitly flip it on. Trading crypto is risky — never put in
> money you can't afford to lose.

## How it works

```
Binance public API ──▶ every POLL_SECONDS ──▶ strategy.decide() ──▶ PaperBroker
     (live prices)         (default 60s)       (BUY/SELL/HOLD)    (simulated orders)
```

- `exchange.py` — fetches candles/prices from Binance public endpoints (no API key needed)
- `strategy.py` — **your strategy lives here** (currently an RSI placeholder)
- `paper.py` — simulated wallet: USDT cash, holdings, fees (0.1%), P&L
- `bot.py` — the main loop
- `app.py` — Flask dashboard + `/health` endpoint

## Deploy to Render via GitHub

1. **Push to GitHub** — create a new repo, upload these files (or `git init` +
   push). Keep everything in the repo root OR adjust paths accordingly.
2. In Render: **New → Web Service** → connect your GitHub repo.
   - If the repo contains `render.yaml`, Render auto-fills everything. Just
     click **Apply**.
   - Otherwise set: Runtime `Python`, Build `pip install -r requirements.txt`,
     Start `gunicorn app:app`.
3. Add `gunicorn` is already in requirements — done. Your bot is live at
   `https://<your-service>.onrender.com`.

### Environment variables (optional — all have defaults)

| Variable        | Default  | Meaning                              |
|-----------------|----------|--------------------------------------|
| `SYMBOL`        | BTCUSDT  | Market to trade                      |
| `INTERVAL`       | 1h       | Candle size                           |
| `POLL_SECONDS`  | 60       | How often the bot checks the market   |
| `STARTING_CASH` | 10000    | Paper USDT to start with              |
| `LIVE_TRADING`  | false    | ⚠️ Set `true` only when you mean it  |
| `BINANCE_API_KEY` / `BINANCE_API_SECRET` | — | Only needed for live trading |

## Going live (later, at your own risk)

1. Create an API key on Binance with **spot trading enabled and withdrawals DISABLED**.
2. Set `LIVE_TRADING=true` + the key/secret in Render's dashboard.
3. The bot switches `buy()`/`sell()` to real market orders.

## Notes

- Render's **free/starter tier restarts services**, which wipes the `data/`
  folder — the bot will reset its paper wallet. Attach a Render **Disk**
  (paid plans) at `/opt/render/project/src/data` to persist state, or treat
  resets as clean experiments.
- Free web services spin down after inactivity — visiting the dashboard or a
  free uptime pinger (e.g. cron-job.org) hitting `/health` keeps it awake.
