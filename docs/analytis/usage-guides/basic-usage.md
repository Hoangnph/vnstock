# Basic Usage Guide

## Tổng quan

Hướng dẫn sử dụng cơ bản cho hệ thống phân tích StockAI, bao gồm cách khởi tạo, cấu hình và chạy phân tích cho một mã cổ phiếu.

## Cài đặt và Khởi tạo

### 1. Cài đặt Dependencies

```bash
# Cài đặt các package cần thiết
pip install pandas numpy sqlalchemy asyncpg httpx

# Hoặc sử dụng requirements.txt
pip install -r requirements.txt
```

### 2. Khởi tạo Database

```bash
# Tạo schema database
python database/scripts/create_modular_analysis_tables.py

# Kiểm tra kết nối database
python database/scripts/test_connection.py
```

### 3. Import Modules

```python
# Import các module cần thiết
from analytis.analysis_engine import AnalysisEngine, AnalysisConfig
from analytis.analysis_engine_db import DatabaseIntegratedAnalysisEngine
from analytis.engines.indicator_engine import IndicatorConfig
from analytis.engines.scoring_engine import ScoringConfig
```

## Sử dụng cơ bản

### 1. Phân tích đơn giản

```python
# Khởi tạo engine với cấu hình mặc định
engine = AnalysisEngine()

# Phân tích một mã cổ phiếu
result = engine.analyze_symbol(
    symbol="PDR",
    start_date="2025-01-01",
    end_date="2025-10-01"
)

# Xem kết quả
print(f"Symbol: {result.symbol}")
print(f"Data points: {result.data_info['total_rows']}")
print(f"Signals generated: {len(result.signals)}")

# Xem tín hiệu gần nhất
if result.signals:
    latest_signal = result.signals[-1]
    print(f"Latest signal: {latest_signal.action.value} {latest_signal.strength.value}")
    print(f"Score: {latest_signal.score}")
    print(f"Description: {latest_signal.description}")
```

### 2. Phân tích với cấu hình tùy chỉnh

```python
# Tạo cấu hình tùy chỉnh
config = AnalysisConfig(
    indicator_config=IndicatorConfig(
        ma_short=5,
        ma_long=30,
        rsi_period=21,
        bb_period=15,
        bb_std=1.5
    ),
    scoring_config=ScoringConfig(
        strong_threshold=80.0,
        medium_threshold=30.0,
        buy_strong_threshold=-80.0,
        sell_strong_threshold=80.0
    ),
    min_score_threshold=15.0,
    lookback_days=180
)

# Khởi tạo engine với cấu hình
engine = AnalysisEngine(config)

# Phân tích
result = engine.analyze_symbol("PDR", "2025-01-01", "2025-10-01")
```

### 3. Phân tích với database

```python
import asyncio

async def analyze_with_database():
    # Khởi tạo engine tích hợp database
    engine = DatabaseIntegratedAnalysisEngine()
    
    # Phân tích và lưu vào database
    result = await engine.analyze_symbol(
        symbol="PDR",
        start_date="2025-01-01",
        end_date="2025-10-01"
    )
    
    # Xem thông tin database
    print(f"Analysis Result ID: {result.analysis_result_id}")
    print(f"Indicator Config ID: {result.indicator_config_id}")
    print(f"Scoring Config ID: {result.scoring_config_id}")
    
    return result

# Chạy phân tích
result = asyncio.run(analyze_with_database())
```

## Xem kết quả

### 1. Thông tin cơ bản

```python
# Thông tin tổng quan
print("=== Analysis Results ===")
print(f"Symbol: {result.symbol}")
print(f"Analysis Date: {result.analysis_date}")
print(f"Data Points: {result.data_info['total_rows']}")
print(f"Date Range: {result.data_info['start_date']} to {result.data_info['end_date']}")
print(f"Signals Generated: {len(result.signals)}")

# Thông tin chỉ số
print("\n=== Latest Indicators ===")
for category, indicators in result.indicators.items():
    print(f"{category}:")
    for name, value in indicators.items():
        if value is not None:
            print(f"  {name}: {value}")
```

### 2. Tín hiệu giao dịch

```python
# Xem tất cả tín hiệu
print("=== Trading Signals ===")
for i, signal in enumerate(result.signals):
    print(f"{i+1}. {signal.timestamp.date()}: {signal.action.value} {signal.strength.value}")
    print(f"   Score: {signal.score:.2f}")
    print(f"   Description: {signal.description}")
    print(f"   Triggered Rules: {len(signal.triggered_rules)}")
    print()

# Lọc tín hiệu theo loại
buy_signals = [s for s in result.signals if s.action.value == "MUA"]
sell_signals = [s for s in result.signals if s.action.value == "BÁN"]
strong_signals = [s for s in result.signals if s.strength.value in ["STRONG", "RẤT MẠNH"]]

print(f"Buy signals: {len(buy_signals)}")
print(f"Sell signals: {len(sell_signals)}")
print(f"Strong signals: {len(strong_signals)}")
```

