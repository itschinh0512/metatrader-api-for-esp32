# Bao cao du an Web API MetaTrader 5 - ESP32

Ngay lap: 2026-05-28

Cap nhat 2026-06-01: Cac uu tien trong bao cao da duoc thuc hien trong code. Project hien co them cau hinh qua `.env`, API key cho endpoint nhay cam, OHLCV candles voi query params, va cac endpoint giao dich: xem account, positions, orders, dat market order, dat pending order, sua pending order, huy pending order, sua SL/TP position, va dong position. Xem `README.md` de lay contract API moi nhat.

## 1. Muc tieu du an

Du an hien tai la mot Web API trung gian giua MetaTrader 5 (MT5) tren may tinh va thiet bi ESP32. Y tuong chinh:

- May tinh chay Python Flask server.
- Python ket noi den MT5 bang thu vien `MetaTrader5`.
- ESP32 goi HTTP API den Flask server de lay du lieu gia hoac gui lenh giao dich.
- MT5 la noi thuc thi lenh that tren tai khoan demo/live.

Hien tai project moi lam phan doc du lieu thi truong. Phan giao dich nhu pending order va modify stop loss/take profit chua duoc code.

## 2. Cau truc file hien tai

| File | Vai tro |
| --- | --- |
| `server.py` | Flask web server, dinh nghia cac API endpoint. |
| `mt5_client.py` | Lop ham lam viec voi MetaTrader5: connect, lay tick, lay candles, disconnect. |
| `config.py` | Cau hinh tai khoan MT5, Flask host/port, danh sach symbol. |
| `test.py` | Script test nhanh viec ket noi MT5 va lay gia XAUUSD. |

Virtual environment `.venv` da co Python 3.10, Flask va MetaTrader5.

## 3. API hien co

### `GET /`

Kiem tra server Flask co dang chay khong.

Response mau:

```json
{
  "status": "Server is running!"
}
```

### `GET /tick/<symbol>`

Lay gia bid/ask moi nhat cua mot symbol.

Vi du:

```text
GET /tick/XAUUSD
```

Response mau:

```json
{
  "symbol": "XAUUSD",
  "bid": 2345.12,
  "ask": 2345.42,
  "time": 1712000000
}
```

### `GET /candles/<symbol>`

Lay 10 nen M1 gan nhat cua symbol.

Vi du:

```text
GET /candles/EURUSD
```

Response mau:

```json
[
  {
    "time": 1712000000,
    "open": 1.085,
    "high": 1.086,
    "low": 1.084,
    "close": 1.0855,
    "volume": 123
  }
]
```

### `GET /all`

Lay tick moi nhat cua cac symbol trong `SYMBOLS`, hien la:

```text
EURUSD, GBPUSD, XAUUSD
```

## 4. Cach du lieu di chuyen trong he thong

```text
ESP32
  |
  | HTTP request qua Wi-Fi
  v
Flask API tren PC: server.py
  |
  | Goi ham trong mt5_client.py
  v
MetaTrader5 Python package
  |
  | Noi voi MT5 terminal dang chay tren PC
  v
Tai khoan MT5 / broker server
```

## 5. Trang thai hien tai

Da co:

- Server Flask chay o `0.0.0.0:5000`, nen ESP32 co the truy cap bang IP LAN cua may tinh.
- API health check.
- API lay tick theo symbol.
- API lay candles M1.
- API lay tick cho nhieu symbol.
- Script test doc gia XAUUSD.

Chua co:

- API dat lenh market.
- API dat pending order.
- API sua stop loss / take profit.
- API huy pending order.
- API dong position.
- API xem danh sach position/order.
- API key hoac co che bao ve endpoint giao dich.
- Validate request body cho ESP32.
- File `requirements.txt`.
- Huong dan chay project.

## 6. Yeu cau cua ban trong tin nhan va doi chieu voi project

Ban cua minh nhac cac y chinh:

- "Pending order": can lam API dat lenh cho BUY LIMIT, SELL LIMIT, BUY STOP, SELL STOP.
- "Modify stop loss voi profit": can lam API sua SL/TP cho position dang mo.
- "Doc coi co nao quan trong lam het": can doc cac chuc nang giao dich quan trong cua MT5 va chon nhung API can thiet cho workflow ESP32.
- "Kh thi pick ra mot danh sach gui ban coi": neu khong lam het ngay thi tao danh sach uu tien de ban duyet.

Ket luan: project hien tai chua dap ung duoc phan ban ay dang can. Viec can lam tiep la mo rong tu API doc du lieu sang API trade management.

## 7. Danh sach viec nen lam ngay

### Uu tien 1: Bao mat va chuan hoa project

1. Chuyen thong tin login/password MT5 ra file `.env` hoac bien moi truong.
2. Doi password tai khoan demo/live neu file nay tung duoc gui cho nguoi khac.
3. Them API key don gian cho cac endpoint trade, vi ESP32 co the gui header `X-API-Key`.
4. Tao `requirements.txt` de cai dat lai moi truong de hon.
5. Viet README cach chay server va cach ESP32 goi API.

