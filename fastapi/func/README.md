# StockAI Data Functions

Thư viện các hàm tiện ích để lấy và xử lý dữ liệu chứng khoán Việt Nam.

## 📁 Cấu trúc thư mục

```
fastapi/func/
├── README.md                    # Tài liệu này
├── stock_data_fetcher.py       # Hàm lấy dữ liệu chứng khoán tổng quát
├── normalize_foreign_data.py   # Hàm chuẩn hóa dữ liệu foreign trading
├── vn100_fetcher.py           # Hàm lấy danh sách mã VN100
├── demo.py                     # Script demo các tính năng
└── __init__.py                 # Package initialization
```

## 🚀 Các hàm chính

### 1. `fetch_stock_data()` - Lấy dữ liệu chứng khoán tổng quát

Hàm chính để lấy dữ liệu đầy đủ của bất kỳ mã chứng khoán nào.

#### Cú pháp:
```python
from fastapi.func.stock_data_fetcher import fetch_stock_data

success, df, metadata = fetch_stock_data(
    symbol='PDR',                    # Mã chứng khoán
    start_date='2020-01-01',         # Ngày bắt đầu
    end_date='2024-12-31',           # Ngày kết thúc (tùy chọn)
    source='VCI',                    # Nguồn dữ liệu
    include_foreign=True,            # Có lấy dữ liệu foreign trading
    output_dir='./output',           # Thư mục lưu file
    save_csv=True,                   # Lưu file CSV
    save_json=True,                  # Lưu file JSON
    web_json=False,                  # Lưu JSON cho web
    print_stats=True                 # In thống kê
)
```

#### Tham số:

| Tham số | Kiểu | Mặc định | Mô tả |
|---------|------|----------|-------|
| `symbol` | str | **Bắt buộc** | Mã chứng khoán (VD: 'PDR', 'VIC', 'VCB') |
| `start_date` | str | '2010-01-01' | Ngày bắt đầu (YYYY-MM-DD) |
| `end_date` | str | None | Ngày kết thúc (YYYY-MM-DD), None = hôm nay |
| `source` | str | 'VCI' | Nguồn dữ liệu ('VCI', 'TCBS') |
| `include_foreign` | bool | True | Có lấy dữ liệu foreign trading |
| `output_dir` | str | None | Thư mục lưu file, None = thư mục hiện tại |
| `save_csv` | bool | True | Lưu file CSV |
| `save_json` | bool | True | Lưu file JSON |
| `web_json` | bool | False | Lưu JSON cho web (tên file đặc biệt) |
| `print_stats` | bool | True | In thống kê dữ liệu |

#### Giá trị trả về:

```python
# success: bool - Thành công hay không
# df: pd.DataFrame - Dữ liệu đã xử lý
# metadata: dict - Thông tin metadata

metadata = {
    'symbol': 'PDR',
    'start_date': '2020-01-01',
    'end_date': '2024-12-31',
    'source': 'VCI',
    'final_records': 1250,
    'columns': ['time', 'open', 'high', 'low', 'close', 'volume', ...],
    'date_range': {'start': '2020-01-02', 'end': '2024-12-30'},
    'price_stats': {'high_max': 45.5, 'low_min': 12.3, 'volume_avg': 1500000},
    'foreign_stats': {'buy_avg': 50000, 'sell_avg': 45000},
    'saved_files': {'csv': '/path/to/file.csv', 'json': '/path/to/file.json'}
}
```

#### Ví dụ sử dụng:

```python
# Lấy dữ liệu PDR từ 2020
success, df, metadata = fetch_stock_data('PDR', '2020-01-01', '2024-12-31')

# Lấy dữ liệu VIC không có foreign trading
success, df, metadata = fetch_stock_data(
    'VIC', 
    '2023-01-01', 
    include_foreign=False,
    save_csv=False
)

# Lấy dữ liệu và lưu vào thư mục cụ thể
success, df, metadata = fetch_stock_data(
    'VCB',
    '2024-01-01',
    output_dir='./data/vcb',
    web_json=True
)
```

### 2. `StockDataFetcher` - Class lấy dữ liệu

Class để lấy dữ liệu với nhiều tùy chọn hơn.