### 3. Tóm tắt tín hiệu

```python
# Tóm tắt tín hiệu
summary = result.signal_summary
print("=== Signal Summary ===")
print(f"Total signals: {summary['total_signals']}")
print(f"Buy signals: {summary['buy_signals']}")
print(f"Sell signals: {summary['sell_signals']}")
print(f"Hold signals: {summary['hold_signals']}")
print(f"Strong signals: {summary['strong_signals']}")
print(f"Medium signals: {summary['medium_signals']}")
print(f"Weak signals: {summary['weak_signals']}")
print(f"Average score: {summary['avg_score']:.2f}")
print(f"Max score: {summary['max_score']:.2f}")
print(f"Min score: {summary['min_score']:.2f}")
```

## Xử lý lỗi

### 1. Kiểm tra dữ liệu

```python
def safe_analyze(engine, symbol, start_date, end_date):
    """Phân tích an toàn với xử lý lỗi"""
    try:
        result = engine.analyze_symbol(symbol, start_date, end_date)
        
        # Kiểm tra kết quả
        if result.data_info.get('error'):
            print(f"Error: {result.data_info['error']}")
            return None
        
        if not result.signals:
            print(f"No signals generated for {symbol}")
            return result
        
        print(f"Analysis successful for {symbol}: {len(result.signals)} signals")
        return result
        
    except Exception as e:
        print(f"Analysis failed for {symbol}: {e}")
        return None

# Sử dụng
result = safe_analyze(engine, "PDR", "2025-01-01", "2025-10-01")
```

### 2. Xử lý dữ liệu thiếu

```python
def analyze_with_validation(engine, symbol, start_date, end_date):
    """Phân tích với kiểm tra dữ liệu"""
    try:
        # Kiểm tra dữ liệu có sẵn
        from analytis.data.loader import load_stock_data
        
        df = load_stock_data(symbol, start_date, end_date)
        
        if df.empty:
            print(f"No data available for {symbol}")
            return None
        
        if len(df) < 50:
            print(f"Insufficient data for {symbol}: {len(df)} points (minimum 50 required)")
            return None
        
        # Phân tích
        result = engine.analyze_symbol(symbol, start_date, end_date)
        return result
        
    except Exception as e:
        print(f"Validation failed for {symbol}: {e}")
        return None
```

## Tùy chỉnh cấu hình

### 1. Cấu hình chỉ số

```python
# Cấu hình cho thị trường Việt Nam
vietnam_indicator_config = IndicatorConfig(
    ma_short=5,      # Thị trường biến động cao
    ma_long=30,      # Xu hướng ngắn hạn
    rsi_period=14,   # Chuẩn
    bb_period=20,    # Chuẩn
    bb_std=1.5,      # Dải hẹp hơn
    volume_avg_period=10  # Volume trung bình ngắn hạn
)

# Cấu hình cho phân tích dài hạn
long_term_indicator_config = IndicatorConfig(
    ma_short=20,
    ma_long=100,
    rsi_period=21,
    bb_period=30,
    bb_std=2.5,
    volume_avg_period=30
)
```

### 2. Cấu hình chấm điểm

```python
# Cấu hình chấm điểm nhạy cảm
sensitive_scoring_config = ScoringConfig(
    strong_threshold=60.0,      # Ngưỡng thấp hơn
    medium_threshold=20.0,
    weak_threshold=5.0,
    buy_strong_threshold=-60.0,
    sell_strong_threshold=60.0,
    context_multipliers={
        "uptrend_buy": 2.0,     # Tăng multiplier
        "uptrend_sell": 0.3,
        "downtrend_sell": 2.0,
        "downtrend_buy": 0.3,
        "sideways": 0.5
    }
)

# Cấu hình chấm điểm bảo thủ
conservative_scoring_config = ScoringConfig(
    strong_threshold=90.0,      # Ngưỡng cao hơn
    medium_threshold=40.0,
    weak_threshold=15.0,
    buy_strong_threshold=-90.0,
    sell_strong_threshold=90.0,
    context_multipliers={
        "uptrend_buy": 1.2,     # Giảm multiplier
        "uptrend_sell": 0.8,
        "downtrend_sell": 1.2,
        "downtrend_buy": 0.8,
        "sideways": 0.9
    }
)
```

### 3. Cấu hình phân tích

