import os
import streamlit as st
import pandas as pd
import numpy as np
import ccxt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

st.set_page_config(
    page_title="Crypto Trading Suite",
    layout="wide",
    page_icon="⬡",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
#  CSS GLOBAL
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=Space+Mono:wght@400;700&family=Bebas+Neue&display=swap');

html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
    background-color: #080c14;
    color: #e0e6f0;
}

.main-title {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 2.1rem;
    letter-spacing: -0.5px;
    background: linear-gradient(90deg, #00d4ff 0%, #7b5cf0 50%, #ff6b6b 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0;
}
.main-sub {
    font-family: 'Space Mono', monospace;
    font-size: 0.7rem;
    color: #4a6080;
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-top: 2px;
    margin-bottom: 16px;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background: transparent;
    border-bottom: 1px solid #1e2d45;
}
.stTabs [data-baseweb="tab"] {
    background: #0d1525 !important;
    border: 1px solid #1e3050 !important;
    border-radius: 6px 6px 0 0 !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.75rem !important;
    color: #6a8090 !important;
    padding: 10px 24px !important;
    letter-spacing: 2px !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(180deg, #0f1c2e 0%, #0a1525 100%) !important;
    border-color: #00d4ff !important;
    color: #00d4ff !important;
}

/* Cards */
.metric-card {
    background: linear-gradient(135deg, #0f1c2e 0%, #0a1525 100%);
    border: 1px solid #1e3050;
    border-radius: 12px;
    padding: 18px 22px;
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #00d4ff, #7b5cf0);
}
.metric-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.6rem;
    color: #4a6080;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.metric-value {
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 1.5rem;
    color: #e8f0ff;
    line-height: 1;
}
.metric-sub {
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem;
    color: #5a7088;
    margin-top: 4px;
}
.delta-up   { color: #00d4a0; }
.delta-down { color: #ff5c7a; }
.delta-mid  { color: #7b8fa8; }

/* Sinal box */
.signal-box {
    border-radius: 10px;
    padding: 16px 22px;
    border: 1px solid;
    margin-bottom: 8px;
}
.signal-buy   { background: linear-gradient(135deg, #001f1a 0%, #002e22 100%); border-color: #00c87a; }
.signal-sell  { background: linear-gradient(135deg, #1f0010 0%, #2e0018 100%); border-color: #ff3d6b; }
.signal-warn  { background: linear-gradient(135deg, #1a1500 0%, #2a2000 100%); border-color: #ffc300; }
.signal-flat  { background: linear-gradient(135deg, #0d1525 0%, #0a1020 100%); border-color: #2a4060; }

.signal-label {
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 1.4rem;
}

/* Section header */
.sec-header {
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem;
    color: #3a5070;
    letter-spacing: 3px;
    text-transform: uppercase;
    border-bottom: 1px solid #1e2d45;
    padding-bottom: 8px;
    margin: 20px 0 14px;
}

/* Tabela de níveis */
.nivel-table {
    background: #0a1525;
    border: 1px solid #1e2d45;
    border-radius: 8px;
    padding: 14px 18px;
    font-family: 'Space Mono', monospace;
    font-size: 0.72rem;
}
.nivel-row {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px solid #121e30;
}
.nivel-row:last-child { border-bottom: none; }
.nivel-key { color: #5a7088; }
.val-green  { color: #00d4a0; font-weight: 700; }
.val-red    { color: #ff5c7a; font-weight: 700; }
.val-yellow { color: #ffc300; font-weight: 700; }
.val-blue   { color: #4fc3f7; font-weight: 700; }

#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem; }

.stSelectbox > div > div {
    background: #0d1525 !important;
    border-color: #1e3050 !important;
    border-radius: 8px !important;
    font-family: 'Space Mono', monospace !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
#  CREDENCIAIS
# ─────────────────────────────────────────────────────────────
BITGET_API_KEY    = os.environ.get("BITGET_API_KEY",    "")
BITGET_SECRET_KEY = os.environ.get("BITGET_SECRET_KEY", "")
BITGET_PASSPHRASE = os.environ.get("BITGET_PASSPHRASE", "")

# ═════════════════════════════════════════════════════════════
#  CABEÇALHO
# ═════════════════════════════════════════════════════════════
st.markdown("""
<div class="main-title">⬡ Crypto Trading Suite</div>
<div class="main-sub">Senior Engine · DayTrade Engine · Real-Time Data</div>
""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════
#  TABS
# ═════════════════════════════════════════════════════════════
tab1, tab2 = st.tabs(["📊  SENIOR ENGINE (Médio/Longo Prazo)", "⚡  DAYTRADE ENGINE (Intradiário)"])

# ─────────────────────────────────────────────────────────────
#  HELPERS COMUNS
# ─────────────────────────────────────────────────────────────
def fmt(p):
    return f"${p:,.4f}" if p < 10 else f"${p:,.2f}"

def calcular_indicadores(df):
    df = df.copy()
    df['EMA9']   = df['close'].ewm(span=9,   adjust=False).mean()
    df['EMA20']  = df['close'].ewm(span=20,  adjust=False).mean()
    df['EMA21']  = df['close'].ewm(span=21,  adjust=False).mean()
    df['EMA50']  = df['close'].ewm(span=50,  adjust=False).mean()
    df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()
    df['Dist_Pct'] = ((df['EMA50']-df['EMA200'])/df['EMA200'])*100

    delta = df['close'].diff()
    up    = delta.clip(lower=0)
    down  = -delta.clip(upper=0)
    eu    = up.ewm(com=13, adjust=False).mean()
    ed    = down.ewm(com=13, adjust=False).mean()
    rs = np.where(ed==0, np.nan, eu/ed)
    df['RSI'] = np.where(ed==0, 100, 100-(100/(1+rs)))

    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD']      = ema12 - ema26
    df['MACD_Sig']  = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Sig']

    high, low, prev = df['high'], df['low'], df['close'].shift(1)
    tr = pd.concat([high-low,(high-prev).abs(),(low-prev).abs()], axis=1).max(axis=1)
    df['ATR'] = tr.ewm(com=13, adjust=False).mean()

    sma20 = df['close'].rolling(20).mean()
    std20 = df['close'].rolling(20).std()
    df['BB_up']  = sma20 + 2*std20
    df['BB_low'] = sma20 - 2*std20

    df['Vol_Rel'] = df['volume'] / df['volume'].rolling(20).mean()

    rec = df.tail(50)
    mx, mn = rec['high'].max(), rec['low'].min()
    rng = mx - mn
    df['Fib_382'] = mx - rng*0.382
    df['Fib_500'] = mx - rng*0.500
    df['Fib_618'] = mx - rng*0.618
    return df

# ═════════════════════════════════════════════════════════════
#  TAB 1 — CRYPTO SENIOR ENGINE
# ═════════════════════════════════════════════════════════════
with tab1:
    ATIVOS_SENIOR = {
        "Bitcoin (BTC)":        "BTC/USD",
        "Ethereum (ETH)":       "ETH/USD",
        "Solana (SOL)":         "SOL/USD",
        "XRP (XRP)":            "XRP/USD",
        "Chainlink (LINK)":     "LINK/USD",
        "Avalanche (AVAX)":     "AVAX/USD",
        "Cardano (ADA)":        "ADA/USD",
        "Polkadot (DOT)":       "DOT/USD",
        "Aave (AAVE)":          "AAVE/USD",
        "Near Protocol (NEAR)": "NEAR/USD",
        "Uniswap (UNI)":        "UNI/USD",
    }

    @st.cache_data(ttl=60)
    def buscar_senior(symbol):
        try:
            ex = ccxt.kraken({'enableRateLimit': True})
            bars = ex.fetch_ohlcv(symbol, timeframe='1d', limit=250)
            df = pd.DataFrame(bars, columns=['timestamp','open','high','low','close','volume'])
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('datetime', inplace=True)
            return df
        except Exception as e:
            st.error(f"Erro Kraken: {e}")
            return None

    col_sel, _ = st.columns([1, 2])
    with col_sel:
        ativo_s = st.selectbox("Ativo", list(ATIVOS_SENIOR.keys()),
                                 key="sel_senior", label_visibility="collapsed")

    with st.spinner("Sincronizando dados da Kraken..."):
        df_s = buscar_senior(ATIVOS_SENIOR[ativo_s])

    if df_s is not None:
        df_s = calcular_indicadores(df_s)
        atual    = df_s.iloc[-1]
        anterior = df_s.iloc[-2]
        preco    = float(atual['close'])
        rsi      = float(atual['RSI'])
        atr      = float(atual['ATR'])
        viés     = "BULL" if atual['EMA50'] > atual['EMA200'] else "BEAR"
        rec      = df_s.tail(100)
        fib618   = rec['high'].max() - (rec['high'].max()-rec['low'].min())*0.618
        fib500   = rec['high'].max() - (rec['high'].max()-rec['low'].min())*0.500

        sinal = "NEUTRO"
        cat   = "neutral"
        score = 0
        if viés == "BULL":
            score += 1
        else:
            score -= 1
        if rsi < 35:
            score += 2
        elif rsi < 45:
            score += 1
        elif rsi > 72:
            score -= 2
        if atual['MACD_Hist'] > 0 and anterior['MACD_Hist'] <= 0:
            score += 2

        if (atual['EMA50'] < atual['EMA200']
                and atual['Dist_Pct'] > anterior['Dist_Pct']
                and atual['Dist_Pct'] > -5
                and rsi < 35 and preco <= fib618*1.02):
            sinal = "COMPRA FORTE"
            cat = "buy"
        elif atual['EMA50'] > atual['EMA200'] and rsi < 45 and preco <= fib500*1.01:
            sinal = "COMPRA"
            cat = "buy"
        elif (preco < atual['EMA20'] and anterior['close'] > anterior['EMA20'] and rsi > 65):
            sinal = "VENDA"
            cat = "sell"
        elif rsi > 72:
            sinal = "ATENÇÃO"
            cat = "warn"

        # Cards
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""<div class="metric-card">
            <div class="metric-label">Preço Atual</div>
            <div class="metric-value">{fmt(preco)}</div>
            <div class="metric-sub">USD · Kraken</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            cor_rsi = "delta-up" if rsi<40 else ("delta-down" if rsi>70 else "delta-mid")
            st.markdown(f"""<div class="metric-card">
            <div class="metric-label">RSI (14)</div>
            <div class="metric-value">{rsi:.1f}</div>
            <div class="metric-sub {cor_rsi}">{'Sobrevenda' if rsi<40 else 'Sobrecompra' if rsi>70 else 'Neutro'}</div>
            </div>""", unsafe_allow_html=True)
        with c3:
            cor_v = "delta-up" if viés == "BULL" else "delta-down"
            st.markdown(f"""<div class="metric-card">
            <div class="metric-label">Viés Macro</div>
            <div class="metric-value" style="font-size:1.3rem">{'📈 BULL' if viés=='BULL' else '📉 BEAR'}</div>
            <div class="metric-sub {cor_v}">{atual['Dist_Pct']:+.1f}%</div>
            </div>""", unsafe_allow_html=True)
        with c4:
            cor_m = "delta-up" if atual['MACD_Hist'] > 0 else "delta-down"
            st.markdown(f"""<div class="metric-card">
            <div class="metric-label">MACD Hist</div>
            <div class="metric-value" style="font-size:1.3rem">{atual['MACD_Hist']:+.4f}</div>
            <div class="metric-sub {cor_m}">{'Momentum ↑' if atual['MACD_Hist']>0 else 'Momentum ↓'}</div>
            </div>""", unsafe_allow_html=True)

        # Sinal
        st.markdown('<div class="sec-header">◈ SINAL DO MODELO</div>', unsafe_allow_html=True)
        cls = {"buy":"signal-buy","sell":"signal-sell","warn":"signal-warn","neutral":"signal-flat"}[cat]
        cor = {"buy":"#00d4a0","sell":"#ff5c7a","warn":"#ffc300","neutral":"#5a7088"}[cat]
        st.markdown(f"""<div class="signal-box {cls}">
        <div class="signal-label" style="color:{cor}">{sinal}</div>
        <div style="font-family:'Space Mono',monospace;font-size:0.65rem;color:#5a7088;margin-top:6px">
        EMA9: {fmt(atual['EMA9'])} · EMA50: {fmt(atual['EMA50'])} · EMA200: {fmt(atual['EMA200'])}
        </div>
        </div>""", unsafe_allow_html=True)

        # Gráfico
        st.markdown('<div class="sec-header">◈ ANÁLISE GRÁFICA</div>', unsafe_allow_html=True)
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            row_heights=[0.7, 0.3], vertical_spacing=0.04)
        fig.add_trace(go.Candlestick(x=df_s.index,
            open=df_s['open'], high=df_s['high'], low=df_s['low'], close=df_s['close'],
            increasing_line_color="#00d4a0", increasing_fillcolor="#003322",
            decreasing_line_color="#ff5c7a", decreasing_fillcolor="#330011",
            name="Preço"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_s.index, y=df_s['EMA50'], name="EMA50",
            line=dict(color="#4fc3f7", width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_s.index, y=df_s['EMA200'], name="EMA200",
            line=dict(color="#bf80ff", width=2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_s.index, y=df_s['RSI'], name="RSI",
            line=dict(color="#7b5cf0", width=1.5)), row=2, col=1)
        fig.add_hline(y=70, line=dict(color="#ff5c7a", width=0.7, dash="dot"), row=2, col=1)
        fig.add_hline(y=30, line=dict(color="#00d4a0", width=0.7, dash="dot"), row=2, col=1)

        fig.update_layout(height=550, template="plotly_dark",
            paper_bgcolor="#080c14", plot_bgcolor="#0a1020",
            font=dict(family="Space Mono", size=9, color="#5a7088"),
            legend=dict(orientation="h", y=1.02, x=0, bgcolor="rgba(0,0,0,0)"),
            margin=dict(l=10, r=20, t=20, b=10),
            xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

# ═════════════════════════════════════════════════════════════
#  TAB 2 — DAYTRADE ENGINE
# ═════════════════════════════════════════════════════════════
with tab2:
    if not BITGET_API_KEY:
        st.warning("⚠️ Credenciais Bitget não configuradas. Configure as variáveis de ambiente: BITGET_API_KEY, BITGET_SECRET_KEY, BITGET_PASSPHRASE")
    else:
        ATIVOS_DAYTRADE = {
            "COPPER — Cobre (1h)": {
                "symbol": "COPPER/USDT:USDT", "tf": "1h",
                "atr_stop": 1.0, "atr_tp1": 2.0, "atr_tp2": 3.0,
                "rsi_min": 50, "rsi_max": 60, "vol_fator": 1.0,
                "cor": "#00d4a0",
            },
            "XAU — Ouro (1h)": {
                "symbol": "XAU/USDT:USDT", "tf": "1h",
                "atr_stop": 1.0, "atr_tp1": 1.5, "atr_tp2": 4.0,
                "rsi_min": 45, "rsi_max": 65, "vol_fator": 1.2,
                "cor": "#ffc300",
            },
            "PENDLE — DeFi (15m)": {
                "symbol": "PENDLE/USDT:USDT", "tf": "15m",
                "atr_stop": 1.0, "atr_tp1": 1.5, "atr_tp2": 5.0,
                "rsi_min": 40, "rsi_max": 60, "vol_fator": 1.5,
                "cor": "#4fc3f7",
            },
        }

        @st.cache_data(ttl=60)
        def buscar_daytrade(symbol, tf):
            try:
                ex = ccxt.bitget({
                    'apiKey': BITGET_API_KEY, 'secret': BITGET_SECRET_KEY,
                    'password': BITGET_PASSPHRASE, 'enableRateLimit': True,
                    'options': {'defaultType': 'swap'}
                })
                bars = ex.fetch_ohlcv(symbol, timeframe=tf, limit=300)
                df = pd.DataFrame(bars, columns=['timestamp','open','high','low','close','volume'])
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('datetime', inplace=True)
                return df
            except Exception as e:
                st.error(f"Erro Bitget: {e}")
                return None

        col_sel2, _ = st.columns([1, 2])
        with col_sel2:
            ativo_d = st.selectbox("Ativo", list(ATIVOS_DAYTRADE.keys()),
                                    key="sel_daytrade", label_visibility="collapsed")

        cfg = ATIVOS_DAYTRADE[ativo_d]
        with st.spinner("Sincronizando com Bitget Futuros..."):
            df_d = buscar_daytrade(cfg['symbol'], cfg['tf'])

        if df_d is not None:
            df_d = calcular_indicadores(df_d)
            r  = df_d.iloc[-1]
            preco = float(r['close'])
            rsi   = float(r['RSI'])
            atr   = float(r['ATR'])

            tl = r['EMA9']>r['EMA21'] and r['close']>r['EMA200']
            ts = r['EMA9']<r['EMA21'] and r['close']<r['EMA200']
            rl = cfg['rsi_min']<=rsi<=cfg['rsi_max']
            rs_s = (100-cfg['rsi_max'])<=rsi<=(100-cfg['rsi_min'])
            ml = r['MACD_Hist']>0
            ms = r['MACD_Hist']<0
            vol = r['Vol_Rel']>=cfg['vol_fator']

            if tl and rl and ml and vol:
                sinal = "LONG"
                stop = preco - atr*cfg['atr_stop']
                tp1  = preco + atr*cfg['atr_tp1']
                tp2  = preco + atr*cfg['atr_tp2']
                cat = "buy"; cor = "#00d4a0"
            elif ts and rs_s and ms and vol:
                sinal = "SHORT"
                stop = preco + atr*cfg['atr_stop']
                tp1  = preco - atr*cfg['atr_tp1']
                tp2  = preco - atr*cfg['atr_tp2']
                cat = "sell"; cor = "#ff5c7a"
            else:
                sinal = "FLAT"
                stop = tp1 = tp2 = 0
                cat = "neutral"; cor = "#5a7088"

            # KPIs
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.markdown(f"""<div class="metric-card">
                <div class="metric-label">Preço Atual</div>
                <div class="metric-value">{fmt(preco)}</div>
                <div class="metric-sub">{cfg['symbol']} · {cfg['tf']}</div>
                </div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""<div class="metric-card">
                <div class="metric-label">RSI (14)</div>
                <div class="metric-value">{rsi:.1f}</div>
                <div class="metric-sub">Zona: {cfg['rsi_min']}-{cfg['rsi_max']}</div>
                </div>""", unsafe_allow_html=True)
            with c3:
                viés_d = "BULL" if r['EMA9'] > r['EMA21'] else "BEAR"
                st.markdown(f"""<div class="metric-card">
                <div class="metric-label">Viés (EMA9 vs 21)</div>
                <div class="metric-value" style="font-size:1.3rem">{'📈 ' + viés_d if viés_d=='BULL' else '📉 ' + viés_d}</div>
                <div class="metric-sub">EMA9: {fmt(r['EMA9'])}</div>
                </div>""", unsafe_allow_html=True)
            with c4:
                st.markdown(f"""<div class="metric-card">
                <div class="metric-label">Volume / Média</div>
                <div class="metric-value">{r['Vol_Rel']:.2f}x</div>
                <div class="metric-sub">Mín: {cfg['vol_fator']}x</div>
                </div>""", unsafe_allow_html=True)
            with c5:
                st.markdown(f"""<div class="metric-card">
                <div class="metric-label">ATR</div>
                <div class="metric-value">{fmt(atr)}</div>
                <div class="metric-sub">{(atr/preco*100):.2f}% / candle</div>
                </div>""", unsafe_allow_html=True)

            # Sinal + Níveis
            col_s, col_n = st.columns(2)
            with col_s:
                st.markdown('<div class="sec-header">◈ SINAL OTIMIZADO</div>', unsafe_allow_html=True)
                cls = {"buy":"signal-buy","sell":"signal-sell","neutral":"signal-flat"}[cat]
                st.markdown(f"""<div class="signal-box {cls}">
                <div class="signal-label" style="color:{cor}">{sinal}</div>
                <div style="font-family:'Space Mono',monospace;font-size:0.65rem;color:#5a7088;margin-top:8px">
                Parâmetros: ATR_SL {cfg['atr_stop']}x · TP1 {cfg['atr_tp1']}x · TP2 {cfg['atr_tp2']}x<br>
                RSI {cfg['rsi_min']}-{cfg['rsi_max']} · Vol mín {cfg['vol_fator']}x
                </div>
                </div>""", unsafe_allow_html=True)

            with col_n:
                st.markdown('<div class="sec-header">◈ NÍVEIS DE OPERAÇÃO</div>', unsafe_allow_html=True)
                if sinal in ["LONG","SHORT"]:
                    rr = abs(tp2-preco)/abs(stop-preco)
                    st.markdown(f"""<div class="nivel-table">
                    <div class="nivel-row"><span class="nivel-key">🔴 Stop Loss</span><span class="val-red">{fmt(stop)}</span></div>
                    <div class="nivel-row"><span class="nivel-key">🟡 TP1 (50%)</span><span class="val-yellow">{fmt(tp1)}</span></div>
                    <div class="nivel-row"><span class="nivel-key">🟢 TP2 (100%)</span><span class="val-green">{fmt(tp2)}</span></div>
                    <div class="nivel-row"><span class="nivel-key">📊 Relação R/R</span><span class="val-blue">{rr:.2f}x</span></div>
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""<div class="nivel-table">
                    <div style="font-size:0.7rem;color:#3a5070;padding:14px 0;text-align:center">
                    Aguardando sinal de entrada<br>para calcular níveis
                    </div>
                    </div>""", unsafe_allow_html=True)

            # Gráfico
            st.markdown('<div class="sec-header">◈ ANÁLISE GRÁFICA</div>', unsafe_allow_html=True)
            fig2 = make_subplots(rows=3, cols=1, shared_xaxes=True,
                                  row_heights=[0.6, 0.2, 0.2], vertical_spacing=0.04)

            fig2.add_trace(go.Candlestick(x=df_d.index,
                open=df_d['open'], high=df_d['high'], low=df_d['low'], close=df_d['close'],
                increasing_line_color="#00d4a0", increasing_fillcolor="#003322",
                decreasing_line_color="#ff5c7a", decreasing_fillcolor="#330011",
                name="Preço"), row=1, col=1)
            fig2.add_trace(go.Scatter(x=df_d.index, y=df_d['EMA9'], name="EMA9",
                line=dict(color="#ffc300", width=1)), row=1, col=1)
            fig2.add_trace(go.Scatter(x=df_d.index, y=df_d['EMA21'], name="EMA21",
                line=dict(color="#4fc3f7", width=1.5)), row=1, col=1)
            fig2.add_trace(go.Scatter(x=df_d.index, y=df_d['EMA200'], name="EMA200",
                line=dict(color="#bf80ff", width=2)), row=1, col=1)

            if sinal in ["LONG","SHORT"]:
                fig2.add_hline(y=stop, line=dict(color="#ff5c7a", width=1, dash="dash"),
                    annotation_text="SL", row=1, col=1)
                fig2.add_hline(y=tp1, line=dict(color="#ffc300", width=1, dash="dash"),
                    annotation_text="TP1", row=1, col=1)
                fig2.add_hline(y=tp2, line=dict(color="#00d4a0", width=1, dash="dash"),
                    annotation_text="TP2", row=1, col=1)

            fig2.add_trace(go.Scatter(x=df_d.index, y=df_d['RSI'], name="RSI",
                line=dict(color=cfg['cor'], width=1.5)), row=2, col=1)
            fig2.add_hline(y=cfg['rsi_max'], line=dict(color="#ff5c7a", width=0.7, dash="dot"), row=2, col=1)
            fig2.add_hline(y=cfg['rsi_min'], line=dict(color="#00d4a0", width=0.7, dash="dot"), row=2, col=1)

            colors_h = ["#00d4a0" if v>=0 else "#ff5c7a" for v in df_d['MACD_Hist']]
            fig2.add_trace(go.Bar(x=df_d.index, y=df_d['MACD_Hist'],
                marker_color=colors_h, name="MACD Hist"), row=3, col=1)

            fig2.update_layout(height=650, template="plotly_dark",
                paper_bgcolor="#080c14", plot_bgcolor="#0a1020",
                font=dict(family="Space Mono", size=9, color="#5a7088"),
                legend=dict(orientation="h", y=1.02, x=0, bgcolor="rgba(0,0,0,0)"),
                margin=dict(l=10, r=20, t=20, b=10),
                xaxis_rangeslider_visible=False,
                yaxis2=dict(range=[0,100]))
            st.plotly_chart(fig2, use_container_width=True)

# ─────────────────────────────────────────────────────────────
#  RODAPÉ
# ─────────────────────────────────────────────────────────────
st.markdown(f"""<div style="text-align:center;font-family:'Space Mono',monospace;
font-size:0.6rem;color:#1e3050;padding:16px;border-top:1px solid #0e1e30;margin-top:20px">
⬡ CRYPTO TRADING SUITE · Senior + DayTrade · Cache 60s ·
{datetime.now().strftime('%d/%m/%Y %H:%M:%S')} BRT ·
<span style="color:#ff3d6b">Não constitui recomendação de investimento.</span>
</div>""", unsafe_allow_html=True)
