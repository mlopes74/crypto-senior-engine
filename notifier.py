import time
from datetime import datetime, timedelta
import urllib.request
import urllib.parse
import json
import numpy as np
import pandas as pd
import ccxt

# ==================== CONFIGURAÇÃO INDISPENSÁVEL ====================
TELEGRAM_TOKEN = "8556182706:AAHCLVj8OdTRJZn90hpNESV6WrIweAujTBU"
TELEGRAM_CHAT_ID = "617365483"
# ====================================================================

# ==================== PARÂMETROS DAS MELHORIAS ======================
COOLDOWN_ALERTA_HORAS = 4        # Melhoria 2: intervalo mínimo entre alertas por ativo
RSI_SEMANAL_MIN_LONG  = 40       # Melhoria 3: RSI semanal mínimo para aceitar LONGs
# ====================================================================

# Dicionário de ativos reais do portfólio
ATIVOS_CARTEIRA = {
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


# =============================================================================
#  FUNÇÃO DE ENVIO TELEGRAM
# =============================================================================
def enviar_alerta_telegram(mensagem):
    texto_codificado = urllib.parse.quote(mensagem)
    url = (
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        f"?chat_id={TELEGRAM_CHAT_ID}"
        f"&text={texto_codificado}"
        f"&parse_mode=Markdown"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response:
            return response.getcode() == 200
    except Exception as e:
        print(f"Erro ao enviar mensagem Telegram: {e}")
        return False


# =============================================================================
#  MOTOR DE ANÁLISE TÉCNICA — v3 (com melhorias)
# =============================================================================
class CryptoAnalystEngine:
    """
    Calcula indicadores em múltiplos timeframes e aplica os filtros:
      1. EMA diária (50 > 200) para liberar LONGs
      2. RSI semanal >= 40 para liberar LONGs
      3. Trailing stop: alerta de breakeven quando TP1 é atingido
    """

    def __init__(self, df_diario: pd.DataFrame, df_semanal: pd.DataFrame):
        self.df  = df_diario.copy()
        self.dfw = df_semanal.copy()

    # ------------------------------------------------------------------
    # Helpers — RSI genérico
    # ------------------------------------------------------------------
    @staticmethod
    def _calcular_rsi(series: pd.Series, periodo: int = 14) -> pd.Series:
        delta    = series.diff()
        up       = delta.clip(lower=0)
        down     = -delta.clip(upper=0)
        ema_up   = up.ewm(com=periodo - 1, adjust=False).mean()
        ema_down = down.ewm(com=periodo - 1, adjust=False).mean()
        rs       = np.where(ema_down == 0, np.nan, ema_up / ema_down)
        return pd.Series(
            np.where(ema_down == 0, 100, 100 - (100 / (1 + rs))),
            index=series.index,
        )

    # ------------------------------------------------------------------
    # MELHORIA 1 — Filtro de tendência diária (EMA50 > EMA200)
    # ------------------------------------------------------------------
    def _tendencia_diaria_bullish(self) -> bool:
        """Retorna True se EMA50 diária > EMA200 diária (bull market macro)."""
        ema50  = self.df["close"].ewm(span=50,  adjust=False).mean().iloc[-1]
        ema200 = self.df["close"].ewm(span=200, adjust=False).mean().iloc[-1]
        return float(ema50) > float(ema200)

    # ------------------------------------------------------------------
    # MELHORIA 3 — RSI semanal
    # ------------------------------------------------------------------
    def _rsi_semanal(self) -> float:
        """Calcula o RSI de 14 períodos no timeframe semanal."""
        rsi_series = self._calcular_rsi(self.dfw["close"], periodo=14)
        return float(rsi_series.iloc[-1])

    # ------------------------------------------------------------------
    # Cálculo principal
    # ------------------------------------------------------------------
    def calcular_sinal_atual(self):
        # --- Médias móveis diárias ---
        self.df["EMA_50"]  = self.df["close"].ewm(span=50,  adjust=False).mean()
        self.df["EMA_200"] = self.df["close"].ewm(span=200, adjust=False).mean()
        self.df["EMA_20"]  = self.df["close"].ewm(span=20,  adjust=False).mean()
        self.df["Distancia_Medias_Pct"] = (
            (self.df["EMA_50"] - self.df["EMA_200"]) / self.df["EMA_200"]
        ) * 100

        # --- RSI diário ---
        self.df["RSI"] = self._calcular_rsi(self.df["close"])

        # --- Fibonacci (lookback 100 velas diárias) ---
        recente = self.df.tail(100)
        maxima  = recente["high"].max()
        minima  = recente["low"].min()
        diff    = maxima - minima
        self.df["Fib_50.0"] = maxima - diff * 0.500
        self.df["Fib_61.8"] = maxima - diff * 0.618
        self.df["Fib_38.2"] = maxima - diff * 0.382

        atual    = self.df.iloc[-1]
        anterior = self.df.iloc[-2]
        preco    = float(atual["close"])
        rsi      = float(atual["RSI"])

        # --- Filtros multi-timeframe (Melhorias 1 e 3) ---
        bull_diario   = self._tendencia_diaria_bullish()   # Melhoria 1
        rsi_sem       = self._rsi_semanal()                # Melhoria 3
        long_liberado = bull_diario and (rsi_sem >= RSI_SEMANAL_MIN_LONG)

        # --- Lógica de sinal ---
        sinal = "Neutro"

        # Gatilho de COMPRA: Antecipação Golden Cross
        if (
            atual["EMA_50"] < atual["EMA_200"]
            and atual["Distancia_Medias_Pct"] > anterior["Distancia_Medias_Pct"]
            and atual["Distancia_Medias_Pct"] > -5
        ):
            if rsi < 35 and preco <= atual["Fib_61.8"] * 1.02:
                if long_liberado:                          # ← Melhorias 1 e 3 aplicadas
                    sinal = "COMPRA (Antecipação Golden Cross)"
                else:
                    sinal = "NEUTRO (LONG bloqueado: tendência diária/RSI semanal desfavoráveis)"

        # Gatilho de COMPRA: Retração em Bull Market
        elif atual["EMA_50"] > atual["EMA_200"]:
            if rsi < 45 and preco <= atual["Fib_50.0"] * 1.01:
                if long_liberado:                          # ← Melhorias 1 e 3 aplicadas
                    sinal = "COMPRA (Retração em Bull Market)"
                else:
                    sinal = "NEUTRO (LONG bloqueado: RSI semanal < 40)"

        # Gatilho de VENDA: Quebra da Média 20 (trailing stop)
        if (
            preco < atual["EMA_20"]
            and anterior["close"] > anterior["EMA_20"]
            and rsi > 65
        ):
            sinal = "VENDA (Quebra de Média 20)"

        return sinal, preco, rsi, bull_diario, rsi_sem


# =============================================================================
#  GERENCIADOR DE ESTADO — controla cooldown e trailing stop
# =============================================================================
class GerenciadorEstado:
    """
    Mantém em memória:
      - último sinal enviado por ativo
      - timestamp do último alerta (para cooldown de 4h)   ← Melhoria 2
      - posições abertas para trailing stop                 ← Melhoria 4
    """

    def __init__(self):
        self.ultimo_sinal:     dict = {}   # nome_ativo → último sinal
        self.ultimo_alerta_ts: dict = {}   # nome_ativo → datetime do último alerta
        self.posicoes_abertas: dict = {}   # nome_ativo → dict com detalhes da posição

    # ------------------------------------------------------------------
    # Melhoria 2 — Cooldown de 4 horas
    # ------------------------------------------------------------------
    def pode_alertar(self, nome_ativo: str) -> bool:
        """Retorna True se já passaram >= 4h desde o último alerta do ativo."""
        ultimo = self.ultimo_alerta_ts.get(nome_ativo)
        if ultimo is None:
            return True
        return datetime.now() - ultimo >= timedelta(hours=COOLDOWN_ALERTA_HORAS)

    def registrar_alerta(self, nome_ativo: str, sinal: str):
        self.ultimo_alerta_ts[nome_ativo] = datetime.now()
        self.ultimo_sinal[nome_ativo]     = sinal

    # ------------------------------------------------------------------
    # Melhoria 4 — Trailing Stop (breakeven após TP1)
    # ------------------------------------------------------------------
    def abrir_posicao(self, nome_ativo: str, direcao: str, preco_entrada: float):
        """Registra uma nova posição para monitorar o trailing stop."""
        atr_estimado = preco_entrada * 0.005  # ATR estimado conservador: 0,5%
        if direcao == "COMPRA":
            tp1  = preco_entrada + atr_estimado * 5   # TP1 = entrada + 5×ATR
            tp2  = preco_entrada + atr_estimado * 10  # TP2 = entrada + 10×ATR
            stop = preco_entrada - atr_estimado        # SL  = entrada − 1×ATR
        else:
            tp1  = preco_entrada - atr_estimado * 5
            tp2  = preco_entrada - atr_estimado * 10
            stop = preco_entrada + atr_estimado

        self.posicoes_abertas[nome_ativo] = {
            "direcao":        direcao,
            "entrada":        preco_entrada,
            "stop":           stop,
            "tp1":            tp1,
            "tp2":            tp2,
            "tp1_atingido":   False,
            "breakeven_aviso": False,
        }

    def verificar_trailing_stop(self, nome_ativo: str, preco_atual: float) -> str | None:
        """
        Verifica se o TP1 foi atingido e emite aviso de breakeven.
        Retorna uma mensagem de alerta ou None.
        """
        pos = self.posicoes_abertas.get(nome_ativo)
        if not pos or pos["breakeven_aviso"]:
            return None

        tp1_atingido = (
            (pos["direcao"] == "COMPRA" and preco_atual >= pos["tp1"])
            or (pos["direcao"] == "VENDA" and preco_atual <= pos["tp1"])
        )

        if tp1_atingido and not pos["tp1_atingido"]:
            pos["tp1_atingido"]    = True
            pos["breakeven_aviso"] = True
            entrada = pos["entrada"]
            return (
                f"🔔 *TRAILING STOP — {nome_ativo}*\n\n"
                f"✅ TP1 atingido! Mova o Stop Loss para o ponto de entrada.\n"
                f"▪️ *Novo SL (Breakeven):* ${entrada:,.4f}\n"
                f"▪️ *Preço Atual:* ${preco_atual:,.4f}\n"
                f"▪️ *Horário:* {datetime.now().strftime('%d/%m %H:%M')}\n\n"
                f"🛡️ _Posição protegida. Deixe o lucro correr até o TP2._"
            )
        return None

    def fechar_posicao(self, nome_ativo: str):
        self.posicoes_abertas.pop(nome_ativo, None)


# =============================================================================
#  LOOP PRINCIPAL DE MONITORAMENTO
# =============================================================================
def executar_monitoramento():
    exchange = ccxt.binance({"enableRateLimit": True})
    estado   = GerenciadorEstado()

    # Inicializa histórico de sinais para todos os ativos
    for nome in ATIVOS_CARTEIRA:
        estado.ultimo_sinal[nome] = "Neutro"

    print("=" * 55)
    print("   CRYPTO SENIOR ENGINE v3 — MONITORAMENTO ATIVO    ")
    print("   Melhorias: EMA diária | Cooldown 4h |            ")
    print("              RSI semanal | Trailing Stop            ")
    print("=" * 55)
    enviar_alerta_telegram(
        "🤖 *Crypto Senior Engine v3 Ativado!*\n"
        "Melhorias aplicadas:\n"
        "✅ Filtro EMA diária (50 > 200)\n"
        "✅ Cooldown de 4h por ativo\n"
        "✅ Filtro RSI semanal ≥ 40\n"
        "✅ Trailing Stop automático (Breakeven após TP1)"
    )

    while True:
        agora = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{agora}] Varrendo o mercado...")

        for nome_ativo, ticker_api in ATIVOS_CARTEIRA.items():
            try:
                # --------------------------------------------------------
                # 1. Buscar dados diários e semanais
                # --------------------------------------------------------
                bars_d = exchange.fetch_ohlcv(ticker_api, timeframe="1d", limit=250)
                bars_w = exchange.fetch_ohlcv(ticker_api, timeframe="1w", limit=52)

                df_d = pd.DataFrame(bars_d, columns=["timestamp","open","high","low","close","volume"])
                df_w = pd.DataFrame(bars_w, columns=["timestamp","open","high","low","close","volume"])

                # --------------------------------------------------------
                # 2. Rodar análise técnica (inclui filtros 1 e 3)
                # --------------------------------------------------------
                engine = CryptoAnalystEngine(df_d, df_w)
                sinal_atual, preco, rsi, bull_diario, rsi_sem = engine.calcular_sinal_atual()

                # --------------------------------------------------------
                # 3. Melhoria 4 — Trailing Stop (verificar posições abertas)
                # --------------------------------------------------------
                msg_trailing = estado.verificar_trailing_stop(nome_ativo, preco)
                if msg_trailing:
                    enviar_alerta_telegram(msg_trailing)
                    print(f" -> [TRAILING STOP] {nome_ativo} @ ${preco:,.4f}")

                # --------------------------------------------------------
                # 4. Verificar se sinal mudou
                # --------------------------------------------------------
                sinal_anterior = estado.ultimo_sinal.get(nome_ativo, "Neutro")
                sinal_mudou    = sinal_atual != sinal_anterior

                if sinal_mudou and sinal_atual not in ("Neutro",) and "NEUTRO" not in sinal_atual:

                    # Melhoria 2 — Cooldown de 4h
                    if not estado.pode_alertar(nome_ativo):
                        restante = COOLDOWN_ALERTA_HORAS * 60 - int(
                            (datetime.now() - estado.ultimo_alerta_ts[nome_ativo]).total_seconds() / 60
                        )
                        print(f" -> [COOLDOWN] {nome_ativo}: próximo alerta em ~{restante}min")
                        estado.ultimo_sinal[nome_ativo] = sinal_atual
                        time.sleep(1)
                        continue

                    # ---- Montar mensagem rica ----
                    eh_compra = "COMPRA" in sinal_atual
                    emoji     = "🟢" if eh_compra else "🔴"
                    tendencia = "📈 BULL" if bull_diario else "📉 BEAR"
                    filtro_ok = "✅ Liberado" if (bull_diario and rsi_sem >= RSI_SEMANAL_MIN_LONG) else "⛔ Filtrado"

                    mensagem_alerta = (
                        f"{emoji} *ALERTA DE OPERAÇÃO: {nome_ativo}*\n\n"
                        f"▪️ *Ação:* {sinal_atual}\n"
                        f"▪️ *Preço Atual:* ${preco:,.4f}\n"
                        f"▪️ *RSI Diário:* {rsi:.1f}\n"
                        f"▪️ *RSI Semanal:* {rsi_sem:.1f}\n"
                        f"▪️ *Tendência Diária:* {tendencia}\n"
                        f"▪️ *Filtro Multi-TF:* {filtro_ok}\n"
                        f"▪️ *Horário:* {datetime.now().strftime('%d/%m %H:%M')}\n\n"
                        f"⚠️ _Acesse sua corretora para gerenciar o risco._"
                    )

                    enviar_alerta_telegram(mensagem_alerta)
                    estado.registrar_alerta(nome_ativo, sinal_atual)
                    print(f" -> [ALERTA] {nome_ativo}: {sinal_atual} | RSI sem={rsi_sem:.1f} | Bull={bull_diario}")

                    # Melhoria 4 — Abrir posição para trailing stop
                    direcao = "COMPRA" if eh_compra else "VENDA"
                    estado.abrir_posicao(nome_ativo, direcao, preco)

                else:
                    # Atualiza sinal mesmo sem alertar (mantém estado correto)
                    estado.ultimo_sinal[nome_ativo] = sinal_atual

                    # Se sinal voltou a Neutro, fecha posição aberta
                    if sinal_atual == "Neutro":
                        estado.fechar_posicao(nome_ativo)

                time.sleep(1)  # Anti-rate-limit entre ativos

            except Exception as e:
                print(f"Erro ao processar {nome_ativo}: {e}")

        # Intervalo de varredura: 1h para gráficos diários
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Próxima varredura em 60 minutos...")
        time.sleep(3600)


if __name__ == "__main__":
    executar_monitoramento()
