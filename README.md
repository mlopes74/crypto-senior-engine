# ⬡ Crypto Trading Suite

Sistema integrado de monitoramento e alertas de criptoativos.

## Componentes

### 1. Senior Engine (Médio/Longo Prazo)
- 11 criptos do portfólio
- Timeframe: 1 dia
- Fonte: Kraken
- Sinais: Golden Cross, Retração Bull Market, Quebra EMA20

### 2. DayTrade Engine (Intradiário)
- COPPER (1h), XAU (1h), PENDLE (15m)
- Fonte: Bitget Futuros Perpétuos
- Parâmetros otimizados via backtest

## Arquivos

- `app.py` — Dashboard Streamlit (2 abas)
- `notifier.py` — Worker Railway 24/7 (alertas Telegram)
- `requirements.txt` — Dependências
- `runtime.txt` — Python 3.11
- `Procfile` + `railway.toml` — Config Railway

## Variáveis de Ambiente Necessárias

```
TELEGRAM_TOKEN
TELEGRAM_CHAT_ID
BITGET_API_KEY
BITGET_SECRET_KEY
BITGET_PASSPHRASE
```

Configuradas em:
- **Railway** → Project → Variables
- **Streamlit Cloud** → App Settings → Secrets