#### Cú pháp:
```python
from fastapi.func.stock_data_fetcher import StockDataFetcher

fetcher = StockDataFetcher(source='VCI')
success, df, metadata = fetcher.fetch_stock_data(
    symbol='PDR',
    start_date='2020-01-01',
    end_date='2024-12-31'
)

# Lưu dữ liệu
saved_files = fetcher.save_data(
    df=df,
    symbol='PDR',
    start_date='2020-01-01',
    end_date='2024-12-31',
    output_dir=Path('./output'),
    save_csv=True,
    save_json=True,
    web_json=True
)
```

### 3. `get_vn100_symbols()` - Lấy danh sách mã VN100

Hàm lấy danh sách 100 mã chứng khoán có vốn hóa lớn nhất và thanh khoản cao nhất.

#### Cú pháp:
```python
from fastapi.func.vn100_fetcher import get_vn100_symbols

symbols = get_vn100_symbols()
print(f"VN100 có {len(symbols)} mã")
```

#### Các hàm VN100 khác:
```python
from fastapi.func.vn100_fetcher import (
    get_vn100_symbols,      # Lấy danh sách mã
    get_vn100_dataframe,    # Lấy DataFrame
    save_vn100_csv,         # Lưu vào CSV
    get_vn100_by_sector,    # Lấy theo ngành
    get_vn100_top_n,        # Lấy top N
    VN100Fetcher           # Class chính
)

# Lấy danh sách mã
symbols = get_vn100_symbols()

# Lấy DataFrame với thông tin chi tiết
df = get_vn100_dataframe()

# Lấy mã theo ngành
banking_symbols = get_vn100_by_sector('Banking')

# Lấy top 20
top_20 = get_vn100_top_n(20)

# Lưu vào CSV
success = save_vn100_csv('data/vn100.csv')
```

### 4. `normalize_foreign_data()` - Chuẩn hóa dữ liệu foreign trading

Hàm chuẩn hóa dữ liệu foreign trading từ các nguồn khác nhau.

#### Cú pháp:
```python
from fastapi.func.normalize_foreign_data import normalize_foreign_data

normalized_data = normalize_foreign_data(
    raw_data,           # Dữ liệu thô
    source='VCI'        # Nguồn dữ liệu
)
```

## 📊 Cấu trúc dữ liệu

### DataFrame output:
```python
df.columns = [
    'time',                 # Ngày (datetime.date)
    'open',                 # Giá mở cửa
    'high',                 # Giá cao nhất
    'low',                  # Giá thấp nhất
    'close',                # Giá đóng cửa
    'volume',               # Khối lượng giao dịch
    'foreign_buy_shares',   # Khối lượng mua của khối ngoại
    'foreign_sell_shares',  # Khối lượng bán của khối ngoại
    'foreign_net_shares'    # Khối lượng ròng của khối ngoại
]
```

### JSON output:
```json
[
  {
    "time": "2024-01-02",
    "open": 25.5,
    "high": 26.0,
    "low": 25.0,
    "close": 25.8,
    "volume": 1500000,
    "foreign_buy_shares": 50000,
    "foreign_sell_shares": 45000,
    "foreign_net_shares": 5000
  }
]
```

## 🔧 Cài đặt và yêu cầu

### Dependencies:
```bash
pip install pandas vnstock
```

### Import:
```python
# Import hàm chính
from fastapi.func.stock_data_fetcher import fetch_stock_data

# Import class
from fastapi.func.stock_data_fetcher import StockDataFetcher

# Import hàm VN100
from fastapi.func.vn100_fetcher import get_vn100_symbols, get_vn100_dataframe

# Import hàm chuẩn hóa
from fastapi.func.normalize_foreign_data import normalize_foreign_data

# Import tất cả
from fastapi.func import *
```

## 📝 Ví dụ sử dụng nâng cao