```python
# Cấu hình phân tích nhanh
quick_analysis_config = AnalysisConfig(
    min_score_threshold=5.0,    # Ngưỡng thấp
    lookback_days=90,           # Thời gian ngắn
    indicator_config=vietnam_indicator_config,
    scoring_config=sensitive_scoring_config
)

# Cấu hình phân tích chi tiết
detailed_analysis_config = AnalysisConfig(
    min_score_threshold=20.0,   # Ngưỡng cao
    lookback_days=365,          # Thời gian dài
    indicator_config=long_term_indicator_config,
    scoring_config=conservative_scoring_config
)
```

## Ví dụ thực tế

### 1. Phân tích một mã cổ phiếu

```python
def analyze_single_stock():
    """Phân tích một mã cổ phiếu"""
    # Cấu hình
    config = AnalysisConfig(
        min_score_threshold=15.0,
        lookback_days=180
    )
    
    # Khởi tạo engine
    engine = AnalysisEngine(config)
    
    # Phân tích
    result = engine.analyze_symbol("PDR", "2025-01-01", "2025-10-01")
    
    # Hiển thị kết quả
    print(f"=== Analysis for {result.symbol} ===")
    print(f"Data points: {result.data_info['total_rows']}")
    print(f"Signals: {len(result.signals)}")
    
    # Tín hiệu gần nhất
    if result.signals:
        latest = result.signals[-1]
        print(f"Latest signal: {latest.action.value} {latest.strength.value}")
        print(f"Score: {latest.score:.2f}")
        print(f"Date: {latest.timestamp.date()}")
    
    return result

# Chạy phân tích
result = analyze_single_stock()
```

### 2. So sánh cấu hình

```python
def compare_configurations():
    """So sánh kết quả với các cấu hình khác nhau"""
    symbol = "PDR"
    start_date = "2025-01-01"
    end_date = "2025-10-01"
    
    # Cấu hình 1: Nhạy cảm
    config1 = AnalysisConfig(
        min_score_threshold=10.0,
        lookback_days=90
    )
    
    # Cấu hình 2: Bảo thủ
    config2 = AnalysisConfig(
        min_score_threshold=25.0,
        lookback_days=180
    )
    
    # Phân tích với cả hai cấu hình
    engine1 = AnalysisEngine(config1)
    engine2 = AnalysisEngine(config2)
    
    result1 = engine1.analyze_symbol(symbol, start_date, end_date)
    result2 = engine2.analyze_symbol(symbol, start_date, end_date)
    
    # So sánh kết quả
    print(f"=== Comparison for {symbol} ===")
    print(f"Config 1 (Sensitive): {len(result1.signals)} signals")
    print(f"Config 2 (Conservative): {len(result2.signals)} signals")
    
    # Tín hiệu mua mạnh
    strong_buy1 = [s for s in result1.signals if s.action.value == "MUA" and s.strength.value == "RẤT MẠNH"]
    strong_buy2 = [s for s in result2.signals if s.action.value == "MUA" and s.strength.value == "RẤT MẠNH"]
    
    print(f"Strong buy signals - Config 1: {len(strong_buy1)}, Config 2: {len(strong_buy2)}")
    
    return result1, result2

# Chạy so sánh
result1, result2 = compare_configurations()
```

### 3. Phân tích với database

```python
async def analyze_with_database_example():
    """Ví dụ phân tích với database"""
    # Khởi tạo engine
    engine = DatabaseIntegratedAnalysisEngine()
    
    # Phân tích
    result = await engine.analyze_symbol("PDR", "2025-01-01", "2025-10-01")
    
    # Xem thông tin database
    print(f"=== Database Analysis for {result.symbol} ===")
    print(f"Analysis Result ID: {result.analysis_result_id}")
    print(f"Indicator Config ID: {result.indicator_config_id}")
    print(f"Scoring Config ID: {result.scoring_config_id}")
    print(f"Analysis Config ID: {result.analysis_config_id}")
    
    # Lấy lịch sử phân tích
    history = await engine.get_analysis_history("PDR", limit=5)
    print(f"\nAnalysis History: {len(history)} records")
    for h in history:
        print(f"  {h['analysis_date']}: {h['total_signals']} signals")
    
    # Lấy lịch sử tín hiệu
    signal_history = await engine.get_signal_history("PDR", limit=10)
    print(f"\nSignal History: {len(signal_history)} records")
    for s in signal_history[:5]:
        print(f"  {s['signal_date']}: {s['action']} {s['strength']} (Score: {s['score']:.2f})")
    
    # Thống kê database
    stats = await engine.get_database_stats()
    print(f"\nDatabase Statistics:")
    print(f"  Configurations: {stats.get('configurations', {})}")
    print(f"  Indicator Calculations: {stats.get('indicator_calculations', {}).get('total_calculations', 0)}")
    print(f"  Analysis Results: {stats.get('analysis_results', {}).get('total_analyses', 0)}")
    print(f"  Signals: {stats.get('signals', {}).get('total_signals', 0)}")
    
    return result

# Chạy ví dụ
result = asyncio.run(analyze_with_database_example())
```

