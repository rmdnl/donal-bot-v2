"""Modern live web dashboard (mobile-friendly, auto-refresh tanpa reload).

Server ringan pakai http.server bawaan Python.
Endpoint: / (HTML) dan /api/data (JSON).
"""
import json, os, sqlite3, subprocess, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pandas as pd
import requests

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
DB = os.path.join(BASE, "data", "trades.db")
PORT = int(os.environ.get("PORT", 8501))

from core.config_loader import ConfigLoader
from strategies.regime_detector import detect_regime

CFG = ConfigLoader(os.path.join(BASE, "config.yaml")).load()
SYMBOLS = CFG["trading"]["symbols"]
MODE = CFG["trading"].get("mode", "testnet")

_cache = {}
def cached(key, ttl, fn):
    now = time.time()
    if key not in _cache or now - _cache[key][0] > ttl:
        _cache[key] = (now, fn())
    return _cache[key][1]

def svc(name):
    try:
        return subprocess.run(["systemctl","is-active",name],
                              capture_output=True,text=True,timeout=2).stdout.strip()
    except Exception:
        return "unknown"

HOSTS = ["https://data-api.binance.vision", "https://api.binance.com", "https://api1.binance.com"]
_last_err = {"msg": ""}

def _sym_list():
    s = SYMBOLS
    if isinstance(s, str):
        return [x.strip() for x in s.split(",") if x.strip()]
    return list(s)

SYMS = _sym_list()

def tickers():
    errs = []
    for h in HOSTS:
        try:
            r = requests.get(h + "/api/v3/ticker/24hr", timeout=8)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, list):
                _last_err["msg"] = ""
                return {x["symbol"]: x for x in data if x.get("symbol") in SYMS}
            errs.append(h + ": " + str(data)[:60])
        except Exception as e:
            errs.append(h + ": " + type(e).__name__)
    _last_err["msg"] = " | ".join(errs)
    return {}

def regime(sym):
    for h in HOSTS:
        try:
            r = requests.get(h + "/api/v3/klines",
                             params={"symbol": sym, "interval": "4h", "limit": 120}, timeout=8)
            cols = ["ot","open","high","low","close","volume","ct","qv","tr","tb","tq","ig"]
            df = pd.DataFrame(r.json(), columns=cols)
            for c in ["open","high","low","close","volume"]:
                df[c] = df[c].astype(float)
            return detect_regime(df).mode.value
        except Exception:
            continue
    return "?"

def all_tickers():
    for h in HOSTS:
        try:
            r = requests.get(h + "/api/v3/ticker/24hr", timeout=8)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, list):
                return data
        except Exception:
            continue
    return []

def _k4(sym):
    for h in HOSTS:
        try:
            r = requests.get(h + "/api/v3/klines",
                             params={"symbol": sym, "interval": "4h", "limit": 120}, timeout=8)
            cols = ["ot","open","high","low","close","volume","ct","qv","tr","tb","tq","ig"]
            df = pd.DataFrame(r.json(), columns=cols)
            for c in ["open","high","low","close","volume"]:
                df[c] = df[c].astype(float)
            return df
        except Exception:
            continue
    return None

def scan_signals():
    from strategies.indicators import ema, rsi, highest
    tick = cached("alltick", 30, all_tickers)
    rows = [t for t in tick if t.get("symbol","").endswith("USDT")
            and not any(x in t.get("symbol","") for x in ["UP","DOWN","BULL","BEAR"])]
    rows.sort(key=lambda x: float(x.get("quoteVolume",0) or 0), reverse=True)
    out = []
    for t in rows[:20]:
        sym = t["symbol"]
        df = cached(f"k4_{sym}", 60, lambda s=sym: _k4(s))
        if df is None or len(df) < 60:
            continue
        close = df["close"]
        ef = float(ema(close,20).iloc[-1]); es = float(ema(close,50).iloc[-1])
        r = float(rsi(close,14).iloc[-1])
        hh = float(highest(df["high"],20).shift(1).iloc[-1])
        ll = float(df["low"].rolling(20).min().shift(1).iloc[-1])
        cl = float(close.iloc[-1])
        if ef > es and r > 50 and cl > hh: sig = "BUY"
        elif ef > es and cl < ef and cl > es: sig = "PULLBACK"
        elif ef < es and cl < ll: sig = "SELL"
        else: sig = "WAIT"
        out.append({"symbol":sym.replace("USDT",""),
                    "price":float(t.get("lastPrice",0) or 0),
                    "chg":float(t.get("priceChangePercent",0) or 0),
                    "rsi":round(r,0),"signal":sig})
    order = {"BUY":0,"PULLBACK":1,"SELL":2,"WAIT":3}
    out.sort(key=lambda x: order.get(x["signal"],4))
    return out

