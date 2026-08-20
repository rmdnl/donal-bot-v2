# donal-bot-pro

Automated spot trading bot for Binance with multi-regime strategy routing
and production-grade risk management.

## Overview

The bot monitors multiple symbols and routes each one to a strategy based
on the detected market regime (4H timeframe):

| Regime   | Condition                    | Strategy                          |
|----------|------------------------------|-----------------------------------|
| TREND    | ADX > 25 and EMA20 > EMA60   | DONAL breakout (HH20 on 1H)       |
| SIDEWAYS | ADX < 20                     | Mean reversion (Bollinger + RSI)  |
| BEAR     | EMA20 < EMA60                | No new entries; open positions closed |

## Features

Trading
- Multi-symbol monitoring with 4H trend filter and 1H entry confirmation
- OCO take-profit / stop-loss with automatic re-placement (self-healing)
- Breakeven stop: SL moves to entry after 1x ATR profit
- Position state persisted in SQLite; survives restarts

Risk management
- Risk-based position sizing with per-asset (7.5%) and total (30%) exposure caps
- Daily / weekly loss limits and max drawdown lock
- Flash-crash kill switch on 1m candles with volume confirmation, plus cooldown
- Circuit breaker for API and order failures

Operations
- Telegram notifications and remote commands
- Daily performance report (scheduled + on-demand)
- Anomaly alerts: API health, unexplained balance drops, unprotected positions
- Structured JSON logging with file rotation
- Streamlit analytics dashboard
- Unit test suite

## Requirements

- Ubuntu 20.04+ VPS
- Python 3.9+
- Binance API key (spot trading permission only)
- Telegram bot token (optional, for notifications)

## Installation (fresh VPS)

    git clone https://github.com/rmdnl/donal-bot-pro.git
    cd donal-bot-pro
    chmod +x scripts/install_vps.sh
    ./scripts/install_vps.sh

The installer creates a virtualenv, installs dependencies, copies
`.env.example` to `.env`, and registers the systemd service.

Fill in credentials, then start:

    nano .env
    sudo systemctl start donal-bot-pro
    journalctl -u donal-bot-pro -f

Recommended first run (simulation, no real orders):

    sudo systemctl stop donal-bot-pro
    venv/bin/python main.py --dry-run

## Configuration

- `config.yaml` - strategy, risk, kill switch, logging, monitoring parameters
- `.env` - secrets (API keys, Telegram token); never committed

Default risk parameters:

| Parameter                | Default |
|--------------------------|---------|
| Risk per trade           | 1%      |
| Max exposure per asset   | 7.5%    |
| Max total exposure       | 30%     |
| Daily loss limit         | 3%      |
| Weekly loss limit        | 5%      |
| Max drawdown             | 10%     |
| Max open positions       | 3       |

## Telegram commands

    /status            bot and risk status
    /positions         open positions
    /pause             block new entries
    /resume            allow entries
    /close SYMBOL      close position manually
    /report            send performance report
    /help              list commands

## Dashboard

    streamlit run dashboard.py

Serves a web UI at port 8551 with cumulative PnL, win rate, profit factor,
and per-symbol / per-exit-type breakdowns.

## Testing

    venv/bin/python -m pytest tests/ -q

Smoke test against live public data (no API key required):

    venv/bin/python scripts/smoke_test.py

## Project layout

    main.py                  entry point
    config.yaml              configuration
    core/                    bot loop, binance client, state, logging, config
    strategies/              regime detector, DONAL, mean reversion, indicators
    risk/                    risk manager, kill switch, circuit breaker, breakeven
    monitoring/              telegram, daily report, anomaly detector, dashboard
    core/trade_history.py    SQLite trade database
    tests/                   unit tests
    scripts/                 installer and smoke test

## Security

- `.env` is gitignored; never commit secrets
- Binance API key: enable spot trading only, disable withdrawals, restrict to VPS IP

## Disclaimer

Trading cryptocurrency involves substantial risk of loss. This software is
provided as-is, without warranty. Backtest and paper-trade before using real
funds. Use at your own risk.
