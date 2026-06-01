import os
import time
import json
import threading
import urllib.request
from datetime import datetime
import numpy as np
import pandas as pd
import ccxt

# ==================== CONFIGURAÇÃO VIA VARIÁVEIS DE AMBIENTE ====================
TELEGRAM_TOKEN    = os.environ.get("TELEGRAM_TOKEN",    "")
TELEGRAM_CHAT_ID  = os.environ.get("TELEGRAM_CHAT_ID",  "")
BITGET_API_KEY    = os.environ.get("BITGET_API_KEY",    "")
BITGET_SECRET_KEY = os.environ.get("BITGET_SECRET_KEY", "")
BITGET_PASSPHRASE = os.environ.get("BITGET_PASSPHRASE", "")
# =================================================================================

# ─────────────────────────────────────────────────────────────
#  PROJETO 1 — CRYPTO SENIOR ENGINE
#  Portfólio cripto · Timeframe 1d · Kraken
# ─────────────────────────────────────────────────────────────
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

# ─────────────────────────────────────────────────────────────
#  PROJETO 2 — DAYTRADE ENGINE
#  Ativos aprovados · Parâmetros otimizados · Bitget Futuros
# ─────────────────────────────────────────────────────────────
ATIVOS_DAYTRADE = [
    {
        "nome": "COPPER (Cobre)", "symbol": "COPPER/USDT:USDT",
        "timeframe": "1h", "limite": 300,
        "atr_stop": 1.0, "atr_tp1": 2.0, "atr_tp2": 3.0,
        "rsi_min": 50, "rsi_max": 60, "vol_fator": 1.0,
        "emoji": "🔶",
    },
    {
        "nome": "XAU (Ouro)", "symbol": "XAU/USDT:USDT",
        "timeframe": "1h", "limite": 300,
        "atr_stop": 1.0, "atr_tp1": 1.5, "atr_tp2": 4.0,
        "rsi_min": 45, "rsi_max": 65, "vol_fator": 1.2,
        "emoji": "🥇",
    },
    {
        "nome": "PENDLE (DeFi)", "symbol": "PENDLE/USDT:USDT",
        "timeframe": "15m", "limite": 300,
        "atr_stop": 1.0, "atr_tp1": 1.5, "atr_tp2": 5.0,
        "rsi_min": 40, "rsi_max": 60, "vol_fator": 1.5,
        "emoji": "🔵",
    },
]

# ─────────────────────────────────────────────────────────────
#  ENVIO TELEGRAM
# ─────────────────────────────────────────────────────────────
def enviar_telegram(mensagem):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[ERRO] Credenciais Telegram ausentes")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem,
        "parse_mode": "Markdown"
    }).encode("utf-8")
    try:
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode()).get("ok", False)
    except Exception as e:
        print(f"[ERRO Telegram] {e}")
        return False

# ─────────────────────────────────────────────────────────────
#  INDICADORES COMPARTILHADOS
# ─────────────────────────────────────────────────────────────
def calcular_indicadores(df):
    df = df.copy()
    df['EMA9']   = df['close'].ewm(span=9,   adjust=False).mean()
    df['EMA20']  = df['close'].ewm(span=20,  adjust=False).mean()
    df['EMA21']  = df['close'].ewm(span=21,  adjust=False).mean()
    df['EMA50']  = df['close'].ewm(span=50,  adjust=False).mean()
    df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()
    df['Dist_Pct'] = ((df['EMA50'] - df['EMA200']) / df['EMA200']) * 100

    delta    = df['close'].diff()
    up       = delta.clip(lower=0)
    down     = -delta.clip(upper=0)
    ema_up   = up.ewm(com=13,   adjust=False).mean()
    ema_down = down.ewm(com=13, adjust=False).mean()
    rs = np.where(ema_down==0, np.nan, ema_up/ema_down)
    df['RSI'] = np.where(ema_down==0, 100, 100-(100/(1+rs)))

    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD_Hist'] = (ema12-ema26) - (ema12-ema26).ewm(span=9, adjust=False).mean()

    high, low, prev = df['high'], df['low'], df['close'].shift(1)
    tr = pd.concat([high-low,(high-prev).abs(),(low-prev).abs()], axis=1).max(axis=1)
    df['ATR'] = tr.ewm(com=13, adjust=False).mean()

    df['Vol_Rel'] = df['volume'] / df['volume'].rolling(20).mean()
    return df

