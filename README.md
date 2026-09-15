# 🤖 50 Pips A Day — Crypto Paper-Trading Bot (Binance)

A Python trading bot that runs 24/7 on [Render](https://render.com), pulls live
Binance market data, and **paper-trades** the **"50 Pips A Day" price-action
strategy** by Laurentiu Damir — adapted from forex to spot crypto. Simulated
money, zero real risk. A dashboard shows equity, the open position, trade
history, and logs.

> ⚠️ **Paper mode by default.** Live trading with real funds is possible but
> off until you explicitly flip it on. Trading crypto is risky — never put in
> money you can't afford to lose.

## The strategy (from the PDF, adapted)

Rules, straight from the book:
1. **Trend** — 200 EMA is the only indicator used. Price above a *rising*
   200EMA = uptrend. Price below a *falling* 200EMA = downtrend. No trend →
   stay out.
2. **Level** — find a support/resistance level opposing the trend (the book
   draws these by hand on the chart; the bot approximates them with detected
   swing highs/lows).
3. **Retest** — wait for price to come back and touch that level.
4. **Confirmation candle** — only enter after a big-body candle (bigger than
   the last few), closing near its high (buy) — this is the "footprint" of
   buyers/sellers stepping back in.
5. **Risk management** — stop loss just beyond where the retest ended; take
   profit sized so reward ≥ risk (book's example uses 1:3); trail the stop
   manually above new swing lows as the trade runs, per the book's rules
   against cutting profits short or letting losses run.

**Adaptations for spot crypto (important):**
- The book uses "pips" (forex) — the bot works directly in price, so it works
  for any Binance pair.
- The book trades both long and short using hand-drawn diagonal/horizontal
  trendlines. Spot crypto can't short without margin/futures, so **this bot
  is long-only**: it buys retests of support in confirmed uptrends, and exits
  (doesn't short) when the trend flips down. Add a futures integration later
  if you want the short side.
- Trendlines drawn "by eye" in the book are approximated with fractal swing
  highs/lows — the single biggest simplification versus the original PDF.
- Position sizing follows the book's money-management rule: risk a fixed %
  of equity per trade (`RISK_PER_TRADE_PCT`, default 2%), sized off the
  stop-loss distance — not a flat amount per trade.

## How it works

```
Binance public API ──▶ every POLL_SECONDS ──▶ strategy.decide() ──▶ PaperBroker
  (4h candles)            (default 300s)     (ENTER_LONG/EXIT/TRAIL/HOLD)
```

- `exchange.py` — fetches candles/prices from Binance public endpoints (no API key needed)
- `strategy.py` — **the 50 Pips A Day logic**: trend, swings, retest, confirmation candle
- `paper.py` — simulated wallet: USDT cash, holdings, open position (entry/SL/TP), fees, P&L
- `bot.py` — the main loop
- `app.py` — Flask dashboard + `/health` endpoint

## Deploy to Render via GitHub

1. **Push to GitHub** — create a new repo, upload these files.
2. In Render: **New → Web Service** → connect your GitHub repo.
   - If the repo contains `render.yaml`, Render auto-fills everything — just
     click **Apply**.
   - Otherwise set: Runtime `Python`, Build `pip install -r requirements.txt`,
     Start `gunicorn app:app`.
3. Your bot is live at `https://<your-service>.onrender.com`.

### Environment variables (optional — all have defaults)

| Variable                  | Default  | Meaning                                  |
|----------------------------|----------|-------------------------------------------|
| `SYMBOL`                  | BTCUSDT  | Market to trade                           |
| `INTERVAL`                 | 4h       | Candle size (book recommends 4h/daily)    |
| `POLL_SECONDS`            | 300      | How often the bot checks the market       |
| `STARTING_CASH`           | 10000    | Paper USDT to start with                  |
| `EMA_PERIOD`              | 200      | Trend filter period                       |
| `RETEST_TOLERANCE_PCT`    | 0.003    | How close price must get to a level ("touch") |
| `CONFIRMATION_BODY_MULT`  | 1.3      | How much bigger the signal candle must be |
| `RISK_REWARD`             | 3.0      | Take-profit distance as a multiple of risk |
| `RISK_PER_TRADE_PCT`      | 0.02     | % of equity risked per trade (book's rule) |
| `LIVE_TRADING`            | false    | ⚠️ Set `true` only when you mean it      |
| `BINANCE_API_KEY` / `BINANCE_API_SECRET` | — | Only needed for live trading |

## Going live (later, at your own risk)

1. Create an API key on Binance with **spot trading enabled and withdrawals DISABLED**.
2. Set `LIVE_TRADING=true` + the key/secret in Render's dashboard.
3. The bot switches to real market orders (you'll want to wire `exchange.live_market_buy/sell`
   into `paper.py`'s flow, or ask me to do that when you're ready).

## Notes

- Render's **free/starter tier restarts services**, which wipes the `data/`
  folder — the bot resets its paper wallet. Attach a Render **Disk** (paid
  plans) to persist state across restarts.
- Free web services spin down after inactivity — a free uptime pinger (e.g.
  cron-job.org) hitting `/health` keeps it awake.
- I ran this strategy against 1000 real recent 4h BTCUSDT candles as a quick
  sanity check (not a rigorous backtest) — it correctly entered/exited on
  stop-loss and take-profit hits. Past behavior on historical data is not a
  promise of future results — test thoroughly in paper mode first.

## Starting & stopping the bot

**From the dashboard (easiest):** open your Render URL and use the
**▶ Start / ⏸ Stop** buttons in the top-right corner. The status pill shows
RUNNING or PAUSED. Stopping pauses trading instantly — the service stays up,
the position dashboard still works, and no new trades are made until you
press Start.

**Control key:** if you set the `CONTROL_TOKEN` environment variable in
Render's dashboard, the Start/Stop buttons ask for that key before they
work (type it into the small "control key" box once per visit). If the
variable is unset, the buttons are open — fine for paper mode on a private
Render service, but set a token before ever going live.

**Via API** (e.g. from your phone or a script):

```bash
curl -X POST https://your-app.onrender.com/control \
  -H 'Content-Type: application/json' \
  -d '{"action":"stop","key":"your-token"}'      # or "start"

curl https://your-app.onrender.com/api/status   # {"running":true,...}
```

**Fully stopping:** deleting or pausing the Web Service in Render's
dashboard stops the bot entirely. Note: an open paper position is kept in
`data/state.json`, so if you stop and restart, the bot remembers it —
on the free tier the disk resets on redeploy/restart, so treat long-running
positions as experiments unless you attach a Render Disk.

## Dashboard features

- Live **equity curve** chart and **price chart with buy/sell markers**
  (Chart.js, updates on every bot cycle)
- Stat cards: equity, cash, **win rate**, average P&L per trade, max drawdown
- Open-position card (entry / stop loss / take profit)
- Full trade history with reasons (stop_loss_hit, take_profit_hit, trend_flip…)
- Live bot log showing every decision, including why it chose to HOLD
