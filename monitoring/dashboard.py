"""Modern live dashboard donal-bot-pro.

Auto-refresh 10 detik, modern UI dengan cards, badges, dan styling.
"""
import glob, json, os, sqlite3, subprocess, sys, time
import pandas as pd
import requests
import streamlit as st
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
DB = os.path.join(BASE, "data", "trades.db")

from core.config_loader import ConfigLoader
from strategies.regime_detector import detect_regime

# Custom CSS untuk modern look
st.markdown("""
<style>
    .stMetric {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    .stMetric label {
        color: rgba(255,255,255,0.8);
    }
    .regime-badge {
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-weight: 600;
        display: inline-block;
    }
    .regime-trend { background: #10b981; color: white; }
    .regime-sideways { background: #f59e0b; color: white; }
    .regime-bear { background: #ef4444; color: white; }
    .pnl-positive { color: #10b981; font-weight: 700; }
    .pnl-negative { color: #ef4444; font-weight: 700; }
    .status-active { color: #10b981; font-weight: 700; }
    .status-inactive { color: #ef4444; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

st.set_page_config(page_title="Donal Bot Pro", layout="wide", page_icon="🤖")

# Header
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.title("🤖 Donal Bot Pro")
    st.caption("Automated Trading System")
with col2:
    st.metric("Mode", "TESTNET" if "testnet" in BASE.lower() else "LIVE", delta=None)
with col3:
    if st.button("🔄 Refresh Now", use_container_width=True):
        st.rerun()

# Load config
@st.cache_data(ttl=300)
def load_cfg():
    return ConfigLoader(os.path.join(BASE, "config.yaml")).load()

CFG = load_cfg()
SYMBOLS = CFG["trading"]["symbols"]

# Helper functions
def svc_status(name):
    try:
        result = subprocess.run(["systemctl", "is-active", name],
                              capture_output=True, text=True, timeout=2)
        return result.stdout.strip()
    except:
        return "unknown"

def col(df, *names):
    for n in names:
        if n in df.columns:
            return n
    return None

def query(sql):
    try:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=5)
        return pd.read_sql(sql, con)
    except:
        return pd.DataFrame()

@st.cache_data(ttl=8)
def fetch_tickers():
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/24hr",
                        params={"symbols": json.dumps(SYMBOLS)}, timeout=5)
        return {x["symbol"]: x for x in r.json()}
    except:
        return {}

@st.cache_data(ttl=60)
def fetch_regime(sym):
    try:
        r = requests.get("https://api.binance.com/api/v3/klines",
                        params={"symbol": sym, "interval": "4h", "limit": 120}, timeout=5)
        k = r.json()
        cols = ["open_time","open","high","low","close","volume","close_time",
                "qvol","trades","tb","tq","ignore"]
        df = pd.DataFrame(k, columns=cols)
        for c in ["open","high","low","close","volume"]:
            df[c] = df[c].astype(float)
        regime = detect_regime(df).mode.value
        return regime
    except:
        return "?"

REGIME_STYLES = {
    "TREND": ("regime-trend", "🟢"),
    "SIDEWAYS": ("regime-sideways", "🟡"),
    "BEAR": ("regime-bear", "🔴"),
    "TRANSITION": ("regime-sideways", "🟠"),
}

# Status bar
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)
with col1:
    bot_status = svc_status("donal-bot-pro")
    status_class = "status-active" if bot_status == "active" else "status-inactive"
    st.markdown(f"**Bot Service:** <span class='{status_class}'>{bot_status.upper()}</span>", unsafe_allow_html=True)
with col2:
    dash_status = svc_status("donal-dashboard")
    status_class = "status-active" if dash_status == "active" else "status-inactive"
    st.markdown(f"**Dashboard:** <span class='{status_class}'>{dash_status.upper()}</span>", unsafe_allow_html=True)
with col3:
    st.markdown(f"**Simbol Aktif:** {len(SYMBOLS)}")
with col4:
    st.markdown(f"**Last Update:** {datetime.now().strftime('%H:%M:%S')}")

# Market data
st.markdown("---")
st.subheader("📊 Market Live")

tickers = fetch_tickers()
state_df = query("SELECT * FROM state")
ip_col = col(state_df, "in_position")
open_positions = {}
if not state_df.empty and ip_col:
    open_pos = state_df[state_df[ip_col].astype(int) == 1]
    if not open_pos.empty:
        for _, p in open_pos.iterrows():
            open_positions[p.get("symbol", "")] = p

# Market table
rows = []
for sym in SYMBOLS:
    t = tickers.get(sym, {})
    price = float(t.get("lastPrice", 0) or 0)
    chg = float(t.get("priceChangePercent", 0) or 0)
    reg = fetch_regime(sym)
    reg_class, reg_icon = REGIME_STYLES.get(reg, ("", "❓"))
    
    # Position info
    pos = open_positions.get(sym)
    if pos is not None:
        entry = float(pos.get("entry_price", 0) or 0)
        qty = float(pos.get("qty", 0) or 0)
        pnl = (price - entry) * qty if price and entry else 0
        pnl_pct = (price - entry) / entry * 100 if price and entry else 0
        pnl_class = "pnl-positive" if pnl >= 0 else "pnl-negative"
        pos_str = f'<span class="{pnl_class}">{pnl:+.2f} USDT ({pnl_pct:+.2f}%)</span>'
    else:
        pos_str = "—"
    
    rows.append({
        "Simbol": sym,
        "Harga": f"${price:,.2f}",
        "24h": f"{chg:+.2f}%",
        "Regime": f'<span class="regime-badge {reg_class}">{reg_icon} {reg}</span>',
        "Posisi": pos_str
    })

df_market = pd.DataFrame(rows)
st.markdown(df_market.to_html(escape=False, index=False), unsafe_allow_html=True)

# Performance metrics
st.markdown("---")
st.subheader("📈 Performance")

trades_df = query("SELECT * FROM trades")
if not trades_df.empty:
    tcol = col(trades_df, "exit_time", "close_time", "time")
    pcol = col(trades_df, "pnl_usdt", "pnl")
    
    if tcol and pcol:
        trades_df[tcol] = pd.to_datetime(trades_df[tcol], errors="coerce")
        trades_df[pcol] = pd.to_numeric(trades_df[pcol], errors="coerce")
        trades_df = trades_df.sort_values(tcol)
        
        wins = trades_df[trades_df[pcol] > 0]
        losses = trades_df[trades_df[pcol] <= 0]
        total_pnl = trades_df[pcol].sum()
        avg_win = wins[pcol].mean() if len(wins) > 0 else 0
        avg_loss = losses[pcol].mean() if len(losses) > 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Trades", len(trades_df))
        with col2:
            wr = len(wins) / len(trades_df) * 100 if len(trades_df) > 0 else 0
            st.metric("Win Rate", f"{wr:.1f}%")
        with col3:
            pnl_class = "pnl-positive" if total_pnl >= 0 else "pnl-negative"
            st.markdown(f"**Total PnL:** <span class='{pnl_class}'>{total_pnl:+.2f} USDT</span>", unsafe_allow_html=True)
        with col4:
            st.metric("Profit Factor", f"{abs(wins[pcol].sum() / losses[pcol].sum()):.2f}" if len(losses) > 0 and losses[pcol].sum() != 0 else "∞")
        
        # Equity curve
        eq = trades_df[[tcol, pcol]].copy()
        eq["cum"] = eq[pcol].cumsum()
        eq["dd"] = eq["cum"] - eq["cum"].cummax()
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Equity Curve")
            st.line_chart(eq.set_index(tcol)["cum"])
        with col2:
            st.subheader("Drawdown")
            st.area_chart(eq.set_index(tcol)["dd"], color="#ef4444")
        
        # Recent trades
        st.subheader("🕒 Recent Trades")
        recent = trades_df.tail(10).iloc[::-1]
        st.dataframe(recent, use_container_width=True)
else:
    st.info("Belum ada trade tertutup. Data akan muncul setelah bot closing posisi.")

# Log section
with st.expander("📜 System Logs (20 baris terakhir)"):
    logs = sorted(glob.glob(os.path.join(BASE, "logs", "*.log")), key=os.path.getmtime)
    if logs:
        log_content = "".join(open(logs[-1]).readlines()[-20:])
        st.code(log_content)
    else:
        st.info("File log tidak ditemukan.")

# Auto-refresh
time.sleep(10)
st.rerun()
