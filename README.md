# DONAL Bot V2

Bot trading spot otomatis untuk Binance dengan routing strategi multi-regime, manajemen risiko berlapis, eksekusi aman, recovery setelah restart, dan dashboard web read-only yang ringan serta mobile-friendly.

> Current deployment: Binance Testnet, `dry_run=false`
>
> Dashboard: port `8501`
>
> Verified test suite: **247 passed**

## Status

| Component | Status |
|---|---|
| Binance Spot Testnet | 🟢 Active |
| Multi-regime strategy | 🟢 Active |
| Risk management | 🟢 Active |
| OCO protection | 🟢 Active |
| Partial-fill settlement | 🟢 Hardened |
| Fill idempotency | 🟢 Hardened |
| Recovery / restart sync | 🟢 Tested |
| Graceful shutdown | 🟢 Active |
| Telegram monitoring | 🟢 Active |
| Read-only dashboard | 🟢 Active |
| Automated tests | 🟢 247 passed |

Current deployment:

```text
mode=testnet
dry_run=false
symbols=BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT
poll_interval=60s
```

## Strategy

Bot menggunakan routing berdasarkan market regime.

| Regime | Behaviour |
|---|---|
| TREND | DONAL trend/breakout strategy |
| SIDEWAYS | Mean reversion |
| BEAR | Block entry baru |

Untuk altcoin, BTC regime digunakan sebagai gate tambahan. Ketika BTC berada dalam regime bearish, bot tidak membuka posisi baru pada altcoin.

## Execution Safety

- Risk-based position sizing
- Per-asset dan total exposure limits
- Daily / weekly loss protection
- Kill switch
- Circuit breaker
- Slippage monitoring
- OCO stop-loss / take-profit
- OCO recovery / replacement
- Balance synchronization
- Locked-balance awareness
- Partial-fill settlement
- Fill idempotency
- Duplicate-fill protection
- Restart recovery
- Position reconciliation
- Graceful SIGTERM shutdown

Partial fill tidak dianggap sebagai full fill. Jika executed quantity berubah dari `0.002` menjadi `0.005`, reconciliation hanya menerapkan delta `0.003`.

## Position & Recovery

State posisi disimpan di SQLite:

```text
data/trades.db
```

Recovery engine menangani pending/filled orders, posisi setelah restart, partial exit, replay protection, dan idempotency.

## Dashboard

Dashboard web **read-only** berjalan pada port:

```text
8501
```

Dirancang untuk VPS kecil:

- Lightweight web stack
- Tanpa React / Node.js
- Mobile-first
- Auto refresh
- Tidak memiliki endpoint BUY / SELL
- Tidak menyimpan API key Binance

Menampilkan bot status, equity, PnL, win rate, active positions, Entry/SL/TP, OCO status, recent trades, heartbeat, cycle interval, error count, risk snapshot, dan equity history.

Akses:

```text
http://<IP-VPS>:8501
```

Service:

```text
donal-dashboard.service
```

## Trading Service

```text
donal-bot-v2.service
```

Cek:

```bash
systemctl status donal-bot-v2.service
systemctl status donal-dashboard.service
```

Restart:

```bash
sudo systemctl restart donal-bot-v2.service
sudo systemctl restart donal-dashboard.service
```

## Configuration

```text
config.yaml
.env
```

Contoh environment:

```text
BINANCE_API_KEY=...
BINANCE_API_SECRET=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

Jangan commit `.env`.

Untuk Binance API key gunakan Spot trading only, withdrawal disabled, IP restriction, dan Testnet selama fase observasi.

## Telegram

Telegram digunakan untuk monitoring dan operational control. Command mengikuti implementasi bot saat ini, termasuk status, positions, regime, PnL, recent trades, config, pause/resume, report, dan help.

## Logging

Structured JSON logging digunakan pada:

```text
bot.log
```

Contoh heartbeat:

```json
{"level":"INFO","module":"bot","msg":"bot_cycle symbols=4 equity=5401.79"}
```

## Architecture

```text
main.py
├── core/
├── app/
│   ├── execution/
│   ├── exchange/
│   ├── position/
│   ├── recovery/
│   ├── portfolio/
│   ├── trading/
│   └── storage/
├── strategies/
├── risk/
├── monitoring/
├── dashboard/
├── tests/
└── data/
```

## Installation

```bash
git clone https://github.com/rmdnl/donal-bot-v2.git
cd donal-bot-v2
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Configure:

```bash
nano .env
nano config.yaml
```

Run tests:

```bash
pytest -q
```

## Testing

Verified full suite:

```text
247 passed
```

Focused execution/recovery suite:

```bash
pytest -q tests/test_recovery_v2.py tests/test_recovery_position_sync.py tests/test_execution_settlement.py tests/test_execution_loop.py tests/test_bot_oco_balance.py
```

Verified focused result:

```text
29 passed
```

Coverage includes partial fills, duplicate fills, idempotent settlement, partial sells, restart recovery, OCO balance handling, position synchronization, execution settlement, order idempotency, and safe order execution.

## Current Deployment

Branch:

```text
v2-foundation
```

The bot is currently intended for Binance Testnet observation before production deployment.

Passing automated tests does not guarantee profitable trading or production safety. Exchange behaviour, fills, OCO lifecycle, recovery, and risk controls must also be validated under testnet conditions.

## Roadmap

### Phase 1
Trading engine hardening, execution safety, recovery, idempotency, OCO protection, graceful shutdown.

### Phase 2
Read-only dashboard, mobile UI, health monitoring, Telegram observability.

### Phase 3
Market analytics, equity snapshots, performance analytics, dashboard improvements.

### Phase 4
Extended testnet observation, failure injection, operational validation, production readiness review.

## Disclaimer

Cryptocurrency trading carries substantial risk of loss.

This software is provided as-is without guarantees. Use Binance Testnet and paper trading for validation before considering live capital.

This project is not financial advice.
