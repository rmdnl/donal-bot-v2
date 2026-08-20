# donal-bot-pro

Bot trading spot otomatis untuk Binance dengan routing strategi multi-regime,
manajemen risiko berlapis ala institusional, dan framework backtesting lengkap.

> Dibangun untuk trading algoritmik yang serius: setiap keputusan tercatat,
> setiap posisi terlindungi, dan setiap strategi divalidasi sebelum deploy.

---

## Ringkasan

Bot memantau beberapa simbol dan mengarahkan masing-masing ke strategi yang
paling cocok dengan regime pasar saat ini, terdeteksi pada timeframe 4H:

| Regime   | Kondisi                    | Strategi                          |
|----------|----------------------------|-----------------------------------|
| TREND    | ADX > 25 dan EMA20 > EMA60 | DONAL breakout (HH20 pada 1H)     |
| SIDEWAYS | ADX < 20                   | Mean reversion (Bollinger + RSI)  |
| BEAR     | EMA20 < EMA60              | Tanpa entry baru; hanya exit      |

Seluruh logika dipakai bersama antara bot live dan engine backtest, sehingga
hasil backtest mereproduksi perilaku live secara akurat.

---

## Fitur Utama

### Trading
- Pemantauan multi-simbol dengan filter tren 4H + konfirmasi entry 1H
- OCO take-profit / stop-loss dengan pemasangan ulang otomatis (self-healing)
- Breakeven stop: SL pindah ke entry setelah profit 1x ATR
- State posisi di SQLite; tahan restart dan crash

### Manajemen Risiko Institusional
- Position sizing berbasis risiko dengan batas exposure per-aset (7.5%) dan total (30%)
- Limit rugi harian / mingguan dan kunci max drawdown
- Kill switch flash-crash pada candle 1m dengan konfirmasi volume
- Circuit breaker untuk kegagalan API dan order
- **BTC gate** - altcoin dilarang entry saat BTC berada di regime bear
- **Time stop** - posisi basi (>48 jam tanpa profit) ditutup otomatis
- **Slippage monitor** - alert bila fill melenceng >0.15% dari sinyal

### Operasional
- Notifikasi dan kendali jarak jauh via Telegram
- Laporan performa terjadwal + on-demand
- Deteksi anomali: kesehatan API, penurunan saldo, posisi tak terlindungi
- Logging JSON terstruktur dengan rotasi dan correlation ID
- Dashboard analitik Streamlit (service terpisah, port 8501)
- Suite unit test

### Riset
- Engine backtest multi-regime (identik dengan logika live)
- Engine alternatif: swing Daily+4H, scalping 5m, pullback 15m
- Optimizer parameter grid-search
- Laporan visual equity / drawdown

---

## Arsitektur

```
main.py                     entry point + wiring
core/
  bot.py                    main loop, eksekusi, sinkronisasi exchange
  binance_client.py         rate limiter, retry, OCO (tahan beda versi)
  state_manager.py          persistensi posisi SQLite
  trade_history.py          database trade SQLite
  structured_logger.py      logging JSON + rotasi
  config_loader.py          config YAML + validasi
strategies/
  regime_detector.py        routing regime ADX + EMA
  donal_strategy.py         trend-following breakout
  mean_reversion_strategy.py strategi sideways
  swing_strategy.py         swing Daily+4H + trailing stop
  pullback_strategy.py      pullback 15m + filter tren 4H
  indicators.py             EMA / RSI / ATR / HH (Wilder)
risk/
  risk_manager.py           sizing + clamp exposure + limit rugi
  kill_switch.py            deteksi flash-crash
  circuit_breaker.py        proteksi kegagalan API/order
  breakeven_manager.py      penyesuaian SL otomatis
monitoring/
  telegram_notifier.py      notifikasi + perintah
  daily_report.py           laporan terjadwal
  anomaly_detector.py       pemantauan kesehatan
  dashboard.py              UI web Streamlit (port 8501)
backtest/
  download_data.py          pengunduh data historis
  engine.py                 simulator multi-regime
  engine_swing.py           simulator swing Daily+4H
  engine_scalp.py           simulator scalping 5m
  engine_pullback.py        simulator pullback 15m
  optimizer.py              grid search
  report.py                 chart equity/drawdown
~~~

---

## Layanan (systemd)

| Service           | Fungsi                          |
|-------------------|---------------------------------|
| `donal-bot-pro`   | Bot trading (testnet/live)      |
| `donal-dashboard` | Dashboard web di port 8501      |

---

## Instalasi (VPS baru)

```bash
git clone https://github.com/rmdnl/donal-bot-pro.git
cd donal-bot-pro
chmod +x scripts/install_vps.sh
./scripts/install_vps.sh

