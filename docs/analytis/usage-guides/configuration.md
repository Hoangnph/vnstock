# Configuration Guide

## Tổng quan

Hướng dẫn cấu hình hệ thống phân tích StockAI, bao gồm cấu hình chỉ số kỹ thuật, chấm điểm, và các tham số phân tích.

## Cấu hình chỉ số kỹ thuật (IndicatorConfig)

### 1. Moving Averages

```python
from analytis.engines.indicator_engine import IndicatorConfig

# Cấu hình mặc định
config = IndicatorConfig(
    ma_short=9,    # MA ngắn hạn
    ma_long=50,    # MA dài hạn
    ma_medium=20   # MA trung hạn
)

# Cấu hình cho thị trường biến động cao
volatile_config = IndicatorConfig(
    ma_short=5,    # MA ngắn hơn
    ma_long=30,    # MA dài hơn
    ma_medium=15   # MA trung hạn
)

# Cấu hình cho phân tích dài hạn
long_term_config = IndicatorConfig(
    ma_short=20,   # MA ngắn hạn
    ma_long=100,   # MA dài hạn
    ma_medium=50   # MA trung hạn
)
```

### 2. RSI Configuration

```python
# Cấu hình RSI mặc định
rsi_config = IndicatorConfig(
    rsi_period=14,      # Chu kỳ RSI
    rsi_overbought=70,  # Ngưỡng quá mua
    rsi_oversold=30     # Ngưỡng quá bán
)

# Cấu hình RSI nhạy cảm
sensitive_rsi_config = IndicatorConfig(
    rsi_period=10,      # Chu kỳ ngắn hơn
    rsi_overbought=75,  # Ngưỡng cao hơn
    rsi_oversold=25     # Ngưỡng thấp hơn
)

# Cấu hình RSI bảo thủ
conservative_rsi_config = IndicatorConfig(
    rsi_period=21,      # Chu kỳ dài hơn
    rsi_overbought=65,  # Ngưỡng thấp hơn
    rsi_oversold=35     # Ngưỡng cao hơn
)
```

### 3. MACD Configuration

```python
# Cấu hình MACD mặc định
macd_config = IndicatorConfig(
    macd_fast=12,    # EMA nhanh
    macd_slow=26,    # EMA chậm
    macd_signal=9    # Signal line
)

# Cấu hình MACD nhạy cảm
sensitive_macd_config = IndicatorConfig(
    macd_fast=8,     # EMA nhanh hơn
    macd_slow=21,    # EMA chậm hơn
    macd_signal=7    # Signal line ngắn hơn
)
```

### 4. Bollinger Bands Configuration

```python
# Cấu hình Bollinger Bands mặc định
bb_config = IndicatorConfig(
    bb_period=20,    # Chu kỳ
    bb_std=2.0       # Độ lệch chuẩn
)

# Cấu hình Bollinger Bands hẹp
narrow_bb_config = IndicatorConfig(
    bb_period=20,
    bb_std=1.5       # Độ lệch chuẩn thấp hơn
)

# Cấu hình Bollinger Bands rộng
wide_bb_config = IndicatorConfig(
    bb_period=20,
    bb_std=2.5       # Độ lệch chuẩn cao hơn
)
```

## Cấu hình chấm điểm (ScoringConfig)

### 1. Ngưỡng sức mạnh tín hiệu

```python
from analytis.engines.scoring_engine import ScoringConfig

# Cấu hình mặc định
scoring_config = ScoringConfig(
    strong_threshold=75.0,    # Ngưỡng tín hiệu mạnh
    medium_threshold=25.0,    # Ngưỡng tín hiệu trung bình
    weak_threshold=10.0       # Ngưỡng tín hiệu yếu
)

# Cấu hình nhạy cảm
sensitive_scoring = ScoringConfig(
    strong_threshold=60.0,    # Ngưỡng thấp hơn
    medium_threshold=20.0,
    weak_threshold=5.0
)

# Cấu hình bảo thủ
conservative_scoring = ScoringConfig(
    strong_threshold=90.0,    # Ngưỡng cao hơn
    medium_threshold=40.0,
    weak_threshold=15.0
)
```

### 2. Ngưỡng mua/bán

