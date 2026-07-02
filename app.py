import streamlit as st
import pandas as pd
import ccxt
import plotly.graph_objects as go

from engine import CryptoEngine

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Crypto Senior Engine v2", layout="wide", page_icon="📈")
st.title("📈 Crypto Senior Analyst — Dashboard em Tempo Real")
st.markdown("---")

# --- LISTA DE ATIVOS ---
ATIVOS = {
    "Bitcoin (BTC)":        "BTC/USDT",
    "Ethereum (ETH)":       "ETH/USDT",
    "Solana (SOL)":         "SOL/USDT",
    "XRP (XRP)":            "XRP/USDT",
    "Chainlink (LINK)":     "LINK/USDT",
    "Pendle (PENDLE)":      "PENDLE/USDT",
    "Avalanche (AVAX)":     "AVAX/USDT",
    "Cardano (ADA)":        "ADA/USDT",
    "Polkadot (DOT)":       "DOT/USDT",
    "Render (RENDER)":      "RENDER/USDT",
    "Aave (AAVE)":          "AAVE/USDT",
    "Ethena (ENA)":         "ENA/USDT",
    "Near Protocol (NEAR)": "NEAR/USDT",
    "Uniswap (UNI)":        "UNI/USDT",
    "Stacks (STX)":         "STX/USDT",
}

# --- BUSCA DE DADOS (cache de 60s) ---
@st.cache_data(ttl=60)
def buscar_dados(symbol: str) -> pd.DataFrame | None:
    try:
        exchange = ccxt.bybit({'enableRateLimit': True})
        bars = exchange.fetch_ohlcv(symbol, timeframe='1d', limit=250)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['Date'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('Date', inplace=True)
        return df
    except Exception as e:
        st.error(f"Erro na API para {symbol}: {e}")
        return None

# --- SIDEBAR ---
st.sidebar.header("Painel de Controle")
ativo_selecionado = st.sidebar.selectbox("Escolha o Ativo:", list(ATIVOS.keys()))
ticker_api = ATIVOS[ativo_selecionado]

# --- ANÁLISE ---
df = buscar_dados(ticker_api)

if df is not None:
    engine = CryptoEngine(df)
    sinal, cor, vies, preco, rsi, macd_hist, ultimo, detalhe = engine.gerar_sinal()
    df_completo = engine.df

    # --- MÉTRICAS ---
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Preço Atual (USDT)", f"$ {preco:,.4f}")
    col2.metric("RSI (14d)", f"{rsi:.2f}")
    col3.metric("MACD Hist", f"{macd_hist:.4f}")
    col4.metric("Viés Macro", vies)

    with col5:
        st.markdown("**Sinal do Modelo:**")
        if cor == "green":    st.success(sinal)
        elif cor == "orange": st.warning(sinal)
        elif cor == "red":    st.error(sinal)
        else:                 st.info(sinal)

    if detalhe:
        st.caption(f"📌 {detalhe}")

    # --- GRÁFICO ---
    st.subheader(f"Análise Gráfica — {ativo_selecionado}")
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df_completo.index,
        open=df_completo['open'], high=df_completo['high'],
        low=df_completo['low'],   close=df_completo['close'],
        name="Preço"
    ))
    fig.add_trace(go.Scatter(x=df_completo.index, y=df_completo['EMA_20'],
        name="EMA 20 (Trailing Stop)", line=dict(color='orange', width=1, dash='dot')))
    fig.add_trace(go.Scatter(x=df_completo.index, y=df_completo['EMA_50'],
        name="EMA 50", line=dict(color='blue', width=1.5)))
    fig.add_trace(go.Scatter(x=df_completo.index, y=df_completo['EMA_200'],
        name="EMA 200 (Suporte Macro)", line=dict(color='purple', width=2)))
    fig.add_trace(go.Scatter(x=df_completo.index, y=df_completo['Fib_50.0'],
        name="Fib 50%", line=dict(color='gold', width=1, dash='dash')))
    fig.add_trace(go.Scatter(x=df_completo.index, y=df_completo['Fib_61.8'],
        name="Fib 61.8%", line=dict(color='tomato', width=1, dash='dash')))

    fig.update_layout(
        xaxis_rangeslider_visible=False,
        height=520,
        template="plotly_dark",
        margin=dict(l=20, r=20, t=20, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- TABELA ---
    st.subheader("Histórico Recente de Indicadores")
    st.dataframe(
        df_completo[['close', 'EMA_20', 'EMA_50', 'EMA_200', 'RSI', 'MACD', 'MACD_Signal', 'Volume_OK']].tail(10),
        use_container_width=True
    )
