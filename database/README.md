# StockAI Database

Hệ thống cơ sở dữ liệu cho StockAI với PostgreSQL, TimescaleDB và FastAPI.

## 📋 Tổng quan

StockAI Database được thiết kế để lưu trữ và quản lý dữ liệu chứng khoán Việt Nam với các tính năng:

- **PostgreSQL 15** với TimescaleDB extension cho time-series data
- **Redis** cho caching và session management
- **FastAPI** với async support và type hints
- **SQLAlchemy 2.0** với async ORM
- **Docker Compose** cho containerization
- **VN100** stocks data với đầy đủ metadata

## 🏗️ Kiến trúc

```
database/
├── docker/                 # Docker configuration
│   ├── docker-compose.yml  # Main compose file
│   ├── env.example         # Environment variables template
│   ├── init/               # Database initialization scripts
│   └── scripts/            # Utility scripts
├── api/                    # FastAPI application
│   ├── database.py         # Database connection management
│   ├── repositories.py     # Repository pattern implementation
│   ├── fastapi_app.py      # FastAPI application
│   └── __init__.py
├── schema/                 # Database models
│   ├── models.py           # SQLAlchemy models
│   └── __init__.py
└── scripts/                # Management scripts
    ├── init_database.py    # Database initialization
    ├── run_api.py          # API server runner
    └── __init__.py
```

## 🚀 Cài đặt và Chạy

### 1. Yêu cầu hệ thống

- Docker và Docker Compose
- Python 3.10+
- 8GB RAM (khuyến nghị)
- 50GB disk space

### 2. Cài đặt dependencies

```bash
# Cài đặt Python dependencies
pip install -r requirements.txt

# Hoặc cài đặt từ pyproject.toml
pip install -e .
```

### 3. Cấu hình môi trường

```bash
# Copy file cấu hình mẫu
cp database/docker/env.example database/docker/.env

# Chỉnh sửa các biến môi trường theo nhu cầu
nano database/docker/.env
```

### 4. Khởi động database

```bash
# Di chuyển vào thư mục docker
cd database/docker

# Khởi động các services
docker-compose up -d

# Kiểm tra trạng thái
docker-compose ps
```

### 5. Khởi tạo database

```bash
# Chạy script khởi tạo
python database/scripts/init_database.py

# Hoặc chạy trực tiếp
cd database/scripts
python init_database.py
```

### 6. Chạy API server

```bash
# Chạy FastAPI server
python database/scripts/run_api.py

# Hoặc sử dụng uvicorn trực tiếp
uvicorn database.api.fastapi_app:app --host 0.0.0.0 --port 8000 --reload
```

## 📊 Cấu trúc Database

### Tables