# ─────────────────────────────────────────────────────────────
#  ROBÔ 1 — SENIOR (1d Kraken)
# ─────────────────────────────────────────────────────────────
def sinal_senior(df):
    df = calcular_indicadores(df)
    atual    = df.iloc[-1]
    anterior = df.iloc[-2]
    preco    = float(atual['close'])
    rsi      = atual['RSI']

    rec    = df.tail(100)
    mx, mn = rec['high'].max(), rec['low'].min()
    diff   = mx - mn
    fib618 = mx - diff * 0.618
    fib500 = mx - diff * 0.500

    sinal = "Neutro"
    if (atual['EMA50'] < atual['EMA200']
            and atual['Dist_Pct'] > anterior['Dist_Pct']
            and atual['Dist_Pct'] > -5):
        if rsi < 35 and preco <= fib618 * 1.02:
            sinal = "COMPRA (Antecipacao Golden Cross)"
    elif atual['EMA50'] > atual['EMA200']:
        if rsi < 45 and preco <= fib500 * 1.01:
            sinal = "COMPRA (Retracao em Bull Market)"

    if (preco < atual['EMA20']
            and anterior['close'] > anterior['EMA20']
            and rsi > 65):
        sinal = "VENDA (Quebra de Media 20)"

    return sinal, preco, rsi

def robo_senior():
    exchange = ccxt.kraken({'enableRateLimit': True})
    historico = {nome: "Neutro" for nome in ATIVOS_SENIOR.keys()}

    print("[SENIOR] Robô iniciado")
    enviar_telegram(
        "📊 *Crypto Senior Engine Ativado!*\n"
        "Monitoramento diário de 11 criptos via Kraken."
    )

    while True:
        agora = datetime.now().strftime('%H:%M:%S')
        print(f"[SENIOR][{agora}] Varrendo portfólio cripto...")

        for nome, symbol in ATIVOS_SENIOR.items():
            try:
                bars = exchange.fetch_ohlcv(symbol, timeframe='1d', limit=250)
                df   = pd.DataFrame(bars, columns=['timestamp','open','high','low','close','volume'])
                sinal, preco, rsi = sinal_senior(df)

                if sinal != historico[nome] and sinal != "Neutro":
                    emoji = "🟢" if "COMPRA" in sinal else "🔴"
                    enviar_telegram(
                        f"{emoji} *{nome}*\n\n"
                        f"*Sinal:* {sinal}\n"
                        f"*Preço:* ${preco:,.4f}\n"
                        f"*RSI:* {rsi:.2f}\n"
                        f"*Horário:* {datetime.now().strftime('%d/%m %H:%M')}\n\n"
                        f"_Acesse sua corretora para gerenciar o risco._"
                    )
                    print(f"[SENIOR] ALERTA: {nome} — {sinal}")

                historico[nome] = sinal
                time.sleep(1)
            except Exception as e:
                print(f"[SENIOR] Erro em {nome}: {e}")

        print(f"[SENIOR] Próxima varredura em 1 hora")
        time.sleep(3600)

# ─────────────────────────────────────────────────────────────
#  ROBÔ 2 — DAYTRADE (Bitget Futuros)
# ─────────────────────────────────────────────────────────────
def sinal_daytrade(df, cfg):
    df = calcular_indicadores(df)
    r  = df.iloc[-1]
    preco = float(r['close'])
    rsi   = float(r['RSI'])
    atr   = float(r['ATR'])

    tl = r['EMA9'] > r['EMA21'] and r['close'] > r['EMA200']
    ts = r['EMA9'] < r['EMA21'] and r['close'] < r['EMA200']
    rl = cfg['rsi_min'] <= rsi <= cfg['rsi_max']
    rs_s = (100-cfg['rsi_max']) <= rsi <= (100-cfg['rsi_min'])
    ml = r['MACD_Hist'] > 0
    ms = r['MACD_Hist'] < 0
    vol = r['Vol_Rel'] >= cfg['vol_fator']

    if tl and rl and ml and vol:
        sinal = "LONG"
        stop  = preco - atr * cfg['atr_stop']
        tp1   = preco + atr * cfg['atr_tp1']
        tp2   = preco + atr * cfg['atr_tp2']
    elif ts and rs_s and ms and vol:
        sinal = "SHORT"
        stop  = preco + atr * cfg['atr_stop']
        tp1   = preco - atr * cfg['atr_tp1']
        tp2   = preco - atr * cfg['atr_tp2']
    else:
        sinal = "FLAT"
        stop = tp1 = tp2 = 0

    return sinal, preco, rsi, atr, stop, tp1, tp2

