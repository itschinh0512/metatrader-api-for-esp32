import MetaTrader5 as mt5

if not mt5.initialize():
    print("MT5 init failed:", mt5.last_error())
    quit()

# Example: get latest price for XAUUSD
tick = mt5.symbol_info_tick("XAUUSD")
print("Bid:", tick.bid, "Ask:", tick.ask)

mt5.shutdown()