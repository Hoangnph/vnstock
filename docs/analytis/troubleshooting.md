# Xử lý sự cố

## Lỗi thường gặp

### 1. Lỗi kết nối database

**Lỗi:** `sqlalchemy.exc.OperationalError: connection to server at "localhost" (127.0.0.1), port 5432 failed`

**Nguyên nhân:**
- Database server không chạy
- Thông tin kết nối sai
- Firewall chặn kết nối

**Giải pháp:**
```bash
# Kiểm tra PostgreSQL
sudo systemctl status postgresql

# Khởi động PostgreSQL
sudo systemctl start postgresql

# Kiểm tra kết nối
psql -h localhost -U postgres -d stockai
```

### 2. Lỗi module không tìm thấy

**Lỗi:** `ModuleNotFoundError: No module named 'analytis'`

**Nguyên nhân:**
- Python path không đúng
- Module chưa được cài đặt
- Virtual environment chưa được kích hoạt

**Giải pháp:**
```bash
# Kiểm tra Python path
python -c "import sys; print(sys.path)"

# Thêm path
export PYTHONPATH="${PYTHONPATH}:/Users/macintoshhd/Project/Project/stockAI"

# Hoặc trong code
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

### 3. Lỗi dữ liệu không đủ

**Lỗi:** `ValueError: Not enough data points for analysis`

**Nguyên nhân:**
- Dữ liệu cổ phiếu không đủ
- Thời gian phân tích quá ngắn
- Mã cổ phiếu không tồn tại

**Giải pháp:**
```python
# Kiểm tra dữ liệu
from analytis.data.loader import load_stock_data

data = load_stock_data('PDR', '2024-01-01', '2024-12-31')
print(f"Số điểm dữ liệu: {len(data)}")

# Tăng thời gian phân tích
start_date = '2023-01-01'  # Thay vì '2024-01-01'
```

### 4. Lỗi cấu hình

**Lỗi:** `ValueError: Invalid configuration parameter`

**Nguyên nhân:**
- Tham số cấu hình không hợp lệ
- Giá trị ngoài phạm vi cho phép
- Cấu hình thiếu tham số bắt buộc

**Giải pháp:**
```python
# Kiểm tra cấu hình
from analytis.config import AnalysisConfig

config = AnalysisConfig()
print(f"MA short: {config.indicator_config.ma_short}")
print(f"MA long: {config.indicator_config.ma_long}")

# Sửa cấu hình
config.indicator_config.ma_short = 10  # Thay vì giá trị không hợp lệ
```

### 5. Lỗi bộ nhớ

**Lỗi:** `MemoryError: Unable to allocate array`

**Nguyên nhân:**
- Dữ liệu quá lớn
- Phân tích quá nhiều mã cùng lúc
- Bộ nhớ hệ thống không đủ

**Giải pháp:**
```python
# Giảm kích thước dữ liệu
start_date = '2024-06-01'  # Thay vì '2020-01-01'

# Phân tích theo batch
symbols = ['PDR', 'VCB', 'FPT']
for symbol in symbols:
    result = engine.analyze_symbol(symbol, start_date, end_date)
    # Xử lý kết quả ngay
```

## Debug

### 1. Bật logging

```python
import logging

# Cấu hình logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Sử dụng
logger = logging.getLogger('analytis')
logger.debug('Debug message')
logger.info('Info message')
logger.warning('Warning message')
logger.error('Error message')
```

### 2. Kiểm tra dữ liệu

```python
def debug_data(symbol, start_date, end_date):
    from analytis.data.loader import load_stock_data
    
    try:
        data = load_stock_data(symbol, start_date, end_date)
        print(f"Symbol: {symbol}")
        print(f"Data shape: {data.shape}")
        print(f"Columns: {data.columns.tolist()}")
        print(f"Date range: {data.index.min()} to {data.index.max()}")
        print(f"Missing values: {data.isnull().sum().sum()}")
        print(f"Sample data:")
        print(data.head())
        return True
    except Exception as e:
        print(f"Error loading data: {e}")
        return False
```

### 3. Kiểm tra cấu hình

```python
def debug_config(config):
    print(f"Config name: {config.name}")
    print(f"Description: {config.description}")
    print(f"Min score threshold: {config.min_score_threshold}")
    print(f"Lookback days: {config.lookback_days}")
    
    print(f"\nIndicator config:")
    print(f"MA short: {config.indicator_config.ma_short}")
    print(f"MA long: {config.indicator_config.ma_long}")
    print(f"RSI period: {config.indicator_config.rsi_period}")
    
    print(f"\nScoring config:")
    print(f"Strong threshold: {config.scoring_config.strong_threshold}")
    print(f"Medium threshold: {config.scoring_config.medium_threshold}")
