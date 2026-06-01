# Báo cáo kỹ thuật và hướng dẫn test API MT5 - ESP32

Ngày cập nhật: 2026-06-01

## 1. Tổng quan dự án

Dự án này là một Web API trung gian giữa MetaTrader 5 và ESP32.

Luồng hoạt động:

```text
ESP32
  -> gọi HTTP qua Wi-Fi/LAN
  -> Flask API chạy trên máy tính
  -> thư viện MetaTrader5 Python
  -> MT5 terminal đang đăng nhập tài khoản demo
  -> broker demo server
```

Mục tiêu hiện tại:

- ESP32 đọc dữ liệu giá từ MT5.
- ESP32 lấy dữ liệu nến OHLCV: open, high, low, close, volume.
- ESP32 có thể quản lý lệnh demo: đặt market order, đặt pending order, sửa SL/TP, hủy pending order, đóng position.
- API có `X-API-Key` cho các endpoint nhạy cảm.

## 2. Cấu trúc file chính

| File | Vai trò |
| --- | --- |
| `server.py` | Flask server, định nghĩa HTTP endpoint. |
| `mt5_client.py` | Logic kết nối MT5, đọc dữ liệu, gửi/sửa/hủy lệnh. |
| `config.py` | Đọc cấu hình từ `.env`. |
| `.env.example` | Mẫu cấu hình local. |
| `requirements.txt` | Danh sách thư viện Python cần cài. |
| `README.md` | Tài liệu API ngắn gọn. |

## 3. Cấu hình cần chuẩn bị

Tạo file `.env` từ `.env.example`.

Nội dung mẫu:

```env
MT5_LOGIN=
MT5_PASSWORD=
MT5_SERVER=ICMarkets-Demo

API_KEY=test-api-key-123

FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=false

SYMBOLS=EURUSD,GBPUSD,XAUUSD
MAX_CANDLES=500
DEFAULT_DEVIATION=20
DEFAULT_MAGIC=20260601
DEFAULT_LOT=0.01
```

Ghi chú:

- Nếu MT5 terminal đã mở và đã login demo account, có thể để trống `MT5_LOGIN` và `MT5_PASSWORD`.
- Nếu muốn Python login trực tiếp, điền `MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER`.
- `API_KEY` là khóa ESP32 phải gửi khi gọi endpoint giao dịch.
- Không gửi file `.env` cho người khác.

## 4. Danh sách endpoint

### Endpoint không cần API key

| Method | Endpoint | Mục đích |
| --- | --- | --- |
| GET | `/` | Kiểm tra server chạy. |
| GET | `/tick/<symbol>` | Lấy bid/ask mới nhất. |
| GET | `/candles/<symbol>?timeframe=M1&count=50` | Lấy dữ liệu OHLCV. |
| GET | `/all` | Lấy tick của các symbol trong config. |
| GET | `/symbols` | Xem symbol đang cấu hình. |

### Endpoint cần API key

Các endpoint dưới đây cần header:

```text
X-API-Key: test-api-key-123
```

| Method | Endpoint | Mục đích |
| --- | --- | --- |
| GET | `/account` | Xem thông tin tài khoản demo. |
| GET | `/positions` | Xem position đang mở. |
| GET | `/orders` | Xem pending order. |
| POST | `/order/market` | Đặt lệnh market BUY/SELL. |
| POST | `/order/pending` | Đặt pending order. |
| POST | `/order/modify` | Sửa pending order. |
| POST | `/order/cancel` | Hủy pending order. |
| POST | `/position/modify` | Sửa SL/TP của position. |
| POST | `/position/close` | Đóng position. |

## 5. Cách chạy API trên máy tính

Mở PowerShell tại thư mục dự án:

```powershell
cd C:\Users\itsch\OneDrive\Documents\test_metatrader
```

Cài thư viện nếu cần:

```powershell
.\.venv\Scripts\pip.exe install -r requirements.txt
```

Chạy server:

```powershell
.\.venv\Scripts\python.exe server.py
```

Nếu chạy thành công, Flask sẽ lắng nghe ở:

```text
http://127.0.0.1:5000
http://<IP-LAN-của-máy-tính>:5000
```

Không tắt cửa sổ PowerShell đang chạy server trong lúc test.

## 6. Cách test từng bước trước khi dùng ESP32

Mở một cửa sổ PowerShell thứ hai để test.

### Bước 1: Test server sống

```powershell
Invoke-RestMethod http://127.0.0.1:5000/
```

Kỳ vọng:

```json
{
  "ok": true,
  "message": "ok",
  "data": {
    "status": "Server is running!"
  }
}
```

### Bước 2: Test lấy tick

```powershell
Invoke-RestMethod http://127.0.0.1:5000/tick/XAUUSD
```

Kỳ vọng:

- Có `bid`.
- Có `ask`.
- Có `time`.
- `ok = true`.

Nếu lỗi symbol, kiểm tra trong MT5 Market Watch có symbol `XAUUSD` hay không. Một số broker dùng tên khác như `XAUUSDm`, `GOLD`, `XAUUSD.`.

