-- Initialize StockAI Database
-- This script sets up the initial database structure for StockAI

-- Create extensions
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS stockai;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS cache;

-- Set default search path
ALTER DATABASE stockai SET search_path TO stockai, public;

-- Create custom types
DO $$ 
BEGIN
    -- Market exchange type
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'market_exchange') THEN
        CREATE TYPE market_exchange AS ENUM ('HOSE', 'HNX', 'UPCOM');
    END IF;
    
    -- Data source type
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'data_source') THEN
        CREATE TYPE data_source AS ENUM ('VCI', 'TCBS', 'SSI', 'VNDIRECT');
    END IF;
    
    -- Time interval type
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'time_interval') THEN
        CREATE TYPE time_interval AS ENUM ('1D', '1H', '30M', '15M', '5M', '1M');
    END IF;
END $$;

-- Create stocks table (metadata)
CREATE TABLE IF NOT EXISTS stockai.stocks (
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

-- Create stock_prices table (TimescaleDB hypertable)
CREATE TABLE IF NOT EXISTS stockai.stock_prices (
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

-- Create foreign_trades table (TimescaleDB hypertable)
CREATE TABLE IF NOT EXISTS stockai.foreign_trades (
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

-- Create stock_statistics table for aggregated data
CREATE TABLE IF NOT EXISTS stockai.stock_statistics (
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

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_stocks_symbol ON stockai.stocks(symbol);
CREATE INDEX IF NOT EXISTS idx_stocks_exchange ON stockai.stocks(exchange);
CREATE INDEX IF NOT EXISTS idx_stocks_sector ON stockai.stocks(sector);
CREATE INDEX IF NOT EXISTS idx_stocks_active ON stockai.stocks(is_active);

CREATE INDEX IF NOT EXISTS idx_stock_prices_symbol_time ON stockai.stock_prices(symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_stock_prices_stock_id_time ON stockai.stock_prices(stock_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_stock_prices_time ON stockai.stock_prices(time DESC);

CREATE INDEX IF NOT EXISTS idx_foreign_trades_symbol_time ON stockai.foreign_trades(symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_foreign_trades_stock_id_time ON stockai.foreign_trades(stock_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_foreign_trades_time ON stockai.foreign_trades(time DESC);

CREATE INDEX IF NOT EXISTS idx_stock_statistics_symbol_date ON stockai.stock_statistics(symbol, date DESC);
CREATE INDEX IF NOT EXISTS idx_stock_statistics_stock_id_date ON stockai.stock_statistics(stock_id, date DESC);

-- Convert to TimescaleDB hypertables
SELECT create_hypertable('stockai.stock_prices', 'time', if_not_exists => TRUE);
SELECT create_hypertable('stockai.foreign_trades', 'time', if_not_exists => TRUE);
SELECT create_hypertable('stockai.stock_statistics', 'date', if_not_exists => TRUE);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION stockai.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for stocks table
DROP TRIGGER IF EXISTS update_stocks_updated_at ON stockai.stocks;
CREATE TRIGGER update_stocks_updated_at
    BEFORE UPDATE ON stockai.stocks
    FOR EACH ROW
    EXECUTE FUNCTION stockai.update_updated_at_column();

-- Create materialized view for daily summary
CREATE MATERIALIZED VIEW IF NOT EXISTS stockai.daily_summary AS
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

-- Create index on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_summary_symbol_date ON stockai.daily_summary(symbol, date);

-- Create refresh function for materialized view
CREATE OR REPLACE FUNCTION stockai.refresh_daily_summary()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY stockai.daily_summary;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT USAGE ON SCHEMA stockai TO stockai_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA stockai TO stockai_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA stockai TO stockai_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA stockai TO stockai_user;

-- Create comments
COMMENT ON SCHEMA stockai IS 'Main schema for StockAI application data';
COMMENT ON TABLE stockai.stocks IS 'Stock symbols metadata and information';
COMMENT ON TABLE stockai.stock_prices IS 'Historical stock price data (OHLCV)';
COMMENT ON TABLE stockai.foreign_trades IS 'Foreign trading data (buy/sell volumes)';
COMMENT ON TABLE stockai.stock_statistics IS 'Calculated technical indicators and statistics';
COMMENT ON MATERIALIZED VIEW stockai.daily_summary IS 'Daily summary view combining prices and foreign trades';

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'StockAI database initialization completed successfully!';
    RAISE NOTICE 'TimescaleDB hypertables created for time-series data';
    RAISE NOTICE 'Materialized view created for daily summaries';
    RAISE NOTICE 'All indexes and constraints applied';
END $$;
