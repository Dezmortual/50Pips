"""Flask web app — serves a small dashboard so Render (and you) can watch the bot."""
from flask import Flask, render_template_string

import bot
from config import Config

app = Flask(__name__)

PAGE = """
<!doctype html>
<html>
<head>
  <title>50 Pips A Day — Trading Bot</title>
  <style>
    body { font-family: ui-sans-serif, system-ui, sans-serif; background:#0f172a; color:#e2e8f0;
           max-width: 900px; margin: 0 auto; padding: 32px 20px; }
    h1 { font-size: 20px; } h2 { font-size: 15px; margin-top: 28px; color:#94a3b8; }
    .cards { display:flex; gap:12px; flex-wrap:wrap; margin-top:12px; }
    .card { background:#1e293b; border:1px solid #334155; border-radius:10px;
            padding:14px 18px; min-width:140px; }
    .card .label { color:#94a3b8; font-size:12px; }
    .card .value { font-size:20px; font-weight:600; margin-top:4px; }
    table { width:100%; border-collapse:collapse; margin-top:12px; font-size:13px; }
    th, td { text-align:left; padding:7px 10px; border-bottom:1px solid #334155; }
    th { color:#94a3b8; font-weight:500; }
    .buy { color:#4ade80; } .sell { color:#f87171; }
    pre { background:#1e293b; border:1px solid #334155; border-radius:10px;
          padding:14px; font-size:12px; overflow-x:auto; white-space:pre-wrap; }
    .pos { background:#1e293b; border:1px solid #334155; border-radius:10px; padding:14px 18px; margin-top:12px; }
  </style>
</head>
<body>
  <h1>🤖 50 Pips A Day Strategy — {{ symbol }} {{ interval }}</h1>
  <p style="color:#94a3b8;font-size:13px">Mode: {{ mode }} · Starting cash: {{ start_cash }} USDT ·
     200 EMA trend filter + support/resistance retest + confirmation candle (long-only)</p>

  <div class="cards">
    <div class="card"><div class="label">EQUITY</div><div class="value">{{ equity }} USDT</div></div>
    <div class="card"><div class="label">CASH</div><div class="value">{{ cash }} USDT</div></div>
    <div class="card"><div class="label">HOLDINGS</div><div class="value">{{ holdings }} {{ base }}</div></div>
    <div class="card"><div class="label">TRADES</div><div class="value">{{ n_trades }}</div></div>
    <div class="card"><div class="label">TOTAL P&L</div><div class="value">{{ pnl }} USDT</div></div>
  </div>

  {% if position %}
  <div class="pos">
    <div class="label" style="color:#94a3b8;font-size:12px">OPEN POSITION</div>
    Entry: {{ position.entry }} · Stop loss: {{ position.stop_loss }} · Take profit: {{ position.take_profit }}
  </div>
  {% endif %}

  <h2>Recent trades</h2>
  <table>
    <tr><th>Time (UTC)</th><th>Side</th><th>Price</th><th>Amount (USDT)</th><th>Reason</th><th>Realized P&L</th></tr>
    {% for t in trades %}
    <tr>
      <td>{{ t.time[:19] }}</td>
      <td class="{{ t.side.lower() }}">{{ t.side }}</td>
      <td>{{ "%.4f"|format(t.price) }}</td>
      <td>{{ "%.2f"|format(t.quote_amount) }}</td>
      <td>{{ t.reason if t.reason is defined else "—" }}</td>
      <td>{{ t.realized_pnl if t.realized_pnl is defined else "—" }}</td>
    </tr>
    {% else %}
    <tr><td colspan="6" style="color:#94a3b8">No trades yet.</td></tr>
    {% endfor %}
  </table>

  <h2>Bot log</h2>
  <pre>{{ log_text }}</pre>
</body>
</html>
"""


@app.get("/")
def dashboard():
    st = bot.broker.state
    price = st["equity_curve"][-1]["price"] if st["equity_curve"] else 0
    equity = bot.broker.equity(price)
    pnl = round(equity - Config.STARTING_CASH, 2)
    return render_template_string(
        PAGE,
        symbol=Config.SYMBOL,
        interval=Config.INTERVAL,
        mode="LIVE ⚠️" if Config.LIVE_TRADING else "PAPER",
        start_cash=f"{Config.STARTING_CASH:,.0f}",
        equity=f"{equity:,.2f}",
        cash=f"{st['cash']:,.2f}",
        holdings=f"{st['holdings']:.6f}",
        base=Config.SYMBOL.replace("USDT", ""),
        n_trades=len(st["trades"]),
        pnl=f"{pnl:+,.2f}",
        position=st.get("position"),
        trades=list(reversed(st["trades"][-15:])),
        log_text="\n".join(bot.get_recent_log()[:30]),
    )


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    bot.start_background()
    app.run(host="0.0.0.0", port=Config.PORT)