```python
# Cấu hình mặc định
buy_sell_config = ScoringConfig(
    buy_strong_threshold=-75.0,   # Ngưỡng mua mạnh
    buy_medium_threshold=-25.0,   # Ngưỡng mua trung bình
    sell_medium_threshold=25.0,   # Ngưỡng bán trung bình
    sell_strong_threshold=75.0    # Ngưỡng bán mạnh
)

# Cấu hình nhạy cảm
sensitive_buy_sell = ScoringConfig(
    buy_strong_threshold=-60.0,   # Ngưỡng thấp hơn
    buy_medium_threshold=-20.0,
    sell_medium_threshold=20.0,
    sell_strong_threshold=60.0
)
```

### 3. Context Multipliers

```python
# Cấu hình context multipliers
context_config = ScoringConfig(
    context_multipliers={
        "uptrend_buy": 1.5,      # Tăng điểm mua trong xu hướng tăng
        "uptrend_sell": 0.5,     # Giảm điểm bán trong xu hướng tăng
        "downtrend_sell": 1.5,   # Tăng điểm bán trong xu hướng giảm
        "downtrend_buy": 0.5,    # Giảm điểm mua trong xu hướng giảm
        "sideways": 0.7          # Giảm tất cả điểm trong thị trường đi ngang
    }
)

# Cấu hình context multipliers mạnh
strong_context_config = ScoringConfig(
    context_multipliers={
        "uptrend_buy": 2.0,      # Tăng mạnh
        "uptrend_sell": 0.3,     # Giảm mạnh
        "downtrend_sell": 2.0,
        "downtrend_buy": 0.3,
        "sideways": 0.5
    }
)
```

## Cấu hình phân tích (AnalysisConfig)

### 1. Cấu hình cơ bản

```python
from analytis.analysis_engine import AnalysisConfig

# Cấu hình mặc định
analysis_config = AnalysisConfig(
    min_score_threshold=10.0,    # Ngưỡng điểm tối thiểu
    lookback_days=365,           # Số ngày dữ liệu
    start_date=None,             # Ngày bắt đầu (None = tự động)
    end_date=None                # Ngày kết thúc (None = tự động)
)

# Cấu hình phân tích nhanh
quick_analysis = AnalysisConfig(
    min_score_threshold=5.0,     # Ngưỡng thấp
    lookback_days=90,            # Thời gian ngắn
    indicator_config=IndicatorConfig(ma_short=5, ma_long=30),
    scoring_config=ScoringConfig(strong_threshold=60.0)
)

# Cấu hình phân tích chi tiết
detailed_analysis = AnalysisConfig(
    min_score_threshold=20.0,    # Ngưỡng cao
    lookback_days=365,           # Thời gian dài
    indicator_config=IndicatorConfig(ma_short=20, ma_long=100),
    scoring_config=ScoringConfig(strong_threshold=90.0)
)
```

## Cấu hình theo thị trường

### 1. Thị trường Việt Nam

```python
# Cấu hình tối ưu cho thị trường Việt Nam
vietnam_config = AnalysisConfig(
    indicator_config=IndicatorConfig(
        ma_short=5,              # Thị trường biến động cao
        ma_long=30,              # Xu hướng ngắn hạn
        rsi_period=14,           # Chuẩn
        bb_period=20,            # Chuẩn
        bb_std=1.5,              # Dải hẹp hơn
        volume_avg_period=10     # Volume trung bình ngắn hạn
    ),
    scoring_config=ScoringConfig(
        strong_threshold=70.0,   # Ngưỡng vừa phải
        medium_threshold=25.0,
        buy_strong_threshold=-70.0,
        sell_strong_threshold=70.0,
        context_multipliers={
            "uptrend_buy": 1.8,      # Tăng mạnh trong xu hướng tăng
            "uptrend_sell": 0.4,
            "downtrend_sell": 1.8,
            "downtrend_buy": 0.4,
            "sideways": 0.6
        }
    ),
    min_score_threshold=15.0,
    lookback_days=180
)
```

### 2. Thị trường Mỹ

```python
# Cấu hình tối ưu cho thị trường Mỹ
us_config = AnalysisConfig(
    indicator_config=IndicatorConfig(
        ma_short=9,              # Chuẩn
        ma_long=50,              # Chuẩn
        rsi_period=14,           # Chuẩn
        bb_period=20,            # Chuẩn
        bb_std=2.0,              # Chuẩn
        volume_avg_period=20     # Chuẩn
    ),
    scoring_config=ScoringConfig(
        strong_threshold=75.0,   # Ngưỡng chuẩn
        medium_threshold=25.0,
        buy_strong_threshold=-75.0,
        sell_strong_threshold=75.0,
        context_multipliers={
            "uptrend_buy": 1.5,
            "uptrend_sell": 0.5,
            "downtrend_sell": 1.5,
            "downtrend_buy": 0.5,
            "sideways": 0.7
        }
    ),
    min_score_threshold=10.0,
    lookback_days=365
)
```

