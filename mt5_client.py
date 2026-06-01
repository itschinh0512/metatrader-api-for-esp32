# mt5_client.py
import math

import MetaTrader5 as mt5

from config import (
    DEFAULT_DEVIATION,
    DEFAULT_LOT,
    DEFAULT_MAGIC,
    MT5_LOGIN,
    MT5_PASSWORD,
    MT5_SERVER,
)


TIMEFRAMES = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}

MARKET_TYPES = {
    "BUY": mt5.ORDER_TYPE_BUY,
    "SELL": mt5.ORDER_TYPE_SELL,
}

PENDING_TYPES = {
    "BUY_LIMIT": mt5.ORDER_TYPE_BUY_LIMIT,
    "SELL_LIMIT": mt5.ORDER_TYPE_SELL_LIMIT,
    "BUY_STOP": mt5.ORDER_TYPE_BUY_STOP,
    "SELL_STOP": mt5.ORDER_TYPE_SELL_STOP,
}

OK_RETCODES = {
    mt5.TRADE_RETCODE_DONE,
    mt5.TRADE_RETCODE_PLACED,
    mt5.TRADE_RETCODE_DONE_PARTIAL,
}


class MT5Error(Exception):
    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details or {}


def connect():
    if not mt5.initialize():
        print("MT5 initialize() failed, error:", mt5.last_error())
        return False

    if MT5_LOGIN and MT5_PASSWORD and MT5_SERVER:
        if not mt5.login(MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
            print("MT5 login() failed, error:", mt5.last_error())
            return False

    print("Connected to MT5 successfully!")
    return True


def get_tick(symbol):
    symbol = normalize_symbol(symbol)
    ensure_symbol(symbol)
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return None
    return {
        "symbol": symbol,
        "bid": float(tick.bid),
        "ask": float(tick.ask),
        "time": int(tick.time),
    }


def get_candles(symbol, timeframe="M1", count=10):
    symbol = normalize_symbol(symbol)
    ensure_symbol(symbol)
    mt5_timeframe = parse_timeframe(timeframe)
    rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, int(count))
    if rates is None:
        return None
    return [
        {
            "time": int(row["time"]),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": int(row["tick_volume"]),
        }
        for row in rates
    ]


def get_account():
    info = mt5.account_info()
    if info is None:
        raise MT5Error("Could not read account info", {"last_error": mt5.last_error()})
    data = info._asdict()
    return {
        "login": data.get("login"),
        "server": data.get("server"),
        "currency": data.get("currency"),
        "balance": data.get("balance"),
        "equity": data.get("equity"),
        "margin": data.get("margin"),
        "margin_free": data.get("margin_free"),
        "margin_level": data.get("margin_level"),
        "leverage": data.get("leverage"),
    }


def get_symbols(symbols):
    result = []
    for symbol in symbols:
        info = mt5.symbol_info(normalize_symbol(symbol))
        if info is None:
            result.append({"symbol": normalize_symbol(symbol), "available": False})
            continue

        data = info._asdict()
        result.append(
            {
                "symbol": data.get("name"),
                "available": True,
                "description": data.get("description"),
                "digits": data.get("digits"),
                "volume_min": data.get("volume_min"),
                "volume_max": data.get("volume_max"),
                "volume_step": data.get("volume_step"),
                "trade_mode": data.get("trade_mode"),
                "visible": data.get("visible"),
            }
        )
    return result


def get_positions(symbol=None):
    if symbol:
        positions = mt5.positions_get(symbol=normalize_symbol(symbol))
    else:
        positions = mt5.positions_get()
    if positions is None:
        raise MT5Error("Could not read positions", {"last_error": mt5.last_error()})
    return [serialize_position(position) for position in positions]


def get_orders(symbol=None):
    if symbol:
        orders = mt5.orders_get(symbol=normalize_symbol(symbol))
    else:
        orders = mt5.orders_get()
    if orders is None:
        raise MT5Error("Could not read orders", {"last_error": mt5.last_error()})
    return [serialize_order(order) for order in orders]


