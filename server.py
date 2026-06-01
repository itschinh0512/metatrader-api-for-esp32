# server.py
from typing import Optional

import uvicorn
from fastapi import Depends, FastAPI, Query, Security
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

import mt5_client
from config import API_KEY, FLASK_DEBUG, FLASK_HOST, FLASK_PORT, MAX_CANDLES, SYMBOLS


app = FastAPI(
    title="MT5 ESP32 Web API",
    version="1.0.0",
    description="Local FastAPI bridge between ESP32 and MetaTrader 5 demo terminal.",
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
mt5_connected = False


class MarketOrderRequest(BaseModel):
    symbol: str = Field(..., examples=["XAUUSD"])
    type: str = Field(..., examples=["BUY"], description="BUY or SELL")
    volume: float = Field(..., gt=0, examples=[0.01])
    sl: Optional[float] = Field(None, examples=[2320.0])
    tp: Optional[float] = Field(None, examples=[2360.0])
    comment: str = Field("esp32 market", examples=["esp32 market"])


class PendingOrderRequest(BaseModel):
    symbol: str = Field(..., examples=["XAUUSD"])
    type: str = Field(..., examples=["BUY_LIMIT"], description="BUY_LIMIT, SELL_LIMIT, BUY_STOP, or SELL_STOP")
    volume: float = Field(..., gt=0, examples=[0.01])
    price: float = Field(..., gt=0, examples=[2330.0])
    sl: Optional[float] = Field(None, examples=[2320.0])
    tp: Optional[float] = Field(None, examples=[2350.0])
    comment: str = Field("esp32 pending", examples=["esp32 pending"])


class ModifyOrderRequest(BaseModel):
    ticket: int = Field(..., gt=0, examples=[123456789])
    price: Optional[float] = Field(None, gt=0, examples=[2331.0])
    sl: Optional[float] = Field(None, examples=[2321.0])
    tp: Optional[float] = Field(None, examples=[2351.0])


class TicketRequest(BaseModel):
    ticket: int = Field(..., gt=0, examples=[123456789])


class ModifyPositionRequest(BaseModel):
    ticket: int = Field(..., gt=0, examples=[123456789])
    sl: Optional[float] = Field(None, examples=[2325.0])
    tp: Optional[float] = Field(None, examples=[2365.0])


@app.on_event("startup")
def startup():
    global mt5_connected
    mt5_connected = mt5_client.connect()
    if not mt5_connected:
        print("Failed to connect to MT5. API will start, but MT5 endpoints may fail.")


@app.on_event("shutdown")
def shutdown():
    if mt5_connected:
        mt5_client.disconnect()


def require_api_key(api_key: Optional[str] = Security(api_key_header)):
    if not API_KEY:
        return error_response("API_KEY is not configured on the server", status=503)
    if api_key != API_KEY:
        return error_response("Unauthorized", status=401)
    return True


def ok_response(data=None, message="ok"):
    return {"ok": True, "message": message, "data": data or {}}


def error_response(message, details=None, status=400):
    return JSONResponse(
        status_code=status,
        content={"ok": False, "error": message, "details": details or {}},
    )


def handle_mt5_error(error, status=400):
    return error_response(str(error), getattr(error, "details", {}), status=status)


def endpoint_catalog():
    return {
        "status": "Server is running!",
        "docs_url": "/docs",
        "openapi_url": "/openapi.json",
        "base_url_local": "http://127.0.0.1:5000",
        "public_endpoints": [
            {"method": "GET", "path": "/", "description": "Health check and endpoint list"},
            {"method": "GET", "path": "/endpoints", "description": "Endpoint list"},
            {"method": "GET", "path": "/tick/XAUUSD", "description": "Latest bid/ask tick"},
            {
                "method": "GET",
                "path": "/candles/XAUUSD?timeframe=M1&count=10",
                "description": "OHLCV candles",
            },
            {"method": "GET", "path": "/all", "description": "Latest ticks for configured symbols"},
            {"method": "GET", "path": "/symbols", "description": "Configured symbol metadata"},
        ],
        "protected_endpoints": [
            {"method": "GET", "path": "/account", "description": "Demo account info"},
            {"method": "GET", "path": "/positions", "description": "Open positions"},
            {"method": "GET", "path": "/orders", "description": "Pending orders"},
            {"method": "POST", "path": "/order/market", "description": "Place market BUY/SELL order"},
            {"method": "POST", "path": "/order/pending", "description": "Place pending order"},
            {"method": "POST", "path": "/order/modify", "description": "Modify pending order"},
            {"method": "POST", "path": "/order/cancel", "description": "Cancel pending order"},
            {"method": "POST", "path": "/position/modify", "description": "Modify position SL/TP"},
            {"method": "POST", "path": "/position/close", "description": "Close position"},
        ],
        "auth": {"required_for": "protected_endpoints", "header": "X-API-Key"},
    }


@app.get("/", tags=["General"])
def index():
    return ok_response(endpoint_catalog())


@app.get("/endpoints", tags=["General"])
def endpoints():
    return ok_response(endpoint_catalog())


@app.get("/tick/{symbol}", tags=["Market Data"])
def tick(symbol: str):
    try:
        data = mt5_client.get_tick(symbol)
        if data:
            return ok_response(data)
        return error_response(f"Could not get tick for {symbol}", status=404)
    except mt5_client.MT5Error as error:
        return handle_mt5_error(error)


@app.get("/candles/{symbol}", tags=["Market Data"])
def candles(
    symbol: str,
    timeframe: str = Query("M1", description="M1, M5, M15, M30, H1, H4, D1"),
    count: int = Query(10, ge=1, le=MAX_CANDLES),
):
    try:
        data = mt5_client.get_candles(symbol, timeframe=timeframe, count=count)
        if data is not None:
            return ok_response(
                {
                    "symbol": symbol.upper(),
                    "timeframe": timeframe.upper(),
                    "count": len(data),
                    "candles": data,
                }
            )
        return error_response(f"Could not get candles for {symbol}", status=404)
    except mt5_client.MT5Error as error:
        return handle_mt5_error(error)


@app.get("/all", tags=["Market Data"])
def all_ticks():
    result = {}
    for symbol in SYMBOLS:
        try:
            tick_data = mt5_client.get_tick(symbol)
        except mt5_client.MT5Error:
            tick_data = None
        if tick_data:
            result[symbol] = tick_data
    return ok_response(result)


@app.get("/symbols", tags=["Market Data"])
def symbols():
    return ok_response(mt5_client.get_symbols(SYMBOLS))


@app.get("/account", tags=["Account"], dependencies=[Depends(require_api_key)])
def account():
    try:
        return ok_response(mt5_client.get_account())
    except mt5_client.MT5Error as error:
        return handle_mt5_error(error)


@app.get("/positions", tags=["Trading"], dependencies=[Depends(require_api_key)])
def positions(symbol: Optional[str] = Query(None)):
    try:
        return ok_response(mt5_client.get_positions(symbol))
    except mt5_client.MT5Error as error:
        return handle_mt5_error(error)


@app.get("/orders", tags=["Trading"], dependencies=[Depends(require_api_key)])
def orders(symbol: Optional[str] = Query(None)):
    try:
        return ok_response(mt5_client.get_orders(symbol))
    except mt5_client.MT5Error as error:
        return handle_mt5_error(error)


@app.post("/order/market", tags=["Trading"], dependencies=[Depends(require_api_key)])
def order_market(data: MarketOrderRequest):
    try:
        result = mt5_client.place_market_order(
            symbol=data.symbol,
            order_type=data.type,
            volume=data.volume,
            sl=data.sl,
            tp=data.tp,
            comment=data.comment,
        )
        return ok_response(result, message="market order sent")
    except mt5_client.MT5Error as error:
        return handle_mt5_error(error)


@app.post("/order/pending", tags=["Trading"], dependencies=[Depends(require_api_key)])
def order_pending(data: PendingOrderRequest):
    try:
        result = mt5_client.place_pending_order(
            symbol=data.symbol,
            order_type=data.type,
            volume=data.volume,
            price=data.price,
            sl=data.sl,
            tp=data.tp,
            comment=data.comment,
        )
        return ok_response(result, message="pending order placed")
    except mt5_client.MT5Error as error:
        return handle_mt5_error(error)


@app.post("/order/modify", tags=["Trading"], dependencies=[Depends(require_api_key)])
def order_modify(data: ModifyOrderRequest):
    try:
        result = mt5_client.modify_pending_order(
            ticket=data.ticket,
            price=data.price,
            sl=data.sl,
            tp=data.tp,
        )
        return ok_response(result, message="pending order modified")
    except mt5_client.MT5Error as error:
        return handle_mt5_error(error)


@app.post("/order/cancel", tags=["Trading"], dependencies=[Depends(require_api_key)])
def order_cancel(data: TicketRequest):
    try:
        result = mt5_client.cancel_order(data.ticket)
        return ok_response(result, message="pending order canceled")
    except mt5_client.MT5Error as error:
        return handle_mt5_error(error)


@app.post("/position/modify", tags=["Trading"], dependencies=[Depends(require_api_key)])
def position_modify(data: ModifyPositionRequest):
    try:
        result = mt5_client.modify_position(ticket=data.ticket, sl=data.sl, tp=data.tp)
        return ok_response(result, message="position modified")
    except mt5_client.MT5Error as error:
        return handle_mt5_error(error)


@app.post("/position/close", tags=["Trading"], dependencies=[Depends(require_api_key)])
def position_close(data: TicketRequest):
    try:
        result = mt5_client.close_position(data.ticket)
        return ok_response(result, message="position closed")
    except mt5_client.MT5Error as error:
        return handle_mt5_error(error)


if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host=FLASK_HOST,
        port=FLASK_PORT,
        reload=FLASK_DEBUG,
    )
