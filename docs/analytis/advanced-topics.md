# Chủ đề nâng cao

## Tối ưu hiệu suất

### 1. Phân tích bất đồng bộ
```python
import asyncio
from analytis.analysis_engine import AnalysisEngine

async def analyze_multiple_symbols(symbols):
    engine = AnalysisEngine()
    tasks = []
    
    for symbol in symbols:
        task = engine.analyze_symbol_async(symbol, start_date, end_date)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    return results
```

### 2. Caching kết quả
```python
from functools import lru_cache
from analytis.analysis_engine import AnalysisEngine

@lru_cache(maxsize=100)
def get_cached_analysis(symbol, config_hash, start_date, end_date):
    engine = AnalysisEngine()
    return engine.analyze_symbol(symbol, start_date, end_date)
```

### 3. Batch processing
```python
def process_batch(symbols, batch_size=10):
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        results = analyze_batch(batch)
        yield results
```

## Tích hợp với hệ thống khác

### 1. API REST
```python
from fastapi import FastAPI
from analytis.analysis_engine import AnalysisEngine

app = FastAPI()
engine = AnalysisEngine()

@app.get("/analyze/{symbol}")
async def analyze_symbol(symbol: str, start_date: str, end_date: str):
    result = engine.analyze_symbol(symbol, start_date, end_date)
    return result.to_dict()
```

### 2. WebSocket
```python
from fastapi import WebSocket
import asyncio

async def websocket_analysis(websocket: WebSocket, symbol: str):
    engine = AnalysisEngine()
    
    while True:
        result = engine.analyze_symbol(symbol, start_date, end_date)
        await websocket.send_json(result.to_dict())
        await asyncio.sleep(60)  # Cập nhật mỗi phút
```

### 3. Message Queue
```python
import redis
from analytis.analysis_engine import AnalysisEngine

redis_client = redis.Redis()
engine = AnalysisEngine()

def process_analysis_queue():
    while True:
        message = redis_client.blpop('analysis_queue')
        symbol = message[1].decode()
        
        result = engine.analyze_symbol(symbol, start_date, end_date)
        redis_client.lpush('results_queue', result.to_json())
```

## Monitoring và Logging

### 1. Structured Logging
```python
import logging
import json
from datetime import datetime

class AnalysisLogger:
    def __init__(self):
        self.logger = logging.getLogger('analytis')
        self.logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_analysis(self, symbol, result, duration):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'symbol': symbol,
            'signals_count': len(result.signals),
            'duration_ms': duration,
            'success': True
        }
        self.logger.info(json.dumps(log_data))
```

### 2. Metrics Collection
```python
from prometheus_client import Counter, Histogram, Gauge

# Metrics
analysis_counter = Counter('analytis_analyses_total', 'Total analyses', ['symbol', 'status'])
analysis_duration = Histogram('analytis_analysis_duration_seconds', 'Analysis duration')
signals_gauge = Gauge('analytis_signals_total', 'Total signals', ['symbol', 'action'])

def analyze_with_metrics(symbol, start_date, end_date):
    with analysis_duration.time():
        result = engine.analyze_symbol(symbol, start_date, end_date)
        
        analysis_counter.labels(symbol=symbol, status='success').inc()
        
        for signal in result.signals:
            signals_gauge.labels(symbol=symbol, action=signal.action.value).inc()
        
        return result
```

## Testing

### 1. Unit Tests
```python
import unittest
from unittest.mock import Mock, patch
from analytis.analysis_engine import AnalysisEngine

class TestAnalysisEngine(unittest.TestCase):
    def setUp(self):
        self.engine = AnalysisEngine()
    
    @patch('analytis.data.loader.load_stock_data')
    def test_analyze_symbol(self, mock_load_data):
        # Mock data
        mock_data = pd.DataFrame({
            'Close': [100, 101, 102, 103, 104],
            'Volume': [1000, 1100, 1200, 1300, 1400]
        })
        mock_load_data.return_value = mock_data
        
        # Test
        result = self.engine.analyze_symbol('TEST', '2024-01-01', '2024-01-05')
        
        # Assertions
        self.assertIsNotNone(result)
        self.assertGreater(len(result.signals), 0)
```

### 2. Integration Tests
```python
import pytest
from analytis.analysis_engine_db import DatabaseIntegratedAnalysisEngine

@pytest.mark.asyncio
async def test_database_integration():
    engine = DatabaseIntegratedAnalysisEngine()
    
    result = await engine.analyze_symbol('PDR', '2024-01-01', '2024-01-31')
    
    assert result.analysis_result_id is not None
    assert len(result.signals) > 0
    
    # Verify database
    history = await engine.get_analysis_history('PDR', limit=1)
    assert len(history) == 1
    assert history[0]['symbol'] == 'PDR'
```

### 3. Performance Tests
```python
import time
import statistics
from analytis.analysis_engine import AnalysisEngine

def benchmark_analysis(symbols, iterations=10):
    engine = AnalysisEngine()
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

## Security

### 1. Input Validation
```python
from pydantic import BaseModel, validator
from datetime import datetime

class AnalysisRequest(BaseModel):
    symbol: str
    start_date: str
    end_date: str
    
    @validator('symbol')
    def validate_symbol(cls, v):
        if not v.isalpha() or len(v) > 10:
            raise ValueError('Invalid symbol format')
        return v.upper()
    
    @validator('start_date', 'end_date')
    def validate_date(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('Invalid date format')
        return v
```

### 2. Rate Limiting
```python
from functools import wraps
import time
from collections import defaultdict

def rate_limit(calls_per_minute=60):
    def decorator(func):
        calls = defaultdict(list)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            key = args[0] if args else 'default'
            
            # Clean old calls
            calls[key] = [call_time for call_time in calls[key] if now - call_time < 60]
            
            if len(calls[key]) >= calls_per_minute:
                raise Exception('Rate limit exceeded')
            
            calls[key].append(now)
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

@rate_limit(calls_per_minute=30)
def analyze_symbol(symbol, start_date, end_date):
    return engine.analyze_symbol(symbol, start_date, end_date)
```

## Deployment

### 1. Docker
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "-m", "analytis.cli"]
```

### 2. Kubernetes
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: analytis-engine
spec:
  replicas: 3
  selector:
    matchLabels:
      app: analytis-engine
  template:
    metadata:
      labels:
        app: analytis-engine
    spec:
      containers:
      - name: analytis
        image: analytis:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
```

### 3. CI/CD
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest
    - name: Run tests
      run: pytest tests/
    - name: Run analysis
      run: python analytis/test_new_architecture.py
```
