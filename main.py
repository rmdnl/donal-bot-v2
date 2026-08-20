"""DONAL Bot Pro - entry point (Phase 3: full bot loop)."""
import argparse, os, signal
from dotenv import load_dotenv
from core.config_loader import ConfigLoader
from core.structured_logger import get_structured_logger
from core.state_manager import StateManager
from core.binance_client import BinanceSpotBot
from core.bot import Bot
from risk.risk_manager import RiskManager
from risk.circuit_breaker import CircuitBreaker
from risk.breakeven_manager import BreakevenManager
from monitoring.telegram_notifier import TelegramNotifier
from core.trade_history import TradeHistory
from monitoring.anomaly_detector import AnomalyDetector
from monitoring.daily_report import DailyReport

def main():
    p = argparse.ArgumentParser(description="DONAL Bot Pro")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--testnet", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    cfg = ConfigLoader(args.config).load()
    if args.testnet: cfg["trading"]["mode"] = "testnet"
    if args.dry_run: cfg["trading"]["dry_run"] = True
    if args.verbose: cfg["logging"]["level"] = "DEBUG"

    lc = cfg["logging"]
    logmgr = get_structured_logger(log_file=lc["log_file"], max_size_mb=lc["max_size_mb"],
        backup_count=lc["backup_count"], json_format=lc["json_format"],
        console_output=lc["console_output"], level=lc["level"])
    logger = logmgr.get_logger()
    logger.info(f"bot_startup mode={cfg['trading']['mode']} dry_run={args.dry_run}")

    states = StateManager(cfg["database"]["sqlite_file"])
    load_dotenv()
    testnet = cfg["trading"]["mode"] == "testnet"
    key = os.getenv("BINANCE_TESTNET_API_KEY" if testnet else "BINANCE_API_KEY")
    sec = os.getenv("BINANCE_TESTNET_API_SECRET" if testnet else "BINANCE_API_SECRET")

    notifier = TelegramNotifier(os.getenv("TELEGRAM_BOT_TOKEN", ""),
                                os.getenv("TELEGRAM_CHAT_ID", ""))
    history = TradeHistory(cfg["database"]["sqlite_file"])
    anomaly = AnomalyDetector(notifier=notifier)
    daily = DailyReport(notifier, history, send_time_utc=cfg["monitoring"]["daily_report"]["send_time_utc"])
    notifier.register("/report", daily.send_now)

    if not (key and sec):
        print("⚠️  No API keys in .env - bot loop tidak jalan")
        print("   cp .env.example .env lalu isi credentials")
        return

    client = BinanceSpotBot(key, sec, testnet=testnet)
    cb = cfg["circuit_breaker"]
    bot = Bot(
        client=client,
        states=states,
        risk=RiskManager(cfg["risk"]),
        breaker=CircuitBreaker(cb["api_max_failures"], cb["api_cooldown_seconds"], "api"),
        breakeven=BreakevenManager(cfg["strategy"]["breakeven"]["enabled"],
                                   cfg["strategy"]["breakeven"]["trigger_atr_multiplier"]),
        notifier=notifier,
        cfg=cfg,
        trade_history=history,
        anomaly=anomaly,
        dry_run=args.dry_run or cfg["trading"].get("dry_run", False),
    )

    signal.signal(signal.SIGINT, lambda s, f: bot.stop())
    signal.signal(signal.SIGTERM, lambda s, f: bot.stop())

    print(f"▶ DONAL Bot Pro | mode={cfg['trading']['mode']} | dry_run={bot.dry_run}")
    print("  Ctrl+C untuk stop")
    bot.run()

if __name__ == "__main__":
    main()
