"""Paper-trading engine.

Simulates a spot account: USDT cash balance + base asset (e.g. BTC) balance,
plus an optional open "position" dict (entry/stop_loss/take_profit) so the
strategy can manage stops/targets and trail them across cycles.
"""
import os
import json
from datetime import datetime, timezone


class PaperBroker:
    def __init__(self, state_file: str, symbol: str, starting_cash: float):
        self.state_file = state_file
        self.symbol = symbol
        self.base_asset = symbol.replace("USDT", "")
        os.makedirs(os.path.dirname(state_file) or ".", exist_ok=True)
        self.state = self._load() or self._fresh(starting_cash)

    # --- persistence -------------------------------------------------------
    def _fresh(self, cash):
        return {
            "cash": cash,
            "holdings": 0.0,          # amount of base asset held
            "position": None,         # {"entry", "stop_loss", "take_profit"} or None
            "trades": [],             # order history
            "equity_curve": [],       # snapshot history for the dashboard
        }

    def _load(self):
        try:
            with open(self.state_file) as f:
                data = json.load(f)
                data.setdefault("position", None)
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def save(self):
        tmp = self.state_file + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.state, f, indent=2)
        os.replace(tmp, self.state_file)

    # --- account -----------------------------------------------------------
    @property
    def cash(self):
        return self.state["cash"]

    @property
    def holdings(self):
        return self.state["holdings"]

    @property
    def position(self):
        return self.state["position"]

    def equity(self, price: float) -> float:
        return self.state["cash"] + self.state["holdings"] * price

    # --- orders --------------------------------------------------------------
    def enter_long(self, price: float, stop_loss: float, take_profit: float,
                    risk_pct: float, fee: float = 0.001) -> dict:
        """Size the position so a stop-loss hit loses exactly risk_pct of equity."""
        equity = self.equity(price)
        risk_amount = equity * risk_pct
        risk_per_unit = price - stop_loss
        if risk_per_unit <= 0:
            return {"status": "rejected", "reason": "invalid stop"}

        base_amount = risk_amount / risk_per_unit
        quote_amount = min(base_amount * price, self.state["cash"])  # spot: no leverage
        if quote_amount <= 1:
            return {"status": "rejected", "reason": "position size too small"}

        fee_cost = quote_amount * fee
        base_bought = (quote_amount - fee_cost) / price
        self.state["cash"] -= quote_amount
        self.state["holdings"] += base_bought
        self.state["position"] = {
            "entry": price, "stop_loss": stop_loss, "take_profit": take_profit,
            "base_amount": base_bought,
        }
        order = {
            "time": datetime.now(timezone.utc).isoformat(),
            "side": "BUY", "symbol": self.symbol, "price": price,
            "quote_amount": quote_amount, "base_amount": base_bought,
            "fee": fee_cost, "stop_loss": stop_loss, "take_profit": take_profit,
        }
        self.state["trades"].append(order)
        self.state["trades"] = self.state["trades"][-200:]
        return {"status": "filled", **order}

    def exit_position(self, price: float, reason: str, fee: float = 0.001) -> dict:
        pos = self.state["position"]
        if not pos:
            return {"status": "rejected", "reason": "no open position"}
        base_amount = min(self.state["holdings"], pos["base_amount"])
        gross = base_amount * price
        fee_cost = gross * fee
        proceeds = gross - fee_cost
        realized = (price - pos["entry"]) * base_amount - fee_cost
        self.state["cash"] += proceeds
        self.state["holdings"] -= base_amount
        if self.state["holdings"] < 1e-10:
            self.state["holdings"] = 0.0
        self.state["position"] = None
        order = {
            "time": datetime.now(timezone.utc).isoformat(),
            "side": "SELL", "symbol": self.symbol, "price": price,
            "quote_amount": proceeds, "base_amount": base_amount,
            "fee": fee_cost, "realized_pnl": round(realized, 2), "reason": reason,
        }
        self.state["trades"].append(order)
        self.state["trades"] = self.state["trades"][-200:]
        return {"status": "filled", **order}

    def trail_stop(self, new_stop_loss: float):
        if self.state["position"]:
            self.state["position"]["stop_loss"] = new_stop_loss

    def snapshot_equity(self, price: float):
        snap = {
            "time": datetime.now(timezone.utc).isoformat(),
            "price": price,
            "equity": round(self.equity(price), 2),
        }
        curve = self.state["equity_curve"]
        curve.append(snap)
        self.state["equity_curve"] = curve[-500:]
