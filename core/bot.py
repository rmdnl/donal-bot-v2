"""Main trading loop - orchestrates regime, strategies, risk, execution, sync."""
import time, logging
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN

from risk.kill_switch import check_flash_crash, is_in_cooldown, new_cooldown
from strategies.regime_detector import detect_regime, Regime
from strategies.donal_strategy import DonalStrategy
from strategies.mean_reversion_strategy import MeanReversionStrategy

logger = logging.getLogger("bot")

def round_step(value, step):
    return float(Decimal(str(value)).quantize(Decimal(str(step)), rounding=ROUND_DOWN))

def round_price(price, filters):
    tick = filters.get("TICK_SIZE") or filters.get("PRICE_FILTER") or {}
    if not tick: return price
    return round_step(price, float(tick.get("tickSize", 0.01)))

class Bot:
    def __init__(self, client, states, risk, breaker, breakeven, notifier, cfg, dry_run=False, trade_history=None, anomaly=None):
        self.client, self.states, self.risk = client, states, risk
        self.breaker, self.breakeven, self.notifier = breaker, breakeven, notifier
        self.cfg, self.dry_run = cfg, dry_run
        self.running = True
        self.is_paused = False
        self.donal = DonalStrategy(cfg["strategy"]["donal"])
        self.mr = MeanReversionStrategy(cfg["strategy"]["mean_reversion"])
        self.ks = cfg["kill_switch"]
        self.trade_history = trade_history
        self.anomaly = anomaly
        if notifier:
            notifier.register("/status", self.cmd_status)
            notifier.register("/positions", self.cmd_positions)
            notifier.register("/pause", self.cmd_pause)
            notifier.register("/resume", self.cmd_resume)
            notifier.register("/close", self.cmd_close)

    # ---------------- MAIN LOOP ----------------
    def run(self):
        logger.info("bot_loop_started")
        if self.notifier:
            self.notifier.send(f"Bot started | {'DRY RUN' if self.dry_run else 'LIVE'}")
        interval = self.cfg["trading"]["poll_interval_seconds"]
        while self.running:
            try:
                all_states = self.states.load_all_states(self.cfg["trading"]["symbols"])
                equity = self.client.get_total_portfolio_value_usdt(self.cfg["trading"]["symbols"], all_states)
                if self.risk._peak is None:
                    self.risk.initialize(equity)
                for sym in self.cfg["trading"]["symbols"]:
                    self.evaluate_symbol(sym, all_states, equity)
                if self.anomaly and not self.dry_run:
                    self.anomaly.periodic_check(all_states, equity)
            except Exception as e:
                logger.error(f"loop_error: {e}")
            time.sleep(interval)

    def stop(self):
        self.running = False

    # ---------------- EVALUASI PER SYMBOL ----------------
    def evaluate_symbol(self, symbol, all_states, equity):
        if self.is_paused: return
        st = all_states[symbol]
        df1 = self.client.get_closed_klines(symbol, "1h", 200)
        df4 = self.client.get_closed_klines(symbol, "4h", 100)
        if len(df1) < 80 or len(df4) < 70: return

        if not self.dry_run:
            st = self.sync_position(symbol, st)
            all_states[symbol] = st

        price = float(df1.iloc[-1]["close"])

        # Breakeven stop
        if st.in_position and not st.breakeven_triggered:
            new_sl = self.breakeven.check(st, price)
            if new_sl is not None:
                filters = self.client.get_symbol_filters(symbol)
                rsl = round_price(new_sl, filters)
                self.states.update_breakeven(symbol, rsl)
                st.sl_price, st.breakeven_triggered = rsl, True
                if not self.dry_run:
                    self._replace_oco(symbol, st)
                if self.notifier:
                    self.notifier.send(f"BREAKEVEN {symbol}: SL moved to {rsl:.4f}")

        # Kill switch (candle 1m)
        df1m = self.client.get_recent_klines(symbol, "1m",
            self.ks["lookback_minutes"] + self.ks["volume_baseline_minutes"] + 5)
        crash = check_flash_crash(df1m, self.ks["lookback_minutes"], self.ks["crash_threshold_15m"],
                                  self.ks["volume_baseline_minutes"], self.ks["volume_spike_multiplier"])
        if crash.triggered:
            if st.in_position and not is_in_cooldown(st):
                self.execute_exit(symbol, st, price, "KILL_SWITCH", crash.reason)
                st.kill_switch_cooldown_until = new_cooldown(self.ks["cooldown_hours"])
                self.states.save_state(st)
            return

        # Regime routing
        reg = detect_regime(df4) if self.cfg["strategy"]["multi_regime_enabled"] else None
        if reg and reg.mode == Regime.BEAR:
            if st.in_position:
                self.execute_exit(symbol, st, price, "BEAR", reg.reason)
                self.states.save_state(st)
            return

        if reg and reg.mode == Regime.SIDEWAYS:
            sig = self.mr.compute(df1)
            c = self.cfg["strategy"]["mean_reversion"]
            strat = "MEAN_REVERSION"
        else:
            sig = self.donal.compute(df1, df4)
            c = self.cfg["strategy"]["donal"]
            strat = "DONAL"
        sl_mult, tp_mult = c["sl_multiplier"], c["tp_multiplier"]

        # Exit sinyal
        if st.in_position and sig.sell_signal:
            self.execute_exit(symbol, st, price, "SIGNAL", f"{strat} exit")
            self.states.save_state(st)
            return

        # Entry + risk veto
        if sig.buy_signal and not st.in_position:
            est_entry = price * 1.0005
            est_sl = est_entry - sig.atr_value * sl_mult
            decision = self.risk.evaluate_entry(symbol, equity, all_states, est_entry, est_sl)
            if not decision.allowed:
                logger.info(f"risk_veto {symbol}: {decision.reason}")
                return
            self.execute_buy(symbol, st, price, sig.atr_value, decision.adjusted_quote,
                             sl_mult, tp_mult, strat)
            self.states.save_state(st)

        # Persist semua perubahan state (sync / breakeven / OCO) setiap cycle
        self.states.save_state(st)

    # ---------------- EKSEKUSI ----------------
    def execute_buy(self, symbol, st, price, atr_v, quote, sl_mult, tp_mult, strat):
        if not self.breaker.allow():
            logger.warning(f"breaker_open skip buy {symbol}")
            return
        filters = self.client.get_symbol_filters(symbol)
        if self.dry_run:
            st.in_position = True
            st.entry_price, st.quantity = price, quote / price
            st.entry_atr, st.strategy = atr_v, strat
            st.sl_price = round_price(price - atr_v * sl_mult, filters)
            st.tp_price = round_price(price + atr_v * tp_mult, filters)
            st.entry_ts = datetime.now(timezone.utc).isoformat()
            if self.notifier:
                self.notifier.send(f"[DRY] BUY {symbol} @ {price:.4f}\nSL {st.sl_price:.4f} | TP {st.tp_price:.4f} | {strat}")
            return
        try:
            order = self.client.market_buy_quote_qty(symbol, quote)
            fills = order.get("fills") or []
            if not fills: return
            fq = sum(float(f["qty"]) for f in fills)
            fc = sum(float(f["price"]) * float(f["qty"]) for f in fills)
            fp = fc / fq
            st.in_position = True
            st.entry_price, st.quantity, st.entry_atr = fp, fq, atr_v
            st.strategy = strat
            st.entry_ts = datetime.now(timezone.utc).isoformat()
            st.sl_price = round_price(fp - atr_v * sl_mult, filters)
            st.tp_price = round_price(fp + atr_v * tp_mult, filters)
            oco = self.client.place_oco_sell(symbol, fq, st.tp_price, st.sl_price,
                                             round_price(st.sl_price * 0.999, filters))
            st.oco_order_list_id = oco.get("orderListId") if oco else None
            self.breaker.record_success()
            if self.trade_history:
                self.trade_history.record_entry(symbol, fp, fq, strat)
            if self.notifier:
                self.notifier.send(f"BUY {symbol} @ {fp:.4f} qty {fq}\nSL {st.sl_price:.4f} | TP {st.tp_price:.4f} | {strat}")
        except Exception as e:
            self.breaker.record_failure()
            logger.error(f"buy_failed {symbol}: {e}")
            if self.notifier:
                self.notifier.send(f"BUY FAILED {symbol}: {e}")

    def execute_exit(self, symbol, st, price, exit_type, reason=""):
        if not self.dry_run and st.in_position and st.quantity > 0:
            try:
                if st.oco_order_list_id:
                    try: self.client.cancel_oco(symbol, st.oco_order_list_id)
                    except Exception: pass
                order = self.client.market_sell(symbol, st.quantity)
                fills = order.get("fills") or []
                if fills:
                    q = sum(float(f["qty"]) for f in fills)
                    c = sum(float(f["price"]) * float(f["qty"]) for f in fills)
                    price = c / q if q else price
            except Exception as e:
                logger.error(f"sell_failed {symbol}: {e}")
                if self.notifier:
                    self.notifier.send(f"SELL FAILED {symbol}: {e} - TUTUP MANUAL!")
                return
        pnl = (price - st.entry_price) / st.entry_price * 100 if st.entry_price else 0
        if self.trade_history:
            self.trade_history.record_exit(symbol, price, st.quantity, st.entry_price, exit_type, st.strategy)
        if self.notifier:
            self.notifier.send(f"SELL {symbol} @ {price:.4f} ({exit_type})\nPnL {pnl:+.2f}% | {reason}")
        st.in_position = False
        st.quantity = 0
        st.oco_order_list_id = None
        st.breakeven_triggered = False

    # ---------------- EXCHANGE SYNC (self-healing) ----------------
    def sync_position(self, symbol, st):
        if not st.in_position: return st
        base = symbol.replace("USDT", "")
        free = self.client.get_free_balance(base)
        if free < st.quantity * 0.999:
            self._record_external_exit(symbol, st)
            return st
        if st.oco_order_list_id:
            try:
                oco = self.client.get_oco_status(symbol, st.oco_order_list_id)
                stt = (oco or {}).get("orderListStatus", "")
                if stt == "EXECUTED":
                    self._record_external_exit(symbol, st)
                    return st
                if stt in ("CANCELED", "EXPIRED", "REJECTED"):
                    self._replace_oco(symbol, st)
            except Exception as e:
                logger.warning(f"oco_status_error {symbol}: {e}")
        else:
            self._replace_oco(symbol, st)
        return st

    def _record_external_exit(self, symbol, st):
        fill = self._last_sell_fill(symbol, st) or st.entry_price
        etype = "TP" if st.tp_price and fill >= st.tp_price * 0.999 else (
                "SL" if st.sl_price and fill <= st.sl_price * 1.001 else "SYNC")
        pnl = (fill - st.entry_price) / st.entry_price * 100 if st.entry_price else 0
        if self.trade_history:
            self.trade_history.record_exit(symbol, fill, st.quantity, st.entry_price, etype, st.strategy)
        if self.notifier:
            self.notifier.send(f"{etype} {symbol} terisi @ {fill:.4f}\nPnL {pnl:+.2f}%")
        st.in_position = False
        st.quantity = 0
        st.oco_order_list_id = None
        st.breakeven_triggered = False

    def _last_sell_fill(self, symbol, st):
        try:
            trades = self.client.client.get_my_trades(symbol=symbol, limit=50)
        except Exception:
            return None
        entry_ms = 0
        if st.entry_ts:
            try: entry_ms = int(datetime.fromisoformat(st.entry_ts).timestamp() * 1000)
            except ValueError: entry_ms = 0
        sells = [t for t in trades if not t.get("isBuyer") and int(t.get("time", 0)) >= entry_ms]
        qty = sum(float(t["qty"]) for t in sells)
        if not sells or qty < st.quantity * 0.5: return None
        return sum(float(t["qty"]) * float(t["price"]) for t in sells) / qty

    def _replace_oco(self, symbol, st):
        if st.quantity <= 0 or st.sl_price <= 0 or st.tp_price <= 0: return
        try:
            if st.oco_order_list_id:
                try: self.client.cancel_oco(symbol, st.oco_order_list_id)
                except Exception: pass
            filters = self.client.get_symbol_filters(symbol)
            oco = self.client.place_oco_sell(symbol, st.quantity,
                round_price(st.tp_price, filters), round_price(st.sl_price, filters),
                round_price(st.sl_price * 0.999, filters))
            st.oco_order_list_id = oco.get("orderListId") if oco else None
            logger.info(f"oco_replaced {symbol}")
        except Exception as e:
            logger.warning(f"oco_replace_failed {symbol}: {e}")

    # ---------------- TELEGRAM COMMANDS ----------------
    def cmd_status(self, args):
        all_states = self.states.load_all_states(self.cfg["trading"]["symbols"])
        equity = self.client.get_total_portfolio_value_usdt(self.cfg["trading"]["symbols"], all_states)
        msg = f"Status | {'DRY' if self.dry_run else 'LIVE'} | {'PAUSED' if self.is_paused else 'ACTIVE'}\n"
        msg += self.risk.get_status(equity, all_states)
        if self.notifier: self.notifier.send(msg)

    def cmd_positions(self, args):
        pos = self.states.get_open_positions()
        if not pos:
            if self.notifier: self.notifier.send("No open positions")
            return
        lines = [f"{p['symbol']}: {p['quantity']} @ {p['entry_price']:.4f} | SL {p['sl_price']:.4f} | TP {p['tp_price']:.4f} | {p['strategy']}" for p in pos]
        if self.notifier: self.notifier.send("\n".join(lines))

    def cmd_pause(self, args):
        self.is_paused = True
        if self.notifier: self.notifier.send("PAUSED - entry baru diblokir")

    def cmd_resume(self, args):
        self.is_paused = False
        if self.notifier: self.notifier.send("RESUMED")

    def cmd_close(self, args):
        sym = args.strip().upper()
        st = self.states.load_state(sym)
        if not st.in_position:
            if self.notifier: self.notifier.send(f"No position {sym}")
            return
        try: px = float(self.client.client.get_symbol_ticker(symbol=sym)["price"])
        except Exception: px = st.entry_price
        self.execute_exit(sym, st, px, "MANUAL", "close via Telegram")
        self.states.save_state(st)