## Cấu hình theo chiến lược

### 1. Chiến lược Scalping

```python
# Cấu hình cho scalping (giao dịch ngắn hạn)
scalping_config = AnalysisConfig(
    indicator_config=IndicatorConfig(
        ma_short=3,              # MA rất ngắn
        ma_long=15,              # MA ngắn
        rsi_period=7,            # RSI ngắn
        bb_period=10,            # BB ngắn
        bb_std=1.2,              # Dải hẹp
        volume_avg_period=5      # Volume ngắn
    ),
    scoring_config=ScoringConfig(
        strong_threshold=50.0,   # Ngưỡng thấp
        medium_threshold=15.0,
        buy_strong_threshold=-50.0,
        sell_strong_threshold=50.0
    ),
    min_score_threshold=5.0,     # Ngưỡng rất thấp
    lookback_days=30             # Thời gian ngắn
)
```

### 2. Chiến lược Swing Trading

```python
# Cấu hình cho swing trading
swing_config = AnalysisConfig(
    indicator_config=IndicatorConfig(
        ma_short=9,              # MA ngắn
        ma_long=50,              # MA dài
        rsi_period=14,           # RSI chuẩn
        bb_period=20,            # BB chuẩn
        bb_std=2.0,              # Dải chuẩn
        volume_avg_period=20     # Volume chuẩn
    ),
    scoring_config=ScoringConfig(
        strong_threshold=75.0,   # Ngưỡng chuẩn
        medium_threshold=25.0,
        buy_strong_threshold=-75.0,
        sell_strong_threshold=75.0
    ),
    min_score_threshold=15.0,    # Ngưỡng vừa phải
    lookback_days=180            # Thời gian trung bình
)
```

### 3. Chiến lược Position Trading

```python
# Cấu hình cho position trading
position_config = AnalysisConfig(
    indicator_config=IndicatorConfig(
        ma_short=20,             # MA dài
        ma_long=100,             # MA rất dài
        rsi_period=21,           # RSI dài
        bb_period=30,            # BB dài
        bb_std=2.5,              # Dải rộng
        volume_avg_period=30     # Volume dài
    ),
    scoring_config=ScoringConfig(
        strong_threshold=90.0,   # Ngưỡng cao
        medium_threshold=40.0,
        buy_strong_threshold=-90.0,
        sell_strong_threshold=90.0
    ),
    min_score_threshold=25.0,    # Ngưỡng cao
    lookback_days=365            # Thời gian dài
)
```

## Tùy chỉnh cấu hình

### 1. Tạo cấu hình tùy chỉnh

```python
def create_custom_config(
    ma_short=9,
    ma_long=50,
    rsi_period=14,
    bb_std=2.0,
    strong_threshold=75.0,
    min_score_threshold=10.0,
    lookback_days=365
):
    """Tạo cấu hình tùy chỉnh"""
    
    indicator_config = IndicatorConfig(
        ma_short=ma_short,
        ma_long=ma_long,
        rsi_period=rsi_period,
        bb_std=bb_std
    )
    
    scoring_config = ScoringConfig(
        strong_threshold=strong_threshold,
        medium_threshold=strong_threshold / 3,
        weak_threshold=strong_threshold / 7.5,
        buy_strong_threshold=-strong_threshold,
        sell_strong_threshold=strong_threshold
    )
    
    analysis_config = AnalysisConfig(
        indicator_config=indicator_config,
        scoring_config=scoring_config,
        min_score_threshold=min_score_threshold,
        lookback_days=lookback_days
    )
    
    return analysis_config

# Sử dụng
custom_config = create_custom_config(
    ma_short=5,
    ma_long=30,
    rsi_period=10,
    bb_std=1.5,
    strong_threshold=60.0,
    min_score_threshold=8.0,
    lookback_days=180
)
```

### 2. Cấu hình từ file JSON