nano .env                  # isi kredensial
sudo systemctl start donal-bot-pro
sudo systemctl start donal-dashboard
journalctl -u donal-bot-pro -f

# Dashboard web tersedia di http://<IP-VPS>:8501
```

Jalankan pertama kali dalam mode simulasi:

```bash
venv/bin/python main.py --dry-run
```

---

## Konfigurasi

- `config.yaml` - strategi, risiko, kill switch, logging, monitoring
- `.env` - rahasia (tidak pernah di-commit)

Parameter risiko default:

| Parameter                | Default |
|--------------------------|---------|
| Risiko per trade         | 1%      |
| Exposure maks per aset   | 7.5%    |
| Exposure total maks      | 30%     |
| Limit rugi harian        | 3%      |
| Limit rugi mingguan      | 5%      |
| Max drawdown             | 10%     |
| Posisi terbuka maks      | 4       |

---

## Perintah Telegram

~~~
/status      status bot + risiko
/positions   posisi terbuka
/regime      regime pasar per simbol
/pnl         ringkasan performa
/recent N    N trade terakhir
/config      konfigurasi aktif
/pause       blokir entry baru
/resume      izinkan entry
/close SYM   tutup posisi manual
/report      kirim laporan performa
/help        daftar perintah
```

---

## Backtesting

```bash
# Unduh data historis
venv/bin/python -m backtest.download_data --symbols BTCUSDT,ETHUSDT --months 6

# Backtest multi-regime
venv/bin/python -m backtest.engine --symbol BNBUSDT

# Uji A/B: routing regime nyala vs mati
venv/bin/python -m backtest.engine --symbol BNBUSDT --no_regime

# Optimasi SL/TP
venv/bin/python -m backtest.optimizer --symbol BNBUSDT --top 10

# Buat chart equity/drawdown
venv/bin/python -m backtest.report --symbol BNBUSDT

# Backtest strategi alternatif (riset)
venv/bin/python -m backtest.engine_swing --symbol BNBUSDT
venv/bin/python -m backtest.engine_scalp --symbol BTCUSDT
venv/bin/python -m backtest.engine_pullback --symbol BTCUSDT
```

---

## Testing

```bash
venv/bin/python -m pytest tests/ -q
```

---

## Keamanan

- `.env` di-gitignore; jangan pernah commit rahasia
- API key Binance: hanya spot trading, withdrawals dimatikan, dibatasi IP
- Mulai dari testnet; naik ke live hanya setelah validasi positif

---

## Status & Roadmap

Selesai: strategi multi-regime, risiko berlapis, OCO self-heal, breakeven,
kendali Telegram, dashboard, suite backtest (multi-regime, swing, scalping,
pullback), unit test.

Hasil riset (18 bulan data, 4 simbol, 6 keluarga strategi): strategi teknikal
retail di pair major spot tidak memiliki edge setelah biaya (PF terbaik 0.89).
Fase riset alpha ditutup; bot berjalan di testnet untuk observasi stabilitas
platform.

Direncanakan (opsional): backup offsite otomatis, CI/CD, riset funding/basis
market-neutral.

---

## Disclaimer

Trading cryptocurrency mengandung risiko kerugian yang besar. Software ini
disediakan apa adanya, tanpa jaminan. Lakukan backtest dan paper-trade secara
menyeluruh sebelum memakai dana sungguhan. Ini bukan nasihat keuangan.
Gunakan dengan risiko Anda sendiri.
