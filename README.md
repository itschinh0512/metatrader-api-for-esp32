# MetaTrader 5 FastAPI Web API for ESP32

This project runs a FastAPI API on the PC that has MetaTrader 5 installed. ESP32 calls the API over Wi-Fi/LAN to read market data and manage trades.

## Setup

1. Create a local `.env` file from `.env.example`.
2. Fill in `API_KEY`.
3. Fill in MT5 login fields only if you want Python to explicitly log in. If MT5 terminal is already open and logged in, the API can initialize against that session.
4. Set `MT5_PATH` to your installed terminal path, for example `C:\Program Files\MetaTrader 5\terminal64.exe`.
5. Keep `MT5_LOGIN_ON_START=false` when MT5 is already open and logged in. Set it to `true` only if you need Python to force a login.
6. Install dependencies:

```powershell
.\.venv\Scripts\pip.exe install -r requirements.txt
```

7. Start the server from PowerShell, not by double-clicking `server.py`:

```powershell
.\.venv\Scripts\python.exe server.py
```

The server listens on `0.0.0.0:5000` by default. ESP32 should call the PC's LAN IP address, for example `http://192.168.1.20:5000`.

If the terminal stops at `Logging in to MT5 account ...`, set `MT5_LOGIN_ON_START=false`, stop Python with `Ctrl+C`, keep MT5 open, and run `server.py` again.

FastAPI interactive docs:

```text
http://127.0.0.1:5000/docs
```

OpenAPI schema:

```text
http://127.0.0.1:5000/openapi.json
```

## Public Endpoints

### Health check

```text
GET /
```

### Latest tick

```text
GET /tick/XAUUSD
```

### OHLCV candles

```text
GET /candles/XAUUSD?timeframe=M1&count=50
```

Supported timeframes: `M1`, `M5`, `M15`, `M30`, `H1`, `H4`, `D1`.

Response data includes `time`, `open`, `high`, `low`, `close`, and `volume`. For MT5 forex/CFD symbols, `volume` is tick volume.

### All configured ticks

```text
GET /all
```

### Configured symbols

```text
GET /symbols
```

## Protected Endpoints

Send the configured API key with every protected request:

```text
X-API-Key: your-api-key
```

### Account

```text
GET /account
```

### Open positions

```text
GET /positions
GET /positions?symbol=XAUUSD
```

### Pending orders

```text
GET /orders
GET /orders?symbol=XAUUSD
```

### Market order

```text
POST /order/market
```

```json
{
  "symbol": "XAUUSD",
  "type": "BUY",
  "volume": 0.01,
  "sl": 2320.0,
  "tp": 2350.0,
  "comment": "esp32 market"
}
```

### Pending order

```text
POST /order/pending
```

```json
{
  "symbol": "XAUUSD",
  "type": "BUY_LIMIT",
  "volume": 0.01,
  "price": 2330.0,
  "sl": 2320.0,
  "tp": 2350.0,
  "comment": "esp32 pending"
}
```

Supported pending types: `BUY_LIMIT`, `SELL_LIMIT`, `BUY_STOP`, `SELL_STOP`.

### Modify pending order

```text
POST /order/modify
```

```json
{
  "ticket": 123456789,
  "price": 2331.0,
  "sl": 2321.0,
  "tp": 2351.0
}
```

### Cancel pending order

```text
POST /order/cancel
```

```json
{
  "ticket": 123456789
}
```

### Modify position SL/TP

```text
POST /position/modify
```

```json
{
  "ticket": 123456789,
  "sl": 2325.0,
  "tp": 2360.0
}
```

### Close position

```text
POST /position/close
```

```json
{
  "ticket": 123456789
}
```

## Response Format

Success:

```json
{
  "ok": true,
  "message": "ok",
  "data": {}
}
```

Error:

```json
{
  "ok": false,
  "error": "Invalid volume",
  "details": {}
}
```

## Safety Notes

- Test on a demo account first.
- Keep `.env` private.
- Do not expose this local API server to the public internet.
- Change the old MT5 password if it has ever been shared or committed.