```python
import json

def load_config_from_file(config_file):
    """Tải cấu hình từ file JSON"""
    with open(config_file, 'r') as f:
        config_data = json.load(f)
    
    indicator_config = IndicatorConfig(**config_data.get('indicator', {}))
    scoring_config = ScoringConfig(**config_data.get('scoring', {}))
    
    analysis_config = AnalysisConfig(
        indicator_config=indicator_config,
        scoring_config=scoring_config,
        **config_data.get('analysis', {})
    )
    
    return analysis_config

# File config.json
config_json = {
    "indicator": {
        "ma_short": 9,
        "ma_long": 50,
        "rsi_period": 14,
        "bb_std": 2.0
    },
    "scoring": {
        "strong_threshold": 75.0,
        "medium_threshold": 25.0,
        "buy_strong_threshold": -75.0,
        "sell_strong_threshold": 75.0
    },
    "analysis": {
        "min_score_threshold": 10.0,
        "lookback_days": 365
    }
}

# Lưu cấu hình
with open('config.json', 'w') as f:
    json.dump(config_json, f, indent=2)

# Tải cấu hình
config = load_config_from_file('config.json')
```

## Best Practices

### 1. Cấu hình theo mục tiêu

```python
# Cấu hình cho mục tiêu tìm tín hiệu mua
buy_focused_config = AnalysisConfig(
    scoring_config=ScoringConfig(
        buy_strong_threshold=-60.0,  # Ngưỡng thấp hơn
        buy_medium_threshold=-20.0,
        sell_strong_threshold=80.0,  # Ngưỡng cao hơn
        context_multipliers={
            "uptrend_buy": 2.0,      # Tăng mạnh
            "uptrend_sell": 0.3,     # Giảm mạnh
            "downtrend_buy": 0.5,    # Giảm
            "downtrend_sell": 1.0,   # Bình thường
            "sideways": 0.8
        }
    ),
    min_score_threshold=8.0
)

# Cấu hình cho mục tiêu tìm tín hiệu bán
sell_focused_config = AnalysisConfig(
    scoring_config=ScoringConfig(
        buy_strong_threshold=-80.0,  # Ngưỡng cao hơn
        sell_strong_threshold=60.0,  # Ngưỡng thấp hơn
        sell_medium_threshold=20.0,
        context_multipliers={
            "uptrend_buy": 0.3,      # Giảm mạnh
            "uptrend_sell": 2.0,     # Tăng mạnh
            "downtrend_buy": 1.0,    # Bình thường
            "downtrend_sell": 0.5,   # Giảm
            "sideways": 0.8
        }
    ),
    min_score_threshold=8.0
)
```

### 2. Cấu hình theo biến động

```python
def get_volatility_adjusted_config(volatility_level):
    """Cấu hình điều chỉnh theo biến động"""
    
    if volatility_level == "low":
        return AnalysisConfig(
            indicator_config=IndicatorConfig(
                bb_std=1.5,          # Dải hẹp
                rsi_period=10        # RSI nhạy cảm hơn
            ),
            scoring_config=ScoringConfig(
                strong_threshold=60.0,  # Ngưỡng thấp hơn
                buy_strong_threshold=-60.0,
                sell_strong_threshold=60.0
            ),
            min_score_threshold=8.0
        )
    
    elif volatility_level == "high":
        return AnalysisConfig(
            indicator_config=IndicatorConfig(
                bb_std=2.5,          # Dải rộng
                rsi_period=21        # RSI ổn định hơn
            ),
            scoring_config=ScoringConfig(
                strong_threshold=90.0,  # Ngưỡng cao hơn
                buy_strong_threshold=-90.0,
                sell_strong_threshold=90.0
            ),
            min_score_threshold=15.0
        )
    
    else:  # medium
        return AnalysisConfig()  # Cấu hình mặc định
```

### 3. Cấu hình theo thời gian

```python
def get_time_based_config(timeframe):
    """Cấu hình theo khung thời gian"""
    
    if timeframe == "intraday":
        return AnalysisConfig(
            indicator_config=IndicatorConfig(
                ma_short=3,
                ma_long=15,
                rsi_period=7,
                bb_period=10
            ),
            min_score_threshold=5.0,
            lookback_days=30
        )
    
    elif timeframe == "daily":
        return AnalysisConfig(
            indicator_config=IndicatorConfig(
                ma_short=9,
                ma_long=50,
                rsi_period=14,
                bb_period=20
            ),
            min_score_threshold=10.0,
            lookback_days=180
        )
    
    elif timeframe == "weekly":
        return AnalysisConfig(
            indicator_config=IndicatorConfig(
                ma_short=20,
                ma_long=100,
                rsi_period=21,
                bb_period=30
            ),
            min_score_threshold=20.0,
            lookback_days=365
        )
    
    else:
        return AnalysisConfig()  # Cấu hình mặc định
```