### 1. Lấy dữ liệu VN100:
```python
from fastapi.func import get_vn100_symbols, fetch_stock_data

# Lấy danh sách VN100
vn100_symbols = get_vn100_symbols()
print(f"VN100 có {len(vn100_symbols)} mã")

# Lấy dữ liệu cho top 10 VN100
top_10 = vn100_symbols[:10]
results = {}

for symbol in top_10:
    print(f"Fetching {symbol}...")
    success, df, metadata = fetch_stock_data(
        symbol=symbol,
        start_date='2023-01-01',
        output_dir=f'./data/vn100/{symbol}',
        print_stats=False
    )
    
    if success:
        results[symbol] = {
            'data': df,
            'metadata': metadata
        }
        print(f"✅ {symbol}: {len(df)} records")
    else:
        print(f"❌ {symbol}: Failed")

print(f"Successfully fetched {len(results)} VN100 symbols")
```

### 2. Lấy dữ liệu nhiều mã chứng khoán:
```python
symbols = ['PDR', 'VIC', 'VCB', 'HPG', 'MSN']
results = {}

for symbol in symbols:
    print(f"Fetching {symbol}...")
    success, df, metadata = fetch_stock_data(
        symbol=symbol,
        start_date='2023-01-01',
        output_dir=f'./data/{symbol}',
        print_stats=False
    )
    
    if success:
        results[symbol] = {
            'data': df,
            'metadata': metadata
        }
        print(f"✅ {symbol}: {len(df)} records")
    else:
        print(f"❌ {symbol}: Failed")

print(f"Successfully fetched {len(results)} symbols")
```

### 3. Lấy dữ liệu theo batch:
```python
from datetime import datetime, timedelta

def fetch_recent_data(symbol, days=30):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    return fetch_stock_data(
        symbol=symbol,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        output_dir=f'./recent_data/{symbol}',
        web_json=True
    )

# Lấy dữ liệu 30 ngày gần nhất
success, df, metadata = fetch_recent_data('PDR', 30)
```

### 4. Xử lý lỗi và retry:
```python
import time
from typing import Optional

def fetch_with_retry(symbol: str, max_retries: int = 3) -> Optional[pd.DataFrame]:
    for attempt in range(max_retries):
        try:
            success, df, metadata = fetch_stock_data(
                symbol=symbol,
                start_date='2020-01-01',
                print_stats=False
            )
            
            if success:
                return df
            else:
                print(f"Attempt {attempt + 1} failed for {symbol}")
                
        except Exception as e:
            print(f"Attempt {attempt + 1} error for {symbol}: {str(e)}")
            
        if attempt < max_retries - 1:
            time.sleep(2)  # Wait 2 seconds before retry
    
    return None

# Sử dụng
df = fetch_with_retry('PDR')
if df is not None:
    print(f"Successfully fetched {len(df)} records")
```

## 🚨 Xử lý lỗi

### Các lỗi thường gặp:

1. **ImportError: vnstock not found**
   ```bash
   pip install vnstock
   ```

2. **No data found for symbol**
   - Kiểm tra mã chứng khoán có đúng không
   - Kiểm tra khoảng thời gian có dữ liệu không
   - Thử nguồn dữ liệu khác (TCBS thay vì VCI)

3. **Foreign trading data not available**
   - Một số mã không có dữ liệu foreign trading
   - Sử dụng `include_foreign=False`

4. **Network/API errors**
   - Kiểm tra kết nối internet
   - Thử lại sau vài phút
   - Sử dụng retry mechanism

### Debug mode:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Sẽ hiển thị thông tin debug chi tiết
success, df, metadata = fetch_stock_data('PDR', '2020-01-01')
```

## 📈 Performance Tips

1. **Batch processing**: Lấy dữ liệu nhiều mã cùng lúc
2. **Caching**: Lưu dữ liệu để tránh fetch lại
3. **Date range**: Chỉ lấy khoảng thời gian cần thiết
4. **Source selection**: VCI thường nhanh hơn TCBS

## 🔄 Cập nhật

- **Version 1.0.0**: Phiên bản đầu tiên
- **Features**: Fetch OHLCV + Foreign trading data
- **Sources**: VCI, TCBS
- **Formats**: CSV, JSON, Web JSON

## 📞 Hỗ trợ

Nếu gặp vấn đề, vui lòng:
1. Kiểm tra log lỗi
2. Thử với mã chứng khoán khác
3. Kiểm tra kết nối internet
4. Cập nhật thư viện vnstock

---

**StockAI Team** - Cung cấp công cụ phân tích chứng khoán chuyên nghiệp