#### 1. `stocks` - Thông tin cổ phiếu
```sql
CREATE TABLE stockai.stocks (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    exchange market_exchange NOT NULL,
    sector VARCHAR(100),
    industry VARCHAR(100),
    market_cap_tier VARCHAR(20),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### 2. `stock_prices` - Dữ liệu giá cổ phiếu (TimescaleDB Hypertable)
```sql
CREATE TABLE stockai.stock_prices (
    id BIGSERIAL,
    stock_id INTEGER NOT NULL REFERENCES stockai.stocks(id),
    symbol VARCHAR(10) NOT NULL,
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    open DECIMAL(15,2) NOT NULL,
    high DECIMAL(15,2) NOT NULL,
    low DECIMAL(15,2) NOT NULL,
    close DECIMAL(15,2) NOT NULL,
    volume BIGINT NOT NULL DEFAULT 0,
    value DECIMAL(20,2) GENERATED ALWAYS AS (close * volume) STORED,
    source data_source DEFAULT 'VCI',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (id, time)
);
```

#### 3. `foreign_trades` - Dữ liệu giao dịch nước ngoài (TimescaleDB Hypertable)
```sql
CREATE TABLE stockai.foreign_trades (
    id BIGSERIAL,
    stock_id INTEGER NOT NULL REFERENCES stockai.stocks(id),
    symbol VARCHAR(10) NOT NULL,
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    buy_volume BIGINT NOT NULL DEFAULT 0,
    sell_volume BIGINT NOT NULL DEFAULT 0,
    net_volume BIGINT GENERATED ALWAYS AS (buy_volume - sell_volume) STORED,
    buy_value DECIMAL(20,2) NOT NULL DEFAULT 0,
    sell_value DECIMAL(20,2) NOT NULL DEFAULT 0,
    net_value DECIMAL(20,2) GENERATED ALWAYS AS (buy_value - sell_value) STORED,
    source data_source DEFAULT 'VCI',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (id, time)
);
```

#### 4. `stock_statistics` - Thống kê và chỉ số kỹ thuật (TimescaleDB Hypertable)
```sql
CREATE TABLE stockai.stock_statistics (
    id BIGSERIAL,
    stock_id INTEGER NOT NULL REFERENCES stockai.stocks(id),
    symbol VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    daily_return DECIMAL(10,6),
    volatility DECIMAL(10,6),
    avg_volume_20d BIGINT,
    avg_volume_50d BIGINT,
    rsi_14 DECIMAL(5,2),
    sma_20 DECIMAL(15,2),
    sma_50 DECIMAL(15,2),
    ema_20 DECIMAL(15,2),
    ema_50 DECIMAL(15,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (id, date)
);
```

### Materialized Views

#### 1. `daily_summary` - Tóm tắt hàng ngày
```sql
CREATE MATERIALIZED VIEW stockai.daily_summary AS
SELECT 
    s.symbol,
    s.name,
    s.exchange,
    s.sector,
    sp.time::date as date,
    sp.open,
    sp.high,
    sp.low,
    sp.close,
    sp.volume,
    sp.value,
    ft.buy_volume,
    ft.sell_volume,
    ft.net_volume,
    ft.buy_value,
    ft.sell_value,
    ft.net_value,
    CASE 
        WHEN LAG(sp.close) OVER (PARTITION BY s.symbol ORDER BY sp.time) IS NOT NULL 
        THEN ROUND(((sp.close - LAG(sp.close) OVER (PARTITION BY s.symbol ORDER BY sp.time)) / LAG(sp.close) OVER (PARTITION BY s.symbol ORDER BY sp.time)) * 100, 2)
        ELSE NULL 
    END as daily_return_pct
FROM stockai.stocks s
JOIN stockai.stock_prices sp ON s.id = sp.stock_id
LEFT JOIN stockai.foreign_trades ft ON s.id = ft.stock_id AND sp.time::date = ft.time::date
WHERE s.is_active = true
ORDER BY s.symbol, sp.time DESC;
```

#### 2. `sector_performance` - Hiệu suất theo ngành
```sql
CREATE MATERIALIZED VIEW stockai.sector_performance AS
SELECT 
    s.sector,
    COUNT(DISTINCT s.symbol) as stock_count,
    AVG(sp.close) as avg_price,
    SUM(sp.volume) as total_volume,
    SUM(sp.value) as total_value,
    AVG(ft.net_volume) as avg_net_foreign_volume,
    sp.time::date as date
FROM stockai.stocks s
JOIN stockai.stock_prices sp ON s.id = sp.stock_id
LEFT JOIN stockai.foreign_trades ft ON s.id = ft.stock_id AND sp.time::date = ft.time::date
WHERE s.is_active = true
GROUP BY s.sector, sp.time::date
ORDER BY s.sector, sp.time::date DESC;
```

## 🔌 API Endpoints

### Health Check
- `GET /health` - Kiểm tra trạng thái API

### Stocks
- `GET /stocks` - Lấy danh sách cổ phiếu
- `GET /stocks/vn100` - Lấy danh sách VN100
- `GET /stocks/{stock_id}` - Lấy thông tin cổ phiếu theo ID
- `GET /stocks/symbol/{symbol}` - Lấy thông tin cổ phiếu theo symbol
- `POST /stocks` - Tạo cổ phiếu mới
- `PUT /stocks/{stock_id}` - Cập nhật cổ phiếu
- `DELETE /stocks/{stock_id}` - Xóa cổ phiếu (soft delete)

### Stock Prices
- `GET /stock-prices/{symbol}/latest` - Lấy giá mới nhất
- `GET /stock-prices/{symbol}/history` - Lấy lịch sử giá
- `POST /stock-prices` - Tạo bản ghi giá mới

### Foreign Trades
- `GET /foreign-trades/{symbol}/history` - Lấy lịch sử giao dịch nước ngoài
- `POST /foreign-trades` - Tạo bản ghi giao dịch nước ngoài mới

### Stock Statistics
- `GET /stock-statistics/{symbol}/latest` - Lấy thống kê mới nhất
- `POST /stock-statistics` - Tạo bản ghi thống kê mới

## 🛠️ Quản lý Database

### Backup và Restore

```bash
# Tạo backup
docker exec stockai_backup /scripts/backup.sh backup

# Restore từ backup
docker exec stockai_backup /scripts/backup.sh restore /backups/stockai_backup_20250101_120000.sql

# Xem thống kê backup
docker exec stockai_backup /scripts/backup.sh stats

# Dọn dẹp backup cũ
docker exec stockai_backup /scripts/backup.sh cleanup
```

### Monitoring

```bash
# Xem logs
docker-compose logs -f postgres
docker-compose logs -f redis

# Kiểm tra trạng thái
docker-compose ps

# Xem sử dụng tài nguyên
docker stats
```

### pgAdmin

Truy cập pgAdmin tại: http://localhost:8080

- Email: admin@stockai.com
- Password: admin_password_2025

## 🔧 Cấu hình

### Environment Variables

```bash
# Database
POSTGRES_DB=stockai
POSTGRES_USER=stockai_user
POSTGRES_PASSWORD=stockai_password_2025
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# TimescaleDB
TIMESCALE_ENABLED=true
TIMESCALE_COMPRESSION_ENABLED=true
TIMESCALE_RETENTION_DAYS=2555

# API
API_HOST=0.0.0.0
API_PORT=8000
```

### TimescaleDB Configuration

```sql
-- Enable compression
ALTER TABLE stockai.stock_prices SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol'
);

