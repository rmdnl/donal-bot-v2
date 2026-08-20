"""DONAL Bot Pro - entry point (Phase 1: foundation)."""
import argparse, os
from dotenv import load_dotenv
from core.config_loader import ConfigLoader
from core.structured_logger import get_structured_logger
from core.state_manager import StateManager
from core.binance_client import BinanceSpotBot

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
    logger.info(f"bot_startup mode={cfg['trading']['mode']} symbols={cfg['trading']['symbols']}")

    states = StateManager(cfg["database"]["sqlite_file"])
    logger.info(f"state_ready open_positions={len(states.get_open_positions())}")

    load_dotenv()
    testnet = cfg["trading"]["mode"] == "testnet"
    key = os.getenv("BINANCE_TESTNET_API_KEY" if testnet else "BINANCE_API_KEY")
    sec = os.getenv("BINANCE_TESTNET_API_SECRET" if testnet else "BINANCE_API_SECRET")

    if key and sec:
        client = BinanceSpotBot(key, sec, testnet=testnet)
        df = client.get_recent_klines(cfg["trading"]["symbols"][0], "1h", limit=1)
        logger.info(f"binance_connected testnet={testnet} last_close={float(df.iloc[-1]['close']):.2f}")
        print(f"✓ Binance connected ({'testnet' if testnet else 'LIVE'})")
    else:
        print("⚠️  No API keys in .env — exchange connection skipped")

    print("✓ DONAL Bot Pro Phase 1 ready")
    print("  (strategies + risk + monitoring = Phase 2, lanjutkan development)")

if __name__ == "__main__":
    main()