```

### 4. Kiểm tra kết quả

```python
def debug_result(result):
    print(f"Analysis result:")
    print(f"Data info: {result.data_info}")
    print(f"Signals count: {len(result.signals)}")
    
    if result.signals:
        print(f"Signal summary: {result.signal_summary}")
        
        print(f"\nFirst 5 signals:")
        for i, signal in enumerate(result.signals[:5]):
            print(f"  {i+1}. {signal.timestamp.date()} - {signal.action.value} {signal.strength.value} ({signal.score:.2f})")
        
        print(f"\nLast 5 signals:")
        for i, signal in enumerate(result.signals[-5:]):
            print(f"  {i+1}. {signal.timestamp.date()} - {signal.action.value} {signal.strength.value} ({signal.score:.2f})")
```

## Performance

### 1. Tối ưu tốc độ

```python
# Sử dụng cache
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_analysis(symbol, start_date, end_date):
    return engine.analyze_symbol(symbol, start_date, end_date)

# Phân tích bất đồng bộ
import asyncio

async def analyze_async(symbols):
    tasks = []
    for symbol in symbols:
        task = asyncio.create_task(analyze_symbol_async(symbol))
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    return results
```

### 2. Tối ưu bộ nhớ

```python
# Xử lý theo batch
def process_batch(symbols, batch_size=10):
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        results = []
        
        for symbol in batch:
            result = engine.analyze_symbol(symbol, start_date, end_date)
            results.append(result)
        
        # Xử lý kết quả ngay
        process_results(results)
        
        # Giải phóng bộ nhớ
        del results
```

### 3. Monitoring

```python
import time
import psutil
import os

def monitor_analysis(symbol, start_date, end_date):
    # Thông tin hệ thống
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    start_time = time.time()
    
    try:
        result = engine.analyze_symbol(symbol, start_date, end_date)
        
        end_time = time.time()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        print(f"Analysis completed:")
        print(f"  Duration: {end_time - start_time:.2f} seconds")
        print(f"  Memory used: {final_memory - initial_memory:.2f} MB")
        print(f"  Signals: {len(result.signals)}")
        
        return result
        
    except Exception as e:
        print(f"Analysis failed: {e}")
        raise
```

## Testing

### 1. Unit tests

```python
import unittest
from unittest.mock import Mock, patch
from analytis.analysis_engine import AnalysisEngine

class TestAnalysisEngine(unittest.TestCase):
    def setUp(self):
        self.engine = AnalysisEngine()
    
    def test_analyze_symbol_success(self):
        # Mock data
        mock_data = pd.DataFrame({
            'Close': [100, 101, 102, 103, 104],
            'Volume': [1000, 1100, 1200, 1300, 1400]
        })
        
        with patch('analytis.data.loader.load_stock_data', return_value=mock_data):
            result = self.engine.analyze_symbol('TEST', '2024-01-01', '2024-01-05')
            
            self.assertIsNotNone(result)
            self.assertGreater(len(result.signals), 0)
    
    def test_analyze_symbol_no_data(self):
        with patch('analytis.data.loader.load_stock_data', return_value=pd.DataFrame()):
            with self.assertRaises(ValueError):
                self.engine.analyze_symbol('TEST', '2024-01-01', '2024-01-05')
```

### 2. Integration tests

```python
import pytest
from analytis.analysis_engine_db import DatabaseIntegratedAnalysisEngine

@pytest.mark.asyncio
async def test_database_integration():
    engine = DatabaseIntegratedAnalysisEngine()
    
    # Test analysis
    result = await engine.analyze_symbol('PDR', '2024-01-01', '2024-01-31')
    
    assert result.analysis_result_id is not None
    assert len(result.signals) > 0
    
    # Test query
    history = await engine.get_analysis_history('PDR', limit=1)
    assert len(history) == 1
    assert history[0]['symbol'] == 'PDR'
```

### 3. Performance tests

```python
import time
import statistics

def benchmark_analysis(symbols, iterations=5):
    durations = []
    
    for _ in range(iterations):
        start_time = time.time()
        
        for symbol in symbols:
            result = engine.analyze_symbol(symbol, start_date, end_date)
        
        duration = time.time() - start_time
        durations.append(duration)
    
    return {
        'mean': statistics.mean(durations),
        'median': statistics.median(durations),
        'std': statistics.stdev(durations),
        'min': min(durations),
        'max': max(durations)
    }
```

## Liên hệ hỗ trợ

### 1. Tạo issue

Khi gặp lỗi, vui lòng tạo issue với thông tin:
- Mô tả lỗi
- Các bước tái hiện
- Log lỗi
- Thông tin hệ thống

### 2. Debug information

```python
def collect_debug_info():
    import sys
    import platform
    import pandas as pd
    import numpy as np
    
    info = {
        'python_version': sys.version,
        'platform': platform.platform(),
        'pandas_version': pd.__version__,
        'numpy_version': np.__version__,
        'analytis_version': '1.0.0'  # Thay bằng version thực tế
    }
    
    return info
```

### 3. Log files

```python
import logging
import os
from datetime import datetime

def setup_logging():
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f'analytis_{datetime.now().strftime("%Y%m%d")}.log')
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger('analytis')
```