-- Add retention policy
SELECT add_retention_policy('stockai.stock_prices', INTERVAL '7 years');

-- Create continuous aggregates
CREATE MATERIALIZED VIEW stockai.daily_ohlc
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 day', time) AS day,
    symbol,
    first(open, time) AS open,
    max(high) AS high,
    min(low) AS low,
    last(close, time) AS close,
    sum(volume) AS volume
FROM stockai.stock_prices
GROUP BY day, symbol;
```

## 📈 Performance Optimization

### Indexes

```sql
-- Time-series indexes
CREATE INDEX CONCURRENTLY idx_stock_prices_symbol_time ON stockai.stock_prices(symbol, time DESC);
CREATE INDEX CONCURRENTLY idx_foreign_trades_symbol_time ON stockai.foreign_trades(symbol, time DESC);

-- Composite indexes
CREATE INDEX CONCURRENTLY idx_stock_prices_symbol_date ON stockai.stock_prices(symbol, DATE(time));
CREATE INDEX CONCURRENTLY idx_stocks_sector_tier ON stockai.stocks(sector, market_cap_tier);
```

### Query Optimization

```sql
-- Use time_bucket for aggregation
SELECT 
    time_bucket('1 day', time) AS day,
    symbol,
    avg(close) AS avg_price,
    sum(volume) AS total_volume
FROM stockai.stock_prices
WHERE time >= NOW() - INTERVAL '30 days'
GROUP BY day, symbol
ORDER BY day DESC, symbol;

-- Use materialized views for common queries
SELECT * FROM stockai.daily_summary 
WHERE symbol = 'VCB' 
AND date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY date DESC;
```

## 🧪 Testing

### Unit Tests

```bash
# Chạy tests
python -m pytest tests/ -v

# Chạy tests với coverage
python -m pytest tests/ --cov=database --cov-report=html
```

### API Tests

```bash
# Test API endpoints
curl http://localhost:8000/health
curl http://localhost:8000/stocks/vn100
curl http://localhost:8000/stock-prices/VCB/latest
```

## 🚨 Troubleshooting

### Common Issues

1. **Database connection failed**
   ```bash
   # Kiểm tra Docker containers
   docker-compose ps
   
   # Xem logs
   docker-compose logs postgres
   ```

2. **TimescaleDB extension not found**
   ```bash
   # Kiểm tra extension
   docker exec stockai_postgres psql -U stockai_user -d stockai -c "SELECT * FROM pg_extension WHERE extname = 'timescaledb';"
   ```

3. **API server not starting**
   ```bash
   # Kiểm tra dependencies
   pip list | grep fastapi
   pip list | grep sqlalchemy
   
   # Kiểm tra logs
   python database/scripts/run_api.py
   ```

### Performance Issues

1. **Slow queries**
   - Kiểm tra indexes
   - Sử dụng EXPLAIN ANALYZE
   - Tối ưu hóa queries

2. **High memory usage**
   - Điều chỉnh pool_size
   - Sử dụng connection pooling
   - Monitor memory usage

## 📚 Tài liệu tham khảo

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [TimescaleDB Documentation](https://docs.timescale.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

## 🤝 Đóng góp

1. Fork repository
2. Tạo feature branch
3. Commit changes
4. Push to branch
5. Tạo Pull Request

## 📄 License

Dự án này được phát hành theo giấy phép tuỳ chỉnh. Xem file LICENSE.md để biết thêm chi tiết.

## 📞 Hỗ trợ

- Email: support@stockai.com
- GitHub Issues: [Tạo issue mới](https://github.com/your-repo/stockai/issues)
- Documentation: [Xem tài liệu](https://docs.stockai.com)

---

**StockAI Team** - Mang dữ liệu chứng khoán đến gần hơn với mọi người! 🚀
