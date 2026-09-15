"""Flask web app — professional dashboard with graphs + Start/Stop controls."""
import hmac
from flask import Flask, jsonify, render_template_string, request

import bot
from config import Config

app = Flask(__name__)

PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>50 Pips A Day — Trading Bot</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <style>
    :root {
      --bg:#0b1220; --panel:#121a2b; --border:#1f2b40; --text:#e6edf7;
      --muted:#8b98ad; --green:#34d399; --red:#f87171; --accent:#60a5fa;
    }
    * { box-sizing: border-box; }
    body { font-family: 'Inter', ui-sans-serif, system-ui, sans-serif; background:
           radial-gradient(1200px 600px at 80% -10%, #16233d 0%, var(--bg) 55%);
           color: var(--text); margin: 0; padding: 28px 20px 60px; }
    .wrap { max-width: 1080px; margin: 0 auto; }
    header { display:flex; align-items:center; justify-content:space-between;
             flex-wrap:wrap; gap:14px; margin-bottom:22px; }
    .brand { display:flex; align-items:center; gap:12px; }
    .logo { width:38px; height:38px; border-radius:10px; background:linear-gradient(135deg,#3b82f6,#8b5cf6);
            display:flex; align-items:center; justify-content:center; font-size:19px; }
    h1 { font-size:17px; margin:0; letter-spacing:.2px; }
    .sub { color:var(--muted); font-size:12.5px; margin-top:2px; }
    .controls { display:flex; align-items:center; gap:10px; }
    .pill { display:inline-flex; align-items:center; gap:7px; font-size:12.5px; font-weight:600;
            padding:6px 13px; border-radius:999px; border:1px solid var(--border);
            background:var(--panel); }
    .dot { width:8px; height:8px; border-radius:50%; }
    .dot.on { background:var(--green); box-shadow:0 0 8px var(--green); }
    .dot.off { background:var(--muted); }
    button { border:0; cursor:pointer; font:inherit; font-weight:600; font-size:13px;
             padding:9px 18px; border-radius:9px; transition:filter .15s, transform .05s; }
    button:active { transform:scale(.97); }
    #btn-stop { background:#7f1d1d; color:#fecaca; }
    #btn-start { background:#064e3b; color:#a7f3d0; }
    button:disabled { opacity:.45; cursor:not-allowed; }
    .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(158px,1fr));
             gap:12px; margin-bottom:16px; }
    .card { background:var(--panel); border:1px solid var(--border); border-radius:14px;
            padding:16px 18px; position:relative; overflow:hidden; }
    .card::after { content:''; position:absolute; inset:0 0 auto 0; height:2px;
            background:linear-gradient(90deg,#3b82f6,#8b5cf6); opacity:.55; }
    .label { color:var(--muted); font-size:11px; letter-spacing:.8px; text-transform:uppercase; }
    .value { font-size:21px; font-weight:700; margin-top:6px; }
    .delta { font-size:12px; margin-top:3px; }
    .pos { background:var(--panel); border:1px solid var(--border); border-left:3px solid var(--accent);
           border-radius:12px; padding:14px 18px; margin-bottom:16px; font-size:13.5px;
           display:flex; gap:26px; flex-wrap:wrap; }
    .grid2 { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
    @media (max-width: 860px){ .grid2 { grid-template-columns:1fr; } }
    .chartbox { background:var(--panel); border:1px solid var(--border); border-radius:14px;
                padding:16px 18px; }
    .chartbox h3 { margin:0 0 12px; font-size:13px; color:var(--muted);
                   text-transform:uppercase; letter-spacing:.8px; font-weight:600; }
    .chartwrap { position:relative; height:230px; }
    section h2 { font-size:13px; color:var(--muted); text-transform:uppercase;
                 letter-spacing:.8px; margin:26px 0 10px; }
    table { width:100%; border-collapse:collapse; font-size:13px;
            background:var(--panel); border:1px solid var(--border);
            border-radius:12px; overflow:hidden; }
    th, td { text-align:left; padding:10px 14px; border-bottom:1px solid var(--border); }
    th { color:var(--muted); font-weight:600; font-size:11.5px; text-transform:uppercase;
         letter-spacing:.5px; background:#0e1626; }
    tr:last-child td { border-bottom:0; }
    .buy { color:var(--green); font-weight:700; } .sell { color:var(--red); font-weight:700; }
    pre { background:#0a1120; border:1px solid var(--border); border-radius:12px;
          padding:14px; font-size:12px; overflow-x:auto; white-space:pre-wrap;
          color:#9fb3c8; max-height:300px; }
    #toast { position:fixed; bottom:22px; left:50%; transform:translateX(-50%);
             background:#064e3b; color:#a7f3d0; padding:10px 20px; border-radius:10px;
             font-size:13.5px; font-weight:600; opacity:0; transition:opacity .3s; pointer-events:none; }
    .keyrow { display:flex; gap:8px; align-items:center; }
    input[type=password] { background:var(--panel); border:1px solid var(--border); color:var(--text);
           border-radius:9px; padding:8px 12px; font:inherit; font-size:13px; width:140px; }
  </style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="brand">
      <div class="logo">📈</div>
      <div>
        <h1>50 Pips A Day — Trading Bot</h1>
        <div class="sub">{{ symbol }} · {{ interval }} candles · {{ mode }} mode · strategy: 200EMA retest</div>
      </div>
    </div>
    <div class="controls">
      <span class="pill"><span class="dot {{ 'on' if running else 'off' }}"></span>
        {{ 'RUNNING' if running else 'PAUSED' }}</span>
      <input type="password" id="key" placeholder="control key" {% if not needs_key %}hidden{% endif %}>
      <button id="btn-start" {% if running %}disabled{% endif %}>▶ Start</button>
      <button id="btn-stop" {% if not running %}disabled{% endif %}>⏸ Stop</button>
    </div>
  </header>

  <div class="cards">
    <div class="card"><div class="label">Equity</div>
      <div class="value">{{ equity }} <span style="font-size:12px;color:var(--muted)">USDT</span></div>
      <div class="delta" style="color:{{ '#34d399' if pnl_raw >= 0 else '#f87171' }}">{{ pnl }} all-time</div></div>
    <div class="card"><div class="label">Cash</div>
      <div class="value">{{ cash }} <span style="font-size:12px;color:var(--muted)">USDT</span></div>
      <div class="delta" style="color:var(--muted)">{{ holdings }} {{ base }} held</div></div>
    <div class="card"><div class="label">Win rate</div>
      <div class="value">{{ win_rate }}%</div>
      <div class="delta" style="color:var(--muted)">{{ wins }}W / {{ losses }}L closed trades</div></div>
    <div class="card"><div class="label">Avg P&L / trade</div>
      <div class="value">{{ avg_pnl }}</div>
      <div class="delta" style="color:var(--muted)">max drawdown {{ max_dd }}%</div></div>
    <div class="card"><div class="label">Open position</div>
      {% if position %}
      <div class="value" style="font-size:16px;">LONG @ {{ position.entry }}</div>
      <div class="delta" style="color:var(--muted)">SL {{ position.stop_loss }} · TP {{ position.take_profit }}</div>
      {% else %}
      <div class="value" style="color:var(--muted);font-size:16px;">Flat</div>
      <div class="delta" style="color:var(--muted)">waiting for a setup…</div>
      {% endif %}</div>
  </div>

  <div class="grid2">
    <div class="chartbox">
      <h3>Equity curve</h3>
      <div class="chartwrap"><canvas id="equityChart"></canvas></div>
    </div>
    <div class="chartbox">
      <h3>{{ symbol }} price & trades</h3>
      <div class="chartwrap"><canvas id="priceChart"></canvas></div>
    </div>
  </div>

  <section><h2>Trade history</h2>
    <table>
      <tr><th>Time (UTC)</th><th>Side</th><th>Price</th><th>Amount (USDT)</th><th>Reason</th><th>Realized P&L</th></tr>
      {% for t in trades %}
      <tr>
        <td>{{ t.time[:19] }}</td>
        <td class="{{ t.side.lower() }}">{{ t.side }}</td>
        <td>{{ "%.2f"|format(t.price) }}</td>
        <td>{{ "%.2f"|format(t.quote_amount) }}</td>
        <td style="color:var(--muted)">{{ t.reason if t.reason is defined else "—" }}</td>
        <td style="color:{{ '#34d399' if (t.realized_pnl is defined and t.realized_pnl >= 0) else '#f87171' }}">
          {{ t.realized_pnl if t.realized_pnl is defined else "—" }}</td>
      </tr>
      {% else %}
      <tr><td colspan="6" style="color:var(--muted)">No trades yet — the bot logs every decision it makes.</td></tr>
      {% endfor %}
    </table>
  </section>

  <section><h2>Bot log</h2>
    <pre>{{ log_text }}</pre>
  </section>
</div>
<div id="toast"></div>
<script>
const CHART_DEFAULTS = {
  color: '#8b98ad',
  borderColor: '#1f2b40',
  grid: { color: '#16213a' },
  ticks: { color: '#8b98ad', font: { size: 10 } },
  point: { radius: 0 }
};

// ---- Equity curve ----
new Chart(document.getElementById('equityChart'), {
  type: 'line',
  data: {
    labels: {{ eq_labels|tojson }},
    datasets: [{
      label: 'Equity (USDT)',
      data: {{ eq_values|tojson }},
      borderColor: '#60a5fa',
      backgroundColor: 'rgba(96,165,250,.08)',
      fill: true,
      borderWidth: 2,
      tension: .25
    }]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    interaction: { intersect: false, mode: 'index' },
    plugins: { legend: { display: false } },
    scales: { x: CHART_DEFAULTS, y: { ...CHART_DEFAULTS,
      ticks: { ...CHART_DEFAULTS.ticks, callback: v => v.toLocaleString() } } }
  }
});

// ---- Price + trade markers ----
new Chart(document.getElementById('priceChart'), {
  type: 'line',
  data: {
    labels: {{ pr_labels|tojson }},
    datasets: [
      {
        label: '{{ symbol }}',
        data: {{ pr_values|tojson }},
        borderColor: '#a78bfa',
        borderWidth: 2,
        fill: false,
        tension: .25,
        pointRadius: 0
      },
      {
        label: 'Buy',
        data: {{ buy_points|tojson }},
        type: 'scatter',
        pointStyle: 'triangle',
        radius: 9,
        backgroundColor: '#34d399'
      },
      {
        label: 'Sell',
        data: {{ sell_points|tojson }},
        type: 'scatter',
        pointStyle: 'rectRot',
        radius: 8,
        backgroundColor: '#f87171'
      }
    ]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    interaction: { intersect: false, mode: 'nearest' },
    plugins: { legend: { labels: { color: '#8b98ad', boxWidth: 10 } } },
    scales: { x: CHART_DEFAULTS, y: { ...CHART_DEFAULTS,
      ticks: { ...CHART_DEFAULTS.ticks, callback: v => v.toLocaleString() } } }
  }
});

// ---- Start / Stop ----
const keyInput = document.getElementById('key');
function toast(msg, ok = true) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.style.background = ok ? '#064e3b' : '#7f1d1d';
  t.style.color = ok ? '#a7f3d0' : '#fecaca';
  t.style.opacity = 1;
  setTimeout(() => t.style.opacity = 0, 2500);
}
async function control(action) {
  const key = keyInput ? keyInput.value : '';
  const r = await fetch('/control', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ action: action, key: key })
  });
  const data = await r.json();
  if (r.ok) { toast(data.message); setTimeout(() => location.reload(), 800); }
  else toast(data.error || 'failed', false);
}
document.getElementById('btn-start').onclick = () => control('start');
document.getElementById('btn-stop').onclick = () => control('stop');
</script>
</body>
</html>
"""


def _authorized(key):
    if not Config.CONTROL_TOKEN:
        return True  # no token configured — open control (fine for paper mode)
    return hmac.compare_digest(str(key or ""), Config.CONTROL_TOKEN)


def _stats(st, price):
    closed = [t for t in st["trades"] if t.get("realized_pnl") is not None]
    wins = [t for t in closed if t["realized_pnl"] >= 0]
    losses = [t for t in closed if t["realized_pnl"] < 0]
    win_rate = round(100 * len(wins) / len(closed)) if closed else 0
    avg_pnl = (round(sum(t["realized_pnl"] for t in closed) / len(closed), 2)
               if closed else 0.0)
    # max drawdown from the equity curve
    curve = st["equity_curve"]
    max_dd = 0.0
    if curve:
        peak = curve[0]["equity"]
        for pt in curve:
            peak = max(peak, pt["equity"])
            if peak > 0:
                max_dd = max(max_dd, (peak - pt["equity"]) / peak * 100)
    return closed, wins, losses, win_rate, avg_pnl, round(max_dd, 1)


@app.get("/")
def dashboard():
    st = bot.broker.state
    price = st["equity_curve"][-1]["price"] if st["equity_curve"] else 0
    equity = bot.broker.equity(price)
    pnl = round(equity - Config.STARTING_CASH, 2)
    closed, wins, losses, win_rate, avg_pnl, max_dd = _stats(st, price)

    curve = st["equity_curve"][-120:]
    eq_labels = [p["time"][11:16] if p["time"][:10] == (curve[-1]["time"][:10] if curve else "")
                 else p["time"][:10] for p in curve]
    eq_values = [p["equity"] for p in curve]
    pr_labels = eq_labels
    pr_values = [p["price"] for p in curve]

    import bisect
    buy_points, sell_points = [], []
    times = [p["time"] for p in curve]
    for t in st["trades"]:
        i = bisect.bisect_left(times, t["time"])
        if i >= len(times):
            i = len(times) - 1
        pt = {"x": eq_labels[i], "y": t["price"]}
        (buy_points if t["side"] == "BUY" else sell_points).append(pt)

    running = bot.is_running()
    return render_template_string(
        PAGE,
        symbol=Config.SYMBOL,
        interval=Config.INTERVAL,
        mode="LIVE ⚠️" if Config.LIVE_TRADING else "PAPER",
        running=running,
        needs_key=bool(Config.CONTROL_TOKEN),
        equity=f"{equity:,.2f}",
        cash=f"{st['cash']:,.2f}",
        holdings=f"{st['holdings']:.6f}",
        base=Config.SYMBOL.replace("USDT", ""),
        pnl=f"{pnl:+,.2f}",
        pnl_raw=pnl,
        win_rate=win_rate,
        wins=len(wins), losses=len(losses),
        avg_pnl=f"{avg_pnl:+,.2f}",
        max_dd=f"{max_dd:.1f}",
        position=st.get("position"),
        trades=list(reversed(st["trades"][-15:])),
        log_text="\n".join(bot.get_recent_log()[:40]),
        eq_labels=eq_labels,
        eq_values=eq_values,
        pr_labels=pr_labels,
        pr_values=pr_values,
        buy_points=buy_points,
        sell_points=sell_points,
    )


@app.post("/control")
def control():
    body = request.get_json(force=True, silent=True) or {}
    action = body.get("action")
    if not _authorized(body.get("key")):
        return jsonify({"error": "invalid control key"}), 403
    if action == "start":
        bot.start_bot()
        return jsonify({"ok": True, "message": "Bot started", "running": True})
    if action == "stop":
        bot.stop_bot()
        return jsonify({"ok": True, "message": "Bot stopped", "running": False})
    return jsonify({"error": "unknown action"}), 400


@app.get("/api/status")
def api_status():
    st = bot.broker.state
    price = st["equity_curve"][-1]["price"] if st["equity_curve"] else 0
    return jsonify({
        "running": bot.is_running(),
        "symbol": Config.SYMBOL,
        "equity": round(bot.broker.equity(price), 2),
        "in_position": bool(st.get("position")),
    })


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    bot.start_background()
    app.run(host="0.0.0.0", port=Config.PORT)