### Bước 3: Test lấy OHLCV nến M1

```powershell
Invoke-RestMethod "http://127.0.0.1:5000/candles/XAUUSD?timeframe=M1&count=10"
```

Kỳ vọng:

- `data.symbol = XAUUSD`
- `data.timeframe = M1`
- `data.count = 10`
- `data.candles` là danh sách nến.
- Mỗi nến có:
  - `time`
  - `open`
  - `high`
  - `low`
  - `close`
  - `volume`

Lưu ý: `volume` ở đây là tick volume của MT5, phù hợp với forex/CFD demo.

### Bước 4: Test timeframe khác

```powershell
Invoke-RestMethod "http://127.0.0.1:5000/candles/XAUUSD?timeframe=M5&count=20"
Invoke-RestMethod "http://127.0.0.1:5000/candles/XAUUSD?timeframe=H1&count=50"
```

Timeframe hỗ trợ:

```text
M1, M5, M15, M30, H1, H4, D1
```

### Bước 5: Test lỗi validation của candles

```powershell
Invoke-RestMethod "http://127.0.0.1:5000/candles/XAUUSD?timeframe=BAD&count=10"
```

Kỳ vọng: API trả lỗi `Invalid timeframe`.

```powershell
Invoke-RestMethod "http://127.0.0.1:5000/candles/XAUUSD?timeframe=M1&count=999999"
```

Kỳ vọng: API trả lỗi `Count is outside allowed range`.

### Bước 6: Test API key

Không gửi API key:

```powershell
Invoke-RestMethod http://127.0.0.1:5000/account
```

Kỳ vọng:

- Nếu chưa cấu hình `.env`: lỗi `API_KEY is not configured on the server`.
- Nếu đã cấu hình `.env`: lỗi `Unauthorized`.

Gửi API key đúng:

```powershell
$headers = @{ "X-API-Key" = "test-api-key-123" }
Invoke-RestMethod http://127.0.0.1:5000/account -Headers $headers
```

Kỳ vọng:

- Có `balance`.
- Có `equity`.
- Có `margin`.
- Có `server`.
- Đây là tài khoản demo.

### Bước 7: Test danh sách positions và orders

```powershell
$headers = @{ "X-API-Key" = "test-api-key-123" }
Invoke-RestMethod http://127.0.0.1:5000/positions -Headers $headers
Invoke-RestMethod http://127.0.0.1:5000/orders -Headers $headers
```

Kỳ vọng:

- Nếu chưa có lệnh: `data` là danh sách rỗng.
- Nếu có lệnh: `data` chứa ticket, symbol, type, volume, SL, TP.

## 7. Test giao dịch demo bằng API

Chỉ làm phần này sau khi các bước đọc dữ liệu ở trên đã chạy ổn.

### Bước 8: Đặt pending order demo

Chọn giá pending hợp lý so với giá hiện tại. Ví dụ nếu XAUUSD đang ở 2350, có thể đặt `BUY_LIMIT` thấp hơn giá hiện tại.

```powershell
$headers = @{
  "X-API-Key" = "test-api-key-123"
  "Content-Type" = "application/json"
}

$body = @{
  symbol = "XAUUSD"
  type = "BUY_LIMIT"
  volume = 0.01
  price = 2330.0
  sl = 2320.0
  tp = 2350.0
  comment = "api pending test"
} | ConvertTo-Json

Invoke-RestMethod http://127.0.0.1:5000/order/pending -Method POST -Headers $headers -Body $body
```

Kỳ vọng:

- `ok = true`
- Có `retcode`
- Có thông tin order/ticket trong `data`

Nếu lỗi `Invalid stops`, `Invalid price`, hoặc broker từ chối, điều chỉnh `price`, `sl`, `tp` cho xa giá hiện tại hơn.

### Bước 9: Kiểm tra pending order vừa tạo

```powershell
Invoke-RestMethod http://127.0.0.1:5000/orders -Headers $headers
```

Ghi lại `ticket` của pending order.

### Bước 10: Sửa pending order

Thay `123456789` bằng ticket thật.

```powershell
$body = @{
  ticket = 123456789
  price = 2331.0
  sl = 2321.0
  tp = 2351.0
} | ConvertTo-Json

Invoke-RestMethod http://127.0.0.1:5000/order/modify -Method POST -Headers $headers -Body $body
```

### Bước 11: Hủy pending order

```powershell
$body = @{
  ticket = 123456789
} | ConvertTo-Json

Invoke-RestMethod http://127.0.0.1:5000/order/cancel -Method POST -Headers $headers -Body $body
```

Kiểm tra lại:

```powershell
Invoke-RestMethod http://127.0.0.1:5000/orders -Headers $headers
```

### Bước 12: Test market order demo

Chỉ dùng lot nhỏ nhất, ví dụ `0.01`.

