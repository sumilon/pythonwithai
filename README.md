# pythonwithai — StockLens Pro

FastAPI app with stock analysis, financial calculators, and AI chat.  
Designed to run on **GCP Cloud Run** with minimal memory footprint.

---

## Pages & Routes

| URL | Description |
|---|---|
| `/` | Portfolio / landing page |
| `/stock` | Live stock quotes + chart (NSE/BSE/US) |
| `/calculator` | Financial calculators (EMI, SIP, FD, RD, SWP…) |
| `/ai` | AI chat powered by Groq LLM |
| `/todo` | To-do list |
| `/vault` | Password vault |
| `/emi` | EMI calculator |
| `/swp` | SWP calculator |
| `/game` | Game page |
| `/stroop` | Stroop test |
| `/api/quote/{symbol}` | JSON: live stock quote (cached 5 min) |
| `/api/history/{symbol}` | JSON: OHLCV history + MA20/MA50 (cached 30 min) |
| `/health` | JSON: service health check |
| `/api/docs` | Swagger UI |

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | Yes (for /ai) | — | Get free key at console.groq.com |
| `ALLOWED_ORIGINS` | No | `*` | Comma-separated CORS origins. **Set this in production.** |
| `GROQ_MODEL` | No | `llama-3.1-8b-instant` | Groq model to use |
| `GROQ_MAX_TOKENS` | No | `512` | Max tokens per AI response |
| `QUOTE_CACHE_TTL` | No | `300` | Quote cache lifetime (seconds) |
| `HISTORY_CACHE_TTL` | No | `1800` | History cache lifetime (seconds) |
| `QUOTE_CACHE_MAX` | No | `200` | Max symbols in quote cache |
| `HISTORY_CACHE_MAX` | No | `100` | Max entries in history cache |

---

## Stock Symbol Format

| Exchange | Format | Example |
|---|---|---|
| NSE India | `SYMBOL.NS` | `TCS.NS`, `RELIANCE.NS` |
| BSE India | `SYMBOL.BO` | `TCS.BO` |
| US stocks | `SYMBOL` | `AAPL`, `MSFT` |
| Indices | `^INDEX` | `^NSEI`, `^BSESN` |

---

## Local Development

```bash

# Create virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set API key
export GROQ_API_KEY=your_key_here
$env:GROQ_API_KEY="your_key_here"

# Run
uvicorn main:app --reload --port 8080
```

## Deploy to GCP Cloud Run

```bash
# First deploy (builds image via Cloud Build)
gcloud run deploy stocklens \
  --source . \
  --region asia-south1 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 3 \
  --concurrency 80 \
  --set-env-vars GROQ_API_KEY=your_key_here \
  --set-env-vars ALLOWED_ORIGINS=https://yourdomain.com

# Subsequent deploys
gcloud run deploy stocklens --source . --region asia-south1
```

> **Memory note:** pandas + numpy (pulled in by yfinance) account for ~130 MB of the
> ~250 MB baseline. 512 Mi is the correct minimum. Upgrade to 1 Gi if you see OOM kills
> under load or if you enable multiple concurrent symbols being fetched simultaneously.

---

## Expected Memory on Cloud Run

| State | Estimate |
|---|---|
| Idle (after startup) | ~220–260 MB |
| Under moderate load | ~300–380 MB |
| Recommended allocation | **512 Mi** |
