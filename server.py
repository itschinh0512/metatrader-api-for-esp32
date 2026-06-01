# server.py
from functools import wraps

from flask import Flask, jsonify, request

import mt5_client
from config import API_KEY, FLASK_DEBUG, FLASK_HOST, FLASK_PORT, MAX_CANDLES, SYMBOLS


app = Flask(__name__)


def require_api_key(handler):
    @wraps(handler)
    def wrapper(*args, **kwargs):
        if not API_KEY:
            return error_response("API_KEY is not configured on the server", status=503)
        if request.headers.get("X-API-Key") != API_KEY:
            return error_response("Unauthorized", status=401)
        return handler(*args, **kwargs)

    return wrapper


def json_body():
    data = request.get_json(silent=True)
    if data is None:
        raise mt5_client.MT5Error("JSON body is required")
    return data


def ok_response(data=None, message="ok", status=200):
    return jsonify({"ok": True, "message": message, "data": data or {}}), status


def error_response(message, details=None, status=400):
    return jsonify({"ok": False, "error": message, "details": details or {}}), status


def handle_mt5_error(error, status=400):
    return error_response(str(error), getattr(error, "details", {}), status=status)


def parse_count(value):
    try:
        count = int(value)
    except (TypeError, ValueError):
        raise mt5_client.MT5Error("Invalid count", {"count": value})
    if count < 1 or count > MAX_CANDLES:
        raise mt5_client.MT5Error("Count is outside allowed range", {"min": 1, "max": MAX_CANDLES})
    return count


@app.route("/")
def index():
    return ok_response({"status": "Server is running!"})


@app.route("/tick/<symbol>")
def tick(symbol):
    try:
        data = mt5_client.get_tick(symbol)
        if data:
            return ok_response(data)
        return error_response(f"Could not get tick for {symbol}", status=404)
    except mt5_client.MT5Error as error:
        return handle_mt5_error(error)


@app.route("/candles/<symbol>")
def candles(symbol):
    try:
        timeframe = request.args.get("timeframe", "M1")
        count = parse_count(request.args.get("count", 10))
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


@app.route("/all")
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


@app.route("/symbols")
def symbols():
    return ok_response(mt5_client.get_symbols(SYMBOLS))


@app.route("/account")
@require_api_key
def account():
    try:
        return ok_response(mt5_client.get_account())
    except mt5_client.MT5Error as error:
        return handle_mt5_error(error)


@app.route("/positions")
@require_api_key
def positions():
    try:
        return ok_response(mt5_client.get_positions(request.args.get("symbol")))
    except mt5_client.MT5Error as error:
        return handle_mt5_error(error)


@app.route("/orders")
@require_api_key
def orders():
    try:
        return ok_response(mt5_client.get_orders(request.args.get("symbol")))
    except mt5_client.MT5Error as error:
        return handle_mt5_error(error)


@app.route("/order/market", methods=["POST"])
@require_api_key
def order_market():
    try:
        data = json_body()
        result = mt5_client.place_market_order(
            symbol=data.get("symbol"),
            order_type=data.get("type"),
            volume=data.get("volume"),
            sl=data.get("sl"),
            tp=data.get("tp"),
            comment=data.get("comment", "esp32 market"),
        )
        return ok_response(result, message="market order sent")
    except mt5_client.MT5Error as error:
        return handle_mt5_error(error)


@app.route("/order/pending", methods=["POST"])
@require_api_key
def order_pending():
    try:
        data = json_body()
        result = mt5_client.place_pending_order(
            symbol=data.get("symbol"),
            order_type=data.get("type"),
            volume=data.get("volume"),
            price=data.get("price"),
            sl=data.get("sl"),
            tp=data.get("tp"),
            comment=data.get("comment", "esp32 pending"),
        )
        return ok_response(result, message="pending order placed")
    except mt5_client.MT5Error as error:
        return handle_mt5_error(error)


@app.route("/order/modify", methods=["POST"])
@require_api_key
def order_modify():
    try:
        data = json_body()
        result = mt5_client.modify_pending_order(
            ticket=data.get("ticket"),
            price=data.get("price"),
            sl=data.get("sl"),
            tp=data.get("tp"),
        )
        return ok_response(result, message="pending order modified")
    except mt5_client.MT5Error as error:
        return handle_mt5_error(error)


@app.route("/order/cancel", methods=["POST"])
@require_api_key
def order_cancel():
    try:
        data = json_body()
        result = mt5_client.cancel_order(data.get("ticket"))
        return ok_response(result, message="pending order canceled")
    except mt5_client.MT5Error as error:
        return handle_mt5_error(error)


@app.route("/position/modify", methods=["POST"])
@require_api_key
def position_modify():
    try:
        data = json_body()
        result = mt5_client.modify_position(
            ticket=data.get("ticket"),
            sl=data.get("sl"),
            tp=data.get("tp"),
        )
        return ok_response(result, message="position modified")
    except mt5_client.MT5Error as error:
        return handle_mt5_error(error)


@app.route("/position/close", methods=["POST"])
@require_api_key
def position_close():
    try:
        data = json_body()
        result = mt5_client.close_position(data.get("ticket"))
        return ok_response(result, message="position closed")
    except mt5_client.MT5Error as error:
        return handle_mt5_error(error)


if __name__ == "__main__":
    if mt5_client.connect():
        app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
    else:
        print("Failed to connect to MT5. Exiting.")
