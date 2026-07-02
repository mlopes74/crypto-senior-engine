import numpy as np
import pandas as pd


class CryptoEngine:
    """
    Motor único de análise técnica do Crypto Senior Engine v2.
    Importado por app.py (dashboard) e notifier.py (robô de alertas).
    Garante consistência total entre os sinais exibidos e os alertas enviados.
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    # ------------------------------------------------------------------
    # CÁLCULO DE TODOS OS INDICADORES
    # ------------------------------------------------------------------
    def calcular_indicadores(self) -> pd.DataFrame:
        # Médias Móveis Exponenciais
        self.df['EMA_20']  = self.df['close'].ewm(span=20,  adjust=False).mean()
        self.df['EMA_50']  = self.df['close'].ewm(span=50,  adjust=False).mean()
        self.df['EMA_200'] = self.df['close'].ewm(span=200, adjust=False).mean()

        # Distância percentual entre EMA 50 e EMA 200 (detecta convergência)
        self.df['Distancia_Medias_Pct'] = (
            (self.df['EMA_50'] - self.df['EMA_200']) / self.df['EMA_200']
        ) * 100

        # RSI 14 períodos via Wilder Smoothing (ewm com=13 ≡ span=14 de Wilder)
        delta    = self.df['close'].diff()
        up       = delta.clip(lower=0)
        down     = -delta.clip(upper=0)
        ema_up   = up.ewm(com=13, adjust=False).mean()
        ema_down = down.ewm(com=13, adjust=False).mean()
        rs = np.where(ema_down == 0, np.nan, ema_up / ema_down)
        self.df['RSI'] = np.where(ema_down == 0, 100, 100 - (100 / (1 + rs)))

        # MACD (12, 26, 9) — confirmador de momentum
        ema_12 = self.df['close'].ewm(span=12, adjust=False).mean()
        ema_26 = self.df['close'].ewm(span=26, adjust=False).mean()
        self.df['MACD']        = ema_12 - ema_26
        self.df['MACD_Signal'] = self.df['MACD'].ewm(span=9, adjust=False).mean()
        self.df['MACD_Hist']   = self.df['MACD'] - self.df['MACD_Signal']

        # Filtro de Volume — SMA 20 períodos
        self.df['Volume_SMA20'] = self.df['volume'].rolling(window=20).mean()
        self.df['Volume_OK']    = self.df['volume'] >= self.df['Volume_SMA20'] * 0.70

        # Fibonacci Dinâmico — lookback de 100 velas
        recente  = self.df.tail(100)
        maxima   = recente['high'].max()
        minima   = recente['low'].min()
        diff     = maxima - minima
        self.df['Fib_38.2'] = maxima - (diff * 0.382)
        self.df['Fib_50.0'] = maxima - (diff * 0.500)
        self.df['Fib_61.8'] = maxima - (diff * 0.618)

        return self.df

    # ------------------------------------------------------------------
    # GERAÇÃO DO SINAL PRINCIPAL
    # ------------------------------------------------------------------
    def gerar_sinal(self):
        """
        Retorna uma tupla com todos os dados relevantes da análise:
        (sinal, cor, viés_macro, preço, rsi, macd_hist, dados_última_linha, detalhe)
        """
        self.df = self.calcular_indicadores()

        atual    = self.df.iloc[-1]
        anterior = self.df.iloc[-2]

        preco     = float(atual['close'])
        rsi       = float(atual['RSI'])
        macd_hist = float(atual['MACD_Hist'])
        volume_ok = bool(atual['Volume_OK'])

        vies = "BULL (Alta Macro)" if atual['EMA_50'] > atual['EMA_200'] else "BEAR (Baixa Macro)"

        sinal   = "Neutro — Aguardar Claridade"
        cor     = "gray"
        detalhe = ""

        # --- GATILHO 1: Antecipação de Golden Cross ---
        if (
            atual['EMA_50'] < atual['EMA_200']
            and atual['Distancia_Medias_Pct'] > anterior['Distancia_Medias_Pct']
            and atual['Distancia_Medias_Pct'] > -5
            and rsi < 35
            and preco <= atual['Fib_61.8'] * 1.02
            and volume_ok
        ):
            sinal   = "COMPRA: Antecipação de Reversão (Golden Cross)"
            cor     = "green"
            detalhe = "EMA 50 convergindo para EMA 200 | RSI em sobrevenda | Suporte Fib 61.8%"

        # --- GATILHO 2: Retração Protegida em Bull Market ---
        elif (
            atual['EMA_50'] > atual['EMA_200']
            and rsi < 45
            and preco <= atual['Fib_50.0'] * 1.01
            and macd_hist > 0
            and volume_ok
        ):
            sinal   = "COMPRA: Aporte em Suporte de Bull Market"
            cor     = "green"
            detalhe = "Bull Market confirmado | Retração no Fib 50% | MACD positivo"

        # --- GATILHO 3: RSI em Sobrecompra Extrema ---
        if rsi > 72:
            sinal   = "ATENÇÃO: Alvo de RSI Atingido — Monitorar Proteção"
            cor     = "orange"
            detalhe = f"RSI em {rsi:.1f} — zona de sobrecompra"

        # --- GATILHO 4: Trailing Stop — Quebra da EMA 20 (prioridade máxima) ---
        if (
            preco < atual['EMA_20']
            and anterior['close'] > anterior['EMA_20']
            and rsi > 65
        ):
            sinal   = "VENDA: Gatilho de Saída Acionado (Quebra de Média 20)"
            cor     = "red"
            detalhe = "Fechamento abaixo da EMA 20 após RSI elevado — trailing stop ativado"

        return sinal, cor, vies, preco, rsi, macd_hist, atual, detalhe
