"""YAML config loader dengan defaults + validation."""
import os, yaml

class ConfigLoader:
    def __init__(self, config_path="config.yaml"):
        self.config_path = config_path

    def load(self):
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config not found: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        self._defaults(cfg)
        self._validate(cfg)
        return cfg

    def _defaults(self, cfg):
        d = {
            "trading": {"mode": "testnet", "symbols": ["BTCUSDT"],
                        "poll_interval_seconds": 60, "fee_rate": 0.001,
                        "min_order_usdt": 10.0, "dry_run": False},
            "logging": {"level": "INFO", "json_format": True, "log_file": "bot.log",
                        "max_size_mb": 10, "backup_count": 5,
                        "console_output": True, "console_format": "text"},
            "database": {"sqlite_file": "data/trades.db"},
        }
        for section, values in d.items():
            cfg.setdefault(section, {})
            for k, v in values.items():
                cfg[section].setdefault(k, v)

    def _validate(self, cfg):
        if cfg["trading"]["mode"] not in ("testnet", "live"):
            raise ValueError("trading.mode must be 'testnet' or 'live'")
        if not isinstance(cfg["trading"]["symbols"], list) or not cfg["trading"]["symbols"]:
            raise ValueError("trading.symbols must be a non-empty list")