def robo_daytrade():
    if not BITGET_API_KEY:
        print("[DAYTRADE] Credenciais Bitget ausentes - robô não iniciado")
        return

    exchange = ccxt.bitget({
        'apiKey': BITGET_API_KEY, 'secret': BITGET_SECRET_KEY,
        'password': BITGET_PASSPHRASE, 'enableRateLimit': True,
        'options': {'defaultType': 'swap'}
    })
    historico = {cfg['symbol']: "FLAT" for cfg in ATIVOS_DAYTRADE}

    print("[DAYTRADE] Robô iniciado")
    enviar_telegram(
        "⚡ *DayTrade Engine Ativado!*\n\n"
        "🔶 COPPER/USDT (1h)\n"
        "🥇 XAU/USDT (1h)\n"
        "🔵 PENDLE/USDT (15m)\n\n"
        "_Parâmetros otimizados via backtest._"
    )

    while True:
        agora = datetime.now().strftime('%H:%M:%S')
        print(f"[DAYTRADE][{agora}] Varrendo futuros...")

        for cfg in ATIVOS_DAYTRADE:
            try:
                bars = exchange.fetch_ohlcv(
                    cfg['symbol'], timeframe=cfg['timeframe'], limit=cfg['limite']
                )
                df = pd.DataFrame(bars, columns=['timestamp','open','high','low','close','volume'])
                sinal, preco, rsi, atr, stop, tp1, tp2 = sinal_daytrade(df, cfg)

                print(f"[DAYTRADE] {cfg['emoji']} {cfg['nome']}: "
                      f"{sinal} | ${preco:,.4f} | RSI: {rsi:.1f}")

                if sinal != historico[cfg['symbol']] and sinal != "FLAT":
                    emoji = "🟢" if sinal == "LONG" else "🔴"
                    rr = abs(tp2-preco)/abs(stop-preco) if stop != preco else 0
                    enviar_telegram(
                        f"{emoji} *{sinal} — {cfg['nome']}*\n\n"
                        f"▪️ *Preço:* ${preco:,.4f}\n"
                        f"▪️ *RSI:* {rsi:.1f}\n"
                        f"▪️ *ATR:* ${atr:,.4f}\n\n"
                        f"🔴 *Stop Loss:* ${stop:,.4f}\n"
                        f"🟡 *TP1 (50%):* ${tp1:,.4f}\n"
                        f"🟢 *TP2 (100%):* ${tp2:,.4f}\n"
                        f"📊 *R/R:* {rr:.2f}x\n\n"
                        f"⏱️ *TF:* {cfg['timeframe'].upper()} | "
                        f"🕐 {datetime.now().strftime('%d/%m %H:%M')}\n\n"
                        f"_⚠️ Gerencie o risco antes de operar._"
                    )
                    print(f"[DAYTRADE] ALERTA: {cfg['nome']} — {sinal}")

                historico[cfg['symbol']] = sinal
                time.sleep(2)
            except Exception as e:
                print(f"[DAYTRADE] Erro em {cfg['nome']}: {e}")

        print(f"[DAYTRADE] Próxima varredura em 10 minutos")
        time.sleep(600)

# ─────────────────────────────────────────────────────────────
#  EXECUÇÃO PRINCIPAL — DOIS ROBÔS EM PARALELO
# ─────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  🤖 NOTIFIER INTEGRADO — SENIOR + DAYTRADE")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)

    t1 = threading.Thread(target=robo_senior,   daemon=True, name="Senior")
    t2 = threading.Thread(target=robo_daytrade, daemon=True, name="DayTrade")

    t1.start()
    time.sleep(5)
    t2.start()

    print("\n✅ Ambos os robôs ativos!")
    print("  → Senior: varredura a cada 1h")
    print("  → DayTrade: varredura a cada 10min\n")

    while True:
        time.sleep(60)
        if not t1.is_alive():
            print("[AVISO] Senior caiu - reiniciando...")
            t1 = threading.Thread(target=robo_senior, daemon=True, name="Senior")
            t1.start()
        if not t2.is_alive():
            print("[AVISO] DayTrade caiu - reiniciando...")
            t2 = threading.Thread(target=robo_daytrade, daemon=True, name="DayTrade")
            t2.start()

if __name__ == "__main__":
    main()
