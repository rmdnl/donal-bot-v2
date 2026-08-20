"""Structured logging dengan rotation + correlation ID."""
import logging, logging.handlers, os, sys, uuid

class StructuredLogger:
    def __init__(self, log_file="bot.log", max_size_mb=10, backup_count=5,
                 json_format=True, console_output=True, console_format="text", level="INFO"):
        d = os.path.dirname(log_file)
        if d: os.makedirs(d, exist_ok=True)
        root = logging.getLogger()
        root.handlers = []
        root.setLevel(getattr(logging, level.upper(), logging.INFO))
        fh = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_size_mb * 1024 * 1024,
            backupCount=backup_count, encoding="utf-8")
        if json_format:
            fh.setFormatter(logging.Formatter(
                '{"ts":"%(asctime)s","level":"%(levelname)s","module":"%(module)s","line":%(lineno)d,"msg":"%(message)s"}'))
        else:
            fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        root.addHandler(fh)
        if console_output:
            ch = logging.StreamHandler(sys.stdout)
            ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
            root.addHandler(ch)
        self.logger = logging.getLogger("donal_bot")

    def get_logger(self, correlation_id=None):
        return self.logger

    def generate_correlation_id(self):
        return str(uuid.uuid4())[:8]

    def log_trade_entry(self, symbol, strategy, entry_price, quantity, sl, tp, cid):
        self.logger.info(f"[{cid}] trade_entry symbol={symbol} strat={strategy} "
                         f"px={entry_price:.4f} qty={quantity} sl={sl:.4f} tp={tp:.4f}")

    def log_trade_exit(self, symbol, exit_price, entry_price, quantity, reason, pnl_pct, pnl_usdt, cid):
        self.logger.info(f"[{cid}] trade_exit symbol={symbol} px={exit_price:.4f} "
                         f"reason={reason} pnl={pnl_pct:+.2f}%/{pnl_usdt:+.2f}USDT")

_logger = None
def get_structured_logger(**kwargs):
    global _logger
    if _logger is None:
        _logger = StructuredLogger(**kwargs)
    return _logger