def query(sql):
    try:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=5)
        return pd.read_sql(sql, con)
    except Exception:
        return pd.DataFrame()

def get_data():
    tick = cached("tick", 5, tickers)
    state = query("SELECT * FROM state")
    pos = {}
    if not state.empty and "in_position" in state.columns:
        for _, p in state[state["in_position"].astype(int)==1].iterrows():
            pos[p["symbol"]] = p
    markets = []
    for sym in SYMBOLS:
        t = tick.get(sym, {})
        price = float(t.get("lastPrice",0) or 0)
        chg = float(t.get("priceChangePercent",0) or 0)
        m = {"symbol":sym,"price":price,"chg":chg,
             "regime":cached(f"reg_{sym}",60,lambda s=sym: regime(s))}
        if sym in pos:
            e=float(pos[sym].get("entry_price",0) or 0); q=float(pos[sym].get("qty",0) or 0)
            if e and price:
                m["pos"]={"pnl":(price-e)*q,"pct":(price-e)/e*100}
        markets.append(m)

    trades = query("SELECT * FROM trades")
    perf = {"trades":0,"wr":0,"pnl":0,"equity":[]}
    recent = []
    if not trades.empty and "pnl_usdt" in trades.columns:
        p = pd.to_numeric(trades["pnl_usdt"], errors="coerce").dropna()
        perf["trades"]=int(len(p))
        perf["wr"]=round(float((p>0).mean()*100),1)
        perf["pnl"]=round(float(p.sum()),2)
        perf["equity"]=[round(x,2) for x in p.cumsum().tolist()][-300:]
        tcol = "exit_time" if "exit_time" in trades.columns else trades.columns[0]
        for _, r in trades.tail(8).iloc[::-1].iterrows():
            recent.append({"time":str(r.get(tcol,""))[:16],
                           "symbol":str(r.get("symbol","")),
                           "exit":str(r.get("exit_type","")),
                           "pnl":float(r.get("pnl_usdt",0) or 0)})
    return {"time":time.strftime("%H:%M:%S"),"mode":MODE,"bot":svc("donal-bot-pro"),"err":_last_err["msg"],
            "markets":markets,"perf":perf,"recent":recent,"signals":cached("scan",60,scan_signals)}

