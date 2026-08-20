"""Binance client MASTER v4: rate limiter, retry, anti-lookahead, OCO version-proof."""
import time, logging
from collections import deque
from functools import wraps
import pandas as pd
from binance.client import Client
from binance.enums import SIDE_SELL, TIME_IN_FORCE_GTC
from binance.exceptions import BinanceAPIException

try:
    import structlog
    logger = structlog.get_logger("binance_client")
except ImportError:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger("binance_client")

KLINE_COLUMNS = ["open_time","open","high","low","close","volume","close_time",
                 "quote_asset_volume","num_trades","taker_buy_base","taker_buy_quote","ignore"]

class RateLimiter:
    def __init__(self, max_weight=1100, window_seconds=60):
        self.max_weight, self.window, self._entries = max_weight, window_seconds, deque()
    def acquire(self, weight=1):
        now = time.monotonic()
        while self._entries and self._entries[0][0] <= now - self.window: self._entries.popleft()
        if sum(w for _, w in self._entries) + weight > self.max_weight:
            sleep_time = (self._entries[0][0] + self.window) - now + 0.05
            if sleep_time > 0: time.sleep(sleep_time)
        self._entries.append((time.monotonic(), weight))
    def update_from_header(self, used):
        self._entries.clear(); self._entries.append((time.monotonic(), min(used, self.max_weight)))

def retry(max_retries=3, base_delay=1.0):
    def deco(func):
        @wraps(func)
        def wrap(*a, **kw):
            last = None
            for attempt in range(max_retries + 1):
                try: return func(*a, **kw)
                except BinanceAPIException as e:
                    last = e
                    if e.status_code == 418: raise
                    if attempt < max_retries: time.sleep(base_delay * 2 ** attempt)
                    else: raise
                except Exception as e:
                    last = e
                    if attempt < max_retries: time.sleep(base_delay * 2 ** attempt)
                    else: raise
            raise last
        return wrap
    return deco

class BinanceSpotBot:
    def __init__(self, api_key, api_secret, testnet=True):
        self.client = Client(api_key, api_secret, testnet=testnet)
        self.testnet = testnet
        self.rate_limiter = RateLimiter()
        self._st_ms = self._st_mono = 0

    def _weight(self):
        try: return int(self.client.response.headers.get("X-MBX-USED-WEIGHT", 1))
        except Exception: return 1

    def _server_time_ms(self):
        now = time.monotonic()
        if not self._st_ms or now - self._st_mono > 30:
            self.rate_limiter.acquire(1)
            self._st_ms = self.client.get_server_time()["serverTime"]
            self._st_mono = now
            self.rate_limiter.update_from_header(self._weight())
        return self._st_ms

    @retry()
    def get_closed_klines(self, symbol, interval, limit=200):
        self.rate_limiter.acquire(2)
        raw = self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
        self.rate_limiter.update_from_header(self._weight())
        df = pd.DataFrame(raw, columns=KLINE_COLUMNS)
        for c in ["open","high","low","close","volume"]: df[c] = df[c].astype(float)
        df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
        if int(raw[-1][6]) > self._server_time_ms(): df = df.iloc[:-1]
        return df.reset_index(drop=True)

    @retry()
    def get_recent_klines(self, symbol, interval, limit=100):
        self.rate_limiter.acquire(2)
        raw = self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
        self.rate_limiter.update_from_header(self._weight())
        df = pd.DataFrame(raw, columns=KLINE_COLUMNS)
        for c in ["open","high","low","close","volume"]: df[c] = df[c].astype(float)
        df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
        return df.reset_index(drop=True)

    @retry()
    def get_free_balance(self, asset):
        self.rate_limiter.acquire(1)
        bal = self.client.get_asset_balance(asset=asset)
        self.rate_limiter.update_from_header(self._weight())
        return float(bal["free"]) if bal else 0.0

    @retry()
    def get_total_portfolio_value_usdt(self, symbols, states):
        total = self.get_free_balance("USDT")
        for sym, st in states.items():
            if st.in_position and st.quantity > 0:
                try:
                    self.rate_limiter.acquire(1)
                    px = float(self.client.get_symbol_ticker(symbol=sym)["price"])
                    self.rate_limiter.update_from_header(self._weight())
                except Exception:
                    px = st.entry_price
                total += px * st.quantity
        return total

    @retry()
    def get_symbol_filters(self, symbol):
        self.rate_limiter.acquire(1)
        info = self.client.get_symbol_info(symbol)
        self.rate_limiter.update_from_header(self._weight())
        return {f["filterType"]: f for f in info["filters"]}

    @retry()
    def market_buy_quote_qty(self, symbol, quote_qty):
        self.rate_limiter.acquire(1)
        r = self.client.order_market_buy(symbol=symbol, quoteOrderQty=round(quote_qty, 2))
        self.rate_limiter.update_from_header(self._weight())
        return r

    @retry()
    def market_sell(self, symbol, quantity):
        self.rate_limiter.acquire(1)
        r = self.client.order_market_sell(symbol=symbol, quantity=quantity)
        self.rate_limiter.update_from_header(self._weight())
        return r

    @retry()
    def place_oco_sell(self, symbol, quantity, tp_price, sl_stop, sl_limit):
        self.rate_limiter.acquire(1)
        try:
            r = self.client.create_oco_order(symbol=symbol, side=SIDE_SELL, quantity=quantity,
                price=str(tp_price), stopPrice=str(sl_stop), stopLimitPrice=str(sl_limit),
                stopLimitTimeInForce=TIME_IN_FORCE_GTC)
        except (AttributeError, TypeError):
            r = self.client.order_oco_sell(symbol=symbol, quantity=quantity,
                price=str(tp_price), stopPrice=str(sl_stop), stopLimitPrice=str(sl_limit),
                stopLimitTimeInForce=TIME_IN_FORCE_GTC)
        self.rate_limiter.update_from_header(self._weight())
        return r

    @retry()
    def cancel_oco(self, symbol, order_list_id):
        self.rate_limiter.acquire(1)
        try: r = self.client.cancel_oco_order(symbol=symbol, orderListId=order_list_id)
        except (AttributeError, TypeError): r = self.client.cancel_order_list(symbol=symbol, orderListId=order_list_id)
        self.rate_limiter.update_from_header(self._weight())
        return r

    @retry()
    def get_oco_status(self, symbol, order_list_id):
        self.rate_limiter.acquire(1)
        try: r = self.client.get_oco_order(orderListId=order_list_id)
        except (AttributeError, TypeError): r = self.client.get_order_list(orderListId=order_list_id)
        self.rate_limiter.update_from_header(self._weight())
        return r
