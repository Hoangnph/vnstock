# CII Intraday Service

Service tự động lấy thông tin giao dịch CII theo mốc 5 phút trong phiên giao dịch.

## Tính năng

- ✅ Tự động lấy dữ liệu CII mỗi 5 phút trong giờ giao dịch
- ✅ Hỗ trợ giờ giao dịch VN (9:00-11:30, 13:00-15:00)
- ✅ Lưu dữ liệu vào JSON và CSV
- ✅ Logging chi tiết
- ✅ Xử lý lỗi và retry
- ✅ Dừng service gracefully

## Cài đặt

```bash
# Cài đặt dependencies
pip install -r requirements.txt

# Hoặc cài đặt thủ công
pip install vnstock pandas
```

## Sử dụng

### Chạy service trực tiếp

```bash
# Chạy service
python cii_intraday_service.py

# Hoặc sử dụng runner
python run_service.py
```

### Chạy service trong background

```bash
# Chạy trong background
nohup python run_service.py > service.log 2>&1 &

# Xem log
tail -f service.log
```

### Dừng service

```bash
# Tìm process ID
ps aux | grep cii_intraday

# Dừng service
kill <PID>

# Hoặc dùng pkill
pkill -f cii_intraday
```

## Cấu trúc thư mục

```
fastapi/services/
├── cii_intraday_service.py    # Service chính
├── run_service.py             # Script chạy service
├── requirements.txt           # Dependencies
├── README.md                  # Tài liệu
├── data/                      # Dữ liệu lưu trữ
│   ├── CII_intraday_2025-01-26.json
│   └── CII_intraday_2025-01-26.csv
└── logs/                      # Log files
    └── cii_intraday.log
```

## Cấu hình

### Thay đổi symbol

```python
# Trong cii_intraday_service.py
service = CIIIntradayService(symbol="VIC", interval="5m")
```

### Thay đổi interval

```python
# Các interval hỗ trợ: 1m, 5m, 15m, 30m, 1H
service = CIIIntradayService(symbol="CII", interval="15m")
```

### Thay đổi thời gian giao dịch

```python
# Trong class CIIIntradayService
self.market_open = time(9, 0)      # 9:00 AM
self.market_close = time(15, 0)    # 3:00 PM
self.lunch_start = time(11, 30)    # 11:30 AM
self.lunch_end = time(13, 0)       # 1:00 PM
```

## Dữ liệu output

### JSON Format

```json
{
  "time": "2025-01-26T09:05:00",
  "open": 45000,
  "high": 45200,
  "low": 44900,
  "close": 45100,
  "volume": 150000,
  "symbol": "CII",
  "interval": "5m",
  "fetch_time": "2025-01-26T09:05:30.123456",
  "data_source": "vci"
}
```

### CSV Format

| time | open | high | low | close | volume | symbol | interval | fetch_time | data_source |
|------|------|------|-----|-------|--------|--------|----------|------------|-------------|
| 2025-01-26T09:05:00 | 45000 | 45200 | 44900 | 45100 | 150000 | CII | 5m | 2025-01-26T09:05:30.123456 | vci |

## Monitoring

### Xem log real-time

```bash
tail -f fastapi/services/logs/cii_intraday.log
```

### Kiểm tra dữ liệu

```bash
# Xem dữ liệu JSON
cat fastapi/services/data/CII_intraday_2025-01-26.json | jq '.[-1]'

# Xem dữ liệu CSV
tail -5 fastapi/services/data/CII_intraday_2025-01-26.csv
```

### Kiểm tra service status

```bash
# Kiểm tra process
ps aux | grep cii_intraday

# Kiểm tra port (nếu có)
netstat -tlnp | grep :8000
```

## Troubleshooting

### Lỗi thường gặp

1. **ModuleNotFoundError: No module named 'vnstock'**
   ```bash
   pip install vnstock
   ```

2. **Permission denied khi tạo thư mục**
   ```bash
   chmod 755 fastapi/services/
   ```

3. **Service không lấy được dữ liệu**
   - Kiểm tra kết nối internet
   - Kiểm tra API key VCI
   - Xem log để biết lỗi chi tiết

### Debug mode

```python
# Thêm vào đầu file
import logging
logging.basicConfig(level=logging.DEBUG)
```

## API Integration

Service có thể được tích hợp với FastAPI:

```python
from fastapi import FastAPI
from fastapi.services.cii_intraday_service import CIIIntradayService

app = FastAPI()
service = CIIIntradayService()

@app.get("/cii/summary")
async def get_summary():
    return service.get_session_summary()

@app.post("/cii/start")
async def start_service():
    # Start service in background
    pass

@app.post("/cii/stop")
async def stop_service():
    service.stop_service()
    return {"message": "Service stopped"}
```

## License

MIT License
