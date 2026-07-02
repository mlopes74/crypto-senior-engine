import time
import json
import os
import urllib.request
import urllib.parse
from datetime import datetime

import pandas as pd
import ccxt

from engine import CryptoEngine

# ==================== CONFIGURAÇÃO ====================
TELEGRAM_TOKEN   = "8556182706:AAHCLVj8OdTRJZn90hpNESV6WrIweAujTBU"
TELEGRAM_CHAT_ID = "617365483"
ESTADO_FILE      = "estado.json"   # Persiste sinais entre reinicializações
INTERVALO_SCAN   = 3600            # Varredura a cada 1 hora (ideal para timeframe 1d)
# ======================================================

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

# --- PERSISTÊNCIA DE ESTADO ---
def carregar_estado() -> dict:
    """Carrega o último sinal de cada ativo do disco (evita alertas duplicados ao reiniciar)."""
    if os.path.exists(ESTADO_FILE):
        try:
            with open(ESTADO_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {nome: "Neutro" for nome in ATIVOS.keys()}

def salvar_estado(estado: dict):
    with open(ESTADO_FILE, 'w') as f:
        json.dump(estado, f, indent=2)

# --- TELEGRAM ---
def enviar_telegram(mensagem: str) -> bool:
    texto_codificado = urllib.parse.quote(mensagem)
    url = (
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        f"?chat_id={TELEGRAM_CHAT_ID}&text={texto_codificado}&parse_mode=Markdown"
    )
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return response.getcode() == 200
    except Exception as e:
        print(f"Erro Telegram: {e}")
        return False

# --- LOOP PRINCIPAL ---
def executar_monitoramento():
    exchange = ccxt.binance({'enableRateLimit': True})
    historico_sinais = carregar_estado()

    print("=" * 52)
    print("   CRYPTO SENIOR ENGINE v2 — NOTIFIER ATIVO        ")
    print("=" * 52)
    enviar_telegram(
        "🤖 *Crypto Senior Engine v2 Ativado!*\n"
        "Monitoramento em tempo real iniciado.\n"
        f"_Estado anterior carregado: {len(historico_sinais)} ativos._"
    )

    while True:
        agora = datetime.now().strftime('%H:%M:%S')
        print(f"\n[{agora}] Varrendo {len(ATIVOS)} ativos...")

        for nome, ticker in ATIVOS.items():
            try:
                bars = exchange.fetch_ohlcv(ticker, timeframe='1d', limit=250)
                df   = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

                engine = CryptoEngine(df)
                sinal, cor, vies, preco, rsi, macd_hist, _, detalhe = engine.gerar_sinal()

                if sinal != historico_sinais.get(nome, "Neutro"):
                    if sinal != "Neutro — Aguardar Claridade":
                        emoji = "🟢" if cor == "green" else ("🟠" if cor == "orange" else "🔴")
                        mensagem = (
                            f"{emoji} *ALERTA: {nome}*\n\n"
                            f"▪️ *Sinal:* {sinal}\n"
                            f"▪️ *Preço:* ${preco:,.4f}\n"
                            f"▪️ *RSI:* {rsi:.2f}\n"
                            f"▪️ *MACD Hist:* {macd_hist:.4f}\n"
                            f"▪️ *Viés:* {vies}\n"
                            f"▪️ *Detalhe:* {detalhe}\n"
                            f"▪️ *Horário:* {datetime.now().strftime('%d/%m %H:%M')}\n\n"
                            f"⚠️ _Acesse sua corretora para gerenciar o risco._"
                        )
                        enviar_telegram(mensagem)
                        print(f"  → [ALERTA] {nome}: {sinal}")

                    historico_sinais[nome] = sinal
                    salvar_estado(historico_sinais)

                time.sleep(1)  # Anti-rate-limit entre ativos

            except Exception as e:
                print(f"  → [ERRO] {nome}: {e}")

        print(f"  Próxima varredura em {INTERVALO_SCAN // 60} minutos.")
        time.sleep(INTERVALO_SCAN)

if __name__ == "__main__":
    executar_monitoramento()