```powershell
$body = @{
  symbol = "XAUUSD"
  type = "BUY"
  volume = 0.01
  sl = 2320.0
  tp = 2360.0
  comment = "api market test"
} | ConvertTo-Json

Invoke-RestMethod http://127.0.0.1:5000/order/market -Method POST -Headers $headers -Body $body
```

Sau đó xem position:

```powershell
Invoke-RestMethod http://127.0.0.1:5000/positions -Headers $headers
```

Ghi lại `ticket` của position.

### Bước 13: Sửa SL/TP của position

```powershell
$body = @{
  ticket = 123456789
  sl = 2325.0
  tp = 2365.0
} | ConvertTo-Json

Invoke-RestMethod http://127.0.0.1:5000/position/modify -Method POST -Headers $headers -Body $body
```

### Bước 14: Đóng position

```powershell
$body = @{
  ticket = 123456789
} | ConvertTo-Json

Invoke-RestMethod http://127.0.0.1:5000/position/close -Method POST -Headers $headers -Body $body
```

Kiểm tra lại:

```powershell
Invoke-RestMethod http://127.0.0.1:5000/positions -Headers $headers
```

## 8. Test qua IP LAN trước khi dùng ESP32

Lấy IP máy tính:

```powershell
ipconfig
```

Tìm IPv4 của Wi-Fi hoặc Ethernet, ví dụ:

```text
192.168.1.20
```

Test từ chính máy tính bằng IP LAN:

```powershell
Invoke-RestMethod http://192.168.1.20:5000/
Invoke-RestMethod "http://192.168.1.20:5000/candles/XAUUSD?timeframe=M1&count=10"
```

Nếu không truy cập được:

- Kiểm tra Flask có chạy với `FLASK_HOST=0.0.0.0`.
- Kiểm tra Windows Firewall có chặn port `5000`.
- Kiểm tra máy tính và ESP32 cùng mạng Wi-Fi.
- Không dùng `127.0.0.1` trên ESP32, vì `127.0.0.1` trên ESP32 là chính ESP32, không phải máy tính.

## 9. Checklist trước khi chuyển sang ESP32

Chỉ chuyển sang code ESP32 khi tất cả mục dưới đây đã đạt:

- `GET /` chạy thành công.
- `GET /tick/XAUUSD` trả bid/ask.
- `GET /candles/XAUUSD?timeframe=M1&count=10` trả đúng OHLCV.
- `GET /account` chạy được với `X-API-Key`.
- `GET /positions` và `GET /orders` chạy được.
- Đặt, sửa, hủy pending order demo thành công.
- Đặt market order demo với lot nhỏ thành công.
- Sửa SL/TP position demo thành công.
- Đóng position demo thành công.
- Test bằng IP LAN của máy tính thành công.

## 10. Format ESP32 cần gửi

### Request GET candles

```text
GET http://<PC_IP>:5000/candles/XAUUSD?timeframe=M1&count=10
```

### Header cho endpoint trade

```text
X-API-Key: test-api-key-123
Content-Type: application/json
```

### Body đặt pending order

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

### Body sửa SL/TP position

```json
{
  "ticket": 123456789,
  "sl": 2325.0,
  "tp": 2365.0
}
```

## 11. Lỗi thường gặp

| Lỗi | Nguyên nhân thường gặp | Cách xử lý |
| --- | --- | --- |
| `API_KEY is not configured` | Chưa tạo `.env` hoặc chưa set `API_KEY`. | Tạo `.env`, set `API_KEY`, chạy lại server. |
| `Unauthorized` | Sai hoặc thiếu `X-API-Key`. | Kiểm tra header. |
| `Unknown symbol` | Broker dùng tên symbol khác. | Kiểm tra Market Watch trong MT5. |
| `Invalid timeframe` | Timeframe không nằm trong danh sách hỗ trợ. | Dùng `M1`, `M5`, `M15`, `M30`, `H1`, `H4`, `D1`. |
| `Volume is outside broker limits` | Lot nhỏ/lớn hơn broker cho phép. | Kiểm tra `volume_min`, dùng `0.01` nếu được. |
| `Volume does not match broker step` | Lot không đúng bước nhảy. | Dùng lot theo `volume_step`, ví dụ `0.01`. |
| `MT5 rejected trade request` | Broker từ chối lệnh. | Xem `retcode`, kiểm tra market open, price, SL/TP. |
| Không truy cập được từ ESP32 | Sai IP hoặc firewall chặn. | Test bằng IP LAN trước, mở port 5000 nếu cần. |

## 12. Kết luận

API hiện đã đủ để test toàn bộ luồng trước khi đưa lên ESP32:

1. Đọc tick.
2. Đọc OHLCV candles.
3. Xem account.
4. Xem orders/positions.
5. Đặt pending order.
6. Sửa pending order.
7. Hủy pending order.
8. Đặt market order.
9. Sửa SL/TP position.
10. Đóng position.

Sau khi các bước PowerShell chạy ổn bằng IP LAN, ESP32 chỉ cần gọi cùng endpoint, cùng header, cùng JSON body.