## Best Practices

### 1. Xử lý lỗi

```python
def robust_analysis(engine, symbol, start_date, end_date):
    """Phân tích robust với xử lý lỗi đầy đủ"""
    try:
        # Kiểm tra tham số
        if not symbol or not start_date or not end_date:
            raise ValueError("Missing required parameters")
        
        # Phân tích
        result = engine.analyze_symbol(symbol, start_date, end_date)
        
        # Kiểm tra kết quả
        if result.data_info.get('error'):
            logger.error(f"Analysis error for {symbol}: {result.data_info['error']}")
            return None
        
        # Log thông tin
        logger.info(f"Analysis completed for {symbol}: {len(result.signals)} signals")
        
        return result
        
    except ValueError as e:
        logger.error(f"Parameter error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error for {symbol}: {e}")
        return None
```

### 2. Tối ưu hiệu suất

```python
def efficient_analysis(engine, symbol, start_date, end_date):
    """Phân tích hiệu quả"""
    import time
    
    start_time = time.time()
    
    try:
        # Phân tích
        result = engine.analyze_symbol(symbol, start_date, end_date)
        
        # Tính thời gian
        duration = time.time() - start_time
        
        # Log hiệu suất
        logger.info(f"Analysis completed in {duration:.2f}s")
        logger.info(f"Data points: {result.data_info['total_rows']}")
        logger.info(f"Signals: {len(result.signals)}")
        logger.info(f"Signals per second: {len(result.signals) / duration:.2f}")
        
        return result
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Analysis failed after {duration:.2f}s: {e}")
        raise
```

### 3. Caching kết quả

```python
import pickle
import os
from datetime import datetime, timedelta

def cached_analysis(engine, symbol, start_date, end_date, cache_hours=24):
    """Phân tích với caching"""
    # Tạo cache key
    cache_key = f"{symbol}_{start_date}_{end_date}"
    cache_file = f"cache/{cache_key}.pkl"
    
    # Kiểm tra cache
    if os.path.exists(cache_file):
        cache_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
        if datetime.now() - cache_time < timedelta(hours=cache_hours):
            logger.info(f"Loading cached result for {symbol}")
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
    
    # Phân tích mới
    result = engine.analyze_symbol(symbol, start_date, end_date)
    
    # Lưu cache
    os.makedirs("cache", exist_ok=True)
    with open(cache_file, 'wb') as f:
        pickle.dump(result, f)
    
    logger.info(f"Cached result for {symbol}")
    return result
```

## Troubleshooting

### 1. Lỗi "Insufficient data points"

**Nguyên nhân**: Không đủ dữ liệu để tính toán chỉ số

**Giải pháp**:
```python
# Kiểm tra dữ liệu trước khi phân tích
from analytis.data.loader import load_stock_data

df = load_stock_data("PDR", "2025-01-01", "2025-10-01")
print(f"Data points: {len(df)}")

if len(df) < 50:
    print("Need at least 50 data points")
    # Mở rộng khoảng thời gian
    df = load_stock_data("PDR", "2024-01-01", "2025-10-01")
    print(f"Extended data points: {len(df)}")
```

### 2. Lỗi "No signals generated"

**Nguyên nhân**: Không có tín hiệu nào đạt ngưỡng

**Giải pháp**:
```python
# Giảm ngưỡng tối thiểu
config = AnalysisConfig(min_score_threshold=5.0)  # Giảm từ 10.0 xuống 5.0
engine = AnalysisEngine(config)
result = engine.analyze_symbol("PDR", "2025-01-01", "2025-10-01")

# Hoặc sử dụng cấu hình nhạy cảm hơn
sensitive_config = ScoringConfig(
    strong_threshold=60.0,  # Giảm từ 75.0
    medium_threshold=20.0,  # Giảm từ 25.0
    buy_strong_threshold=-60.0,  # Tăng từ -75.0
    sell_strong_threshold=60.0   # Giảm từ 75.0
)
```

### 3. Lỗi "Database connection failed"

**Nguyên nhân**: Không thể kết nối database

**Giải pháp**:
```python
# Kiểm tra kết nối database
from database.api.database import get_database_manager

try:
    db_manager = get_database_manager()
    db_manager.initialize()
    print("Database connection successful")
except Exception as e:
    print(f"Database connection failed: {e}")
    # Sử dụng engine không tích hợp database
    engine = AnalysisEngine()  # Thay vì DatabaseIntegratedAnalysisEngine()
```

### 4. Lỗi "Module not found"

**Nguyên nhân**: Thiếu module hoặc path không đúng

**Giải pháp**:
```python
# Thêm path vào sys.path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Hoặc sử dụng PYTHONPATH
# export PYTHONPATH="${PYTHONPATH}:/path/to/stockAI"
```