def place_market_order(symbol, order_type, volume, sl=None, tp=None, comment="esp32 market"):
    symbol = normalize_symbol(symbol)
    order_type = normalize_order_type(order_type, MARKET_TYPES)
    info = ensure_symbol(symbol)
    volume = validate_volume(volume, info)
    tick = require_tick(symbol)
    price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": round_price(price, info),
        "deviation": DEFAULT_DEVIATION,
        "magic": DEFAULT_MAGIC,
        "comment": safe_comment(comment),
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    add_optional_stops(request, info, sl, tp)
    return send_order(request)


def place_pending_order(
    symbol,
    order_type,
    volume,
    price,
    sl=None,
    tp=None,
    comment="esp32 pending",
):
    symbol = normalize_symbol(symbol)
    order_type = normalize_order_type(order_type, PENDING_TYPES)
    info = ensure_symbol(symbol)
    volume = validate_volume(volume, info)
    price = validate_price(price, info, "price")

    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": price,
        "deviation": DEFAULT_DEVIATION,
        "magic": DEFAULT_MAGIC,
        "comment": safe_comment(comment),
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }
    add_optional_stops(request, info, sl, tp)
    return send_order(request)


def modify_pending_order(ticket, price=None, sl=None, tp=None):
    ticket = validate_ticket(ticket)
    order = get_order_by_ticket(ticket)
    info = ensure_symbol(order.symbol)

    request = {
        "action": mt5.TRADE_ACTION_MODIFY,
        "order": ticket,
        "symbol": order.symbol,
        "price": validate_price(price if price is not None else order.price_open, info, "price"),
    }
    add_optional_stops(request, info, sl if sl is not None else order.sl, tp if tp is not None else order.tp)
    return send_order(request)


def cancel_order(ticket):
    ticket = validate_ticket(ticket)
    get_order_by_ticket(ticket)
    return send_order({"action": mt5.TRADE_ACTION_REMOVE, "order": ticket})


def modify_position(ticket, sl=None, tp=None):
    ticket = validate_ticket(ticket)
    position = get_position_by_ticket(ticket)
    info = ensure_symbol(position.symbol)

    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": ticket,
        "symbol": position.symbol,
    }
    add_optional_stops(request, info, sl if sl is not None else position.sl, tp if tp is not None else position.tp)
    return send_order(request)


def close_position(ticket):
    ticket = validate_ticket(ticket)
    position = get_position_by_ticket(ticket)
    info = ensure_symbol(position.symbol)
    tick = require_tick(position.symbol)

    if position.type == mt5.POSITION_TYPE_BUY:
        order_type = mt5.ORDER_TYPE_SELL
        price = tick.bid
    else:
        order_type = mt5.ORDER_TYPE_BUY
        price = tick.ask

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": ticket,
        "symbol": position.symbol,
        "volume": float(position.volume),
        "type": order_type,
        "price": round_price(price, info),
        "deviation": DEFAULT_DEVIATION,
        "magic": DEFAULT_MAGIC,
        "comment": "esp32 close",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    return send_order(request)


def disconnect():
    mt5.shutdown()
    print("MT5 disconnected.")


def normalize_symbol(symbol):
    if not symbol or not str(symbol).strip():
        raise MT5Error("Symbol is required")
    return str(symbol).strip().upper()


def parse_timeframe(timeframe):
    key = str(timeframe or "M1").upper()
    if key not in TIMEFRAMES:
        raise MT5Error("Invalid timeframe", {"allowed": sorted(TIMEFRAMES.keys())})
    return TIMEFRAMES[key]


def normalize_order_type(order_type, allowed):
    key = str(order_type or "").upper()
    if key not in allowed:
        raise MT5Error("Invalid order type", {"allowed": sorted(allowed.keys())})
    return allowed[key]


def ensure_symbol(symbol):
    info = mt5.symbol_info(symbol)
    if info is None:
        raise MT5Error("Unknown symbol", {"symbol": symbol})
    if not info.visible and not mt5.symbol_select(symbol, True):
        raise MT5Error("Could not select symbol", {"symbol": symbol, "last_error": mt5.last_error()})
    return info


def require_tick(symbol):
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise MT5Error("Could not read current tick", {"symbol": symbol, "last_error": mt5.last_error()})
    return tick