HTML = """<!DOCTYPE html><html lang="id"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Donal Bot Pro</title><style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0b1220;color:#e5e7eb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;padding:16px}
.wrap{max-width:960px;margin:0 auto}
header{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:16px}
h1{font-size:1.3rem;font-weight:700}
.pill{padding:4px 12px;border-radius:999px;font-size:.75rem;font-weight:600}
.pill.ok{background:#064e3b;color:#34d399}.pill.bad{background:#7f1d1d;color:#fca5a5}
.pill.mode{background:#1e3a8a;color:#93c5fd}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:12px;margin-bottom:16px}
.card{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:14px;backdrop-filter:blur(8px)}
.row{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.sym{font-weight:700;font-size:.85rem;color:#9ca3af}
.badge{padding:2px 10px;border-radius:999px;font-size:.7rem;font-weight:700}
.badge.TREND{background:#065f46;color:#34d399}.badge.SIDEWAYS{background:#78350f;color:#fbbf24}
.badge.BEAR{background:#7f1d1d;color:#fca5a5}.badge.TRANSITION{background:#7c2d12;color:#fdba74}
.price{font-size:1.4rem;font-weight:800;letter-spacing:-.5px}
.chg{font-size:.8rem;font-weight:600;margin-top:4px}
.up{color:#34d399}.down{color:#f87171}
.pos{margin-top:8px;font-size:.8rem;font-weight:700;padding:6px 10px;border-radius:10px;background:rgba(255,255,255,.05)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:16px}
.stat{text-align:center}
.stat b{display:block;font-size:1.2rem}
.stat span{font-size:.72rem;color:#9ca3af;text-transform:uppercase;letter-spacing:.5px}
h2{font-size:.95rem;margin:16px 0 8px;color:#9ca3af}
table{width:100%;border-collapse:collapse;font-size:.8rem}
td,th{padding:8px 6px;text-align:left;border-bottom:1px solid rgba(255,255,255,.06)}
th{color:#6b7280;font-weight:600;text-transform:uppercase;font-size:.68rem}
svg{width:100%;height:60px}
footer{margin-top:16px;font-size:.72rem;color:#6b7280;display:flex;justify-content:space-between}
.sig{padding:2px 10px;border-radius:999px;font-size:.7rem;font-weight:800}
.sig-BUY{background:#065f46;color:#34d399}.sig-PULLBACK{background:#1e3a8a;color:#93c5fd}
.sig-SELL{background:#7f1d1d;color:#fca5a5}.sig-WAIT{background:#374151;color:#9ca3af}
.disc{font-size:.68rem;color:#6b7280;margin-top:6px}
</style></head><body><div class="wrap">
<header><h1>🤖 Donal Bot Pro</h1>
<div><span class="pill mode" id="mode"></span> <span class="pill ok" id="bot"></span></div></header>
<div class="grid" id="coins"></div>
<div class="card stats"><div class="stat"><b id="sTrades">–</b><span>Trades</span></div>
<div class="stat"><b id="sWr">–</b><span>Win Rate</span></div>
<div class="stat"><b id="sPnl">–</b><span>Total PnL</span></div></div>
<div class="card"><h2>Equity Curve</h2><svg id="spark" viewBox="0 0 100 30" preserveAspectRatio="none"></svg></div>
<h2>📡 Signal Scanner · Top 20 Volume · 4H</h2>
<div class="grid" id="scan"></div>
<p class="disc">⚠️ Sinyal teknikal informatif untuk monitoring. Berdasarkan riset 18 bulan, sinyal semacam ini tidak memiliki edge setelah biaya — jangan dieksekusi dengan dana asli.</p>
<h2>Trade Terakhir</h2><div class="card"><table><thead><tr><th>Waktu</th><th>Simbol</th><th>Exit</th><th>PnL</th></tr></thead><tbody id="recent"></tbody></table></div>
<footer><span id="err" style="color:#f87171"></span><span>⏱ <span id="clock"></span></span><span>auto-refresh 5s</span></footer>
</div><script>
const $=id=>document.getElementById(id);
const fmt=(n,d=2)=>n.toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});
function spark(v){if(!v||v.length<2){$('spark').innerHTML='';return}
const mn=Math.min(...v),mx=Math.max(...v),r=(mx-mn)||1;
const pts=v.map((x,i)=>`${i/(v.length-1)*100},${28-((x-mn)/r)*26}`).join(' ');
$('spark').innerHTML=`<polyline points="${pts}" fill="none" stroke="#34d399" stroke-width="1.2"/>`}
async function tick(){try{const d=await(await fetch('/api/data')).json();
$('clock').textContent=d.time;$('err').textContent=d.err?('⚠ '+d.err):'';$('mode').textContent=d.mode.toUpperCase();
const b=$('bot');b.textContent='BOT '+d.bot.toUpperCase();b.className='pill '+(d.bot==='active'?'ok':'bad');
$('coins').innerHTML=d.markets.map(m=>`<div class="card"><div class="row"><span class="sym">${m.symbol}</span><span class="badge ${m.regime}">${m.regime}</span></div><div class="price">$${fmt(m.price)}</div><div class="chg ${m.chg>=0?'up':'down'}">${m.chg>=0?'+':''}${fmt(m.chg)}% · 24h</div>${m.pos?`<div class="pos ${m.pos.pnl>=0?'up':'down'}">Posisi: ${m.pos.pnl>=0?'+':''}${fmt(m.pos.pnl)} USDT (${m.pos.pct>=0?'+':''}${fmt(m.pos.pct)}%)</div>`:''}</div>`).join('');
$('sTrades').textContent=d.perf.trades;$('sWr').textContent=d.perf.wr+'%';
const p=$('sPnl');p.textContent=(d.perf.pnl>=0?'+':'')+fmt(d.perf.pnl);p.className=d.perf.pnl>=0?'up':'down';
spark(d.perf.equity);
$('scan').innerHTML=d.signals.map(s=>`<div class="card"><div class="row"><span class="sym">${s.symbol}</span><span class="sig sig-${s.signal}">${s.signal}</span></div><div class="price" style="font-size:1.05rem">$${fmt(s.price)}</div><div class="chg ${s.chg>=0?'up':'down'}">${s.chg>=0?'+':''}${fmt(s.chg)}% · RSI ${s.rsi}</div></div>`).join('')||'<p class="disc">Memuat scanner…</p>';
$('recent').innerHTML=d.recent.map(r=>`<tr><td>${r.time}</td><td>${r.symbol}</td><td>${r.exit}</td><td class="${r.pnl>=0?'up':'down'}">${r.pnl>=0?'+':''}${fmt(r.pnl)}</td></tr>`).join('')||'<tr><td colspan=4>Belum ada trade</td></tr>';
}catch(e){}}
setInterval(tick,5000);tick();
</script></body></html>"""

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "":
            body = HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type","text/html; charset=utf-8")
        elif self.path.startswith("/api/data"):
            body = json.dumps(get_data()).encode()
            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.send_header("Cache-Control","no-store")
        else:
            self.send_response(404); self.end_headers(); return
        self.send_header("Content-Length",str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self,*a): pass

if __name__ == "__main__":
    print(f"Dashboard on :{PORT}")
    ThreadingHTTPServer(("0.0.0.0",PORT),H).serve_forever()