### Uu tien 2: Them API quan trong cho giao dich

Nen lam cac endpoint sau:

| Endpoint | Method | Muc dich |
| --- | --- | --- |
| `/account` | GET | Xem thong tin tai khoan: balance, equity, margin. |
| `/symbols` | GET | Xem danh sach symbol dang theo doi. |
| `/positions` | GET | Xem cac lenh dang mo. |
| `/orders` | GET | Xem cac pending orders. |
| `/order/market` | POST | Dat lenh market BUY/SELL. |
| `/order/pending` | POST | Dat pending order. |
| `/order/modify` | POST | Sua pending order: price, SL, TP. |
| `/position/modify` | POST | Sua SL/TP cua position dang mo. |
| `/order/cancel` | POST | Huy pending order. |
| `/position/close` | POST | Dong position. |

### Uu tien 3: Test voi demo account

1. Test tren symbol XAUUSD truoc.
2. Test lot nho nhat broker cho phep.
3. Log lai request/response cua moi lenh trade.
4. Kiem tra cac loi MT5 hay gap: invalid volume, invalid stops, market closed, symbol not found, trade disabled.
5. Sau khi demo on dinh moi can nhac live account.

## 8. De xuat format API cho ESP32

### Dat pending order

Endpoint:

```text
POST /order/pending
```

Body:

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

Response nen co:

```json
{
  "ok": true,
  "order": 123456789,
  "retcode": 10009,
  "message": "order placed"
}
```

### Sua stop loss / take profit cua position

Endpoint:

```text
POST /position/modify
```

Body:

```json
{
  "ticket": 123456789,
  "sl": 2325.0,
  "tp": 2360.0
}
```

Response nen co:

```json
{
  "ok": true,
  "ticket": 123456789,
  "retcode": 10009,
  "message": "position modified"
}
```

### Huy pending order

Endpoint:

```text
POST /order/cancel
```

Body:

```json
{
  "ticket": 123456789
}
```

## 9. Cac ham MT5 can dung

Trong `MetaTrader5` Python package, cac ham quan trong can dung tiep:

- `mt5.account_info()` de lay thong tin tai khoan.
- `mt5.symbol_info()` de lay thong tin symbol, digits, volume min/max/step.
- `mt5.positions_get()` de lay position dang mo.
- `mt5.orders_get()` de lay pending orders.
- `mt5.order_send()` de dat, sua, huy, dong lenh.
- `mt5.last_error()` de debug khi request loi.

Cac action/type MT5 can map:

- Market order: `TRADE_ACTION_DEAL`
- Pending order: `TRADE_ACTION_PENDING`
- Modify pending order: `TRADE_ACTION_MODIFY`
- Modify SL/TP position: `TRADE_ACTION_SLTP`
- Remove pending order: `TRADE_ACTION_REMOVE`
- Buy limit: `ORDER_TYPE_BUY_LIMIT`
- Sell limit: `ORDER_TYPE_SELL_LIMIT`
- Buy stop: `ORDER_TYPE_BUY_STOP`
- Sell stop: `ORDER_TYPE_SELL_STOP`

## 10. Rui ro can noi ro voi ban

- Day la API co kha nang dat lenh that, nen khong duoc mo public internet.
- Neu Flask chay `0.0.0.0`, tat ca thiet bi cung mang LAN co the thay server neu firewall cho phep.
- Endpoint trade bat buoc nen co API key.
- Can validate volume, price, SL, TP truoc khi gui lenh.
- Can dung demo account de test.
- `config.py` hien dang chua thong tin dang nhap MT5, khong nen commit/gui file nay.

## 11. Tin nhan co the gui lai cho ban

> Minh doc lai project roi. Hien tai code moi co web API Flask doc du lieu tu MT5: health check, lay tick, lay candles va lay tick cho cac symbol EURUSD/GBPUSD/XAUUSD. Phan ban can nhu pending order va modify stop loss/take profit chua co.
>
> De dap ung dung yeu cau, minh se lam them cac API uu tien: xem account, xem positions/orders, dat pending order, sua SL/TP cho position, sua/huy pending order, va co the them market order/close position neu can. Truoc khi lam trade endpoint minh se them API key va chuyen password MT5 ra env de an toan hon. Minh se test tren demo account voi lot nho truoc.
>
> Neu ban muon, minh gui truoc danh sach endpoint de ban duyet: `/order/pending`, `/position/modify`, `/order/modify`, `/order/cancel`, `/positions`, `/orders`, `/account`.

## 12. Ket luan

Project hien tai la nen tang tot cho viec ESP32 doc gia tu MT5, nhung chua hoan thanh yeu cau giao dich. Viec nen lam bay gio la:

1. Bao mat cau hinh va them API key.
2. Them cac API trade quan trong, bat dau voi pending order va modify SL/TP.
3. Them API xem orders/positions de ESP32 biet trang thai lenh.
4. Test ky tren demo account.
5. Viet README va danh sach endpoint de ban cua minh test cung.