def validate_volume(volume, info):
    try:
        value = float(volume)
    except (TypeError, ValueError):
        raise MT5Error("Invalid volume", {"volume": volume})

    if value <= 0:
        raise MT5Error("Volume must be greater than zero", {"volume": value})
    if value < info.volume_min or value > info.volume_max:
        raise MT5Error(
            "Volume is outside broker limits",
            {
                "volume": value,
                "volume_min": info.volume_min,
                "volume_max": info.volume_max,
            },
        )

    steps = (value - info.volume_min) / info.volume_step
    if not math.isclose(steps, round(steps), abs_tol=1e-8):
        raise MT5Error(
            "Volume does not match broker step",
            {
                "volume": value,
                "volume_min": info.volume_min,
                "volume_step": info.volume_step,
            },
        )
    return float(value)


def validate_price(price, info, field):
    try:
        value = float(price)
    except (TypeError, ValueError):
        raise MT5Error(f"Invalid {field}", {field: price})
    if value <= 0:
        raise MT5Error(f"{field} must be greater than zero", {field: value})
    return round_price(value, info)


def validate_optional_price(price, info, field):
    if price in (None, "", 0, 0.0):
        return 0.0
    return validate_price(price, info, field)


def validate_ticket(ticket):
    try:
        value = int(ticket)
    except (TypeError, ValueError):
        raise MT5Error("Invalid ticket", {"ticket": ticket})
    if value <= 0:
        raise MT5Error("Ticket must be greater than zero", {"ticket": value})
    return value


def round_price(price, info):
    return round(float(price), int(info.digits))


def add_optional_stops(request, info, sl=None, tp=None):
    request["sl"] = validate_optional_price(sl, info, "sl")
    request["tp"] = validate_optional_price(tp, info, "tp")


def safe_comment(comment):
    value = str(comment or "")
    return value[:31] if value else "esp32"


def get_order_by_ticket(ticket):
    orders = mt5.orders_get(ticket=ticket)
    if not orders:
        raise MT5Error("Pending order not found", {"ticket": ticket})
    return orders[0]


def get_position_by_ticket(ticket):
    positions = mt5.positions_get(ticket=ticket)
    if not positions:
        raise MT5Error("Position not found", {"ticket": ticket})
    return positions[0]


def send_order(request):
    result = mt5.order_send(request)
    if result is None:
        raise MT5Error("MT5 order_send failed", {"last_error": mt5.last_error(), "request": request})

    data = serialize_result(result)
    data["ok"] = result.retcode in OK_RETCODES
    if not data["ok"]:
        raise MT5Error("MT5 rejected trade request", data)
    return data


def serialize_position(position):
    data = position._asdict()
    return {
        "ticket": data.get("ticket"),
        "symbol": data.get("symbol"),
        "type": "BUY" if data.get("type") == mt5.POSITION_TYPE_BUY else "SELL",
        "volume": data.get("volume"),
        "price_open": data.get("price_open"),
        "price_current": data.get("price_current"),
        "sl": data.get("sl"),
        "tp": data.get("tp"),
        "profit": data.get("profit"),
        "time": data.get("time"),
        "comment": data.get("comment"),
    }


def serialize_order(order):
    data = order._asdict()
    return {
        "ticket": data.get("ticket"),
        "symbol": data.get("symbol"),
        "type": order_type_name(data.get("type")),
        "volume_initial": data.get("volume_initial"),
        "volume_current": data.get("volume_current"),
        "price_open": data.get("price_open"),
        "sl": data.get("sl"),
        "tp": data.get("tp"),
        "time_setup": data.get("time_setup"),
        "comment": data.get("comment"),
    }


def order_type_name(value):
    names = {
        mt5.ORDER_TYPE_BUY: "BUY",
        mt5.ORDER_TYPE_SELL: "SELL",
        mt5.ORDER_TYPE_BUY_LIMIT: "BUY_LIMIT",
        mt5.ORDER_TYPE_SELL_LIMIT: "SELL_LIMIT",
        mt5.ORDER_TYPE_BUY_STOP: "BUY_STOP",
        mt5.ORDER_TYPE_SELL_STOP: "SELL_STOP",
    }
    return names.get(value, str(value))


def serialize_result(result):
    data = result._asdict()
    request = data.get("request")
    if hasattr(request, "_asdict"):
        data["request"] = request._asdict()
    return data
