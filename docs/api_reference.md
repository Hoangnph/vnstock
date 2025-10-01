## Vnstock API Reference (VCI, TCBS, MSN)

This document summarizes all public APIs exposed via the unified imports and provider implementations, with parameters and usage examples. Prefer the unified interface (`from vnstock import ...`) unless you need provider-specific behaviors.

### Importing

```python
from vnstock import Vnstock, Listing, Quote, Company, Finance, Trading, Screener
# Advanced (fixed provider)
# from vnstock.explorer.vci import Listing, Quote, Company, Finance, Trading
# from vnstock.explorer.tcbs import Quote, Company, Finance, Trading, Screener
```

### Unified Orchestration

```python
from vnstock import Vnstock
stock = Vnstock().stock(symbol='ACB', source='VCI')
df = stock.quote.history(start='2024-01-01', end='2025-03-19', interval='1D')
info = stock.company.overview()
bs = stock.finance.balance_sheet(period='year', lang='vi', dropna=True)
```

---

## Listing (sources: VCI, MSN)

Unified class: `Listing(source='vci'|'msn')`

- VCI
  - all_symbols(show_log=False, to_df=True)
  - symbols_by_exchange(lang='vi'|'en', show_log=False, to_df=True)
  - symbols_by_industries(lang='vi'|'en', show_log=False, to_df=True)
  - industries_icb(show_log=False, to_df=True)
  - symbols_by_group(group, show_log=False, to_df=True)
  - Shortcuts: all_future_indices(), all_government_bonds(), all_covered_warrant(), all_bonds()

- MSN
  - search_symbol_id(query, locale=None, limit=10, show_log=False, to_df=True)

Examples

```python
from vnstock import Listing
Listing(source='vci').all_symbols()
Listing(source='vci').symbols_by_group('VN30')

from vnstock.explorer.msn import Listing as MSNListing
MSNListing().search_symbol_id('USDEUR', locale='en-us', limit=10)
```

Notes
- When using `Vnstock().stock(..., source='TCBS')`, listing data is auto-fallback to VCI because TCBS does not provide listing.

---

## Quote (sources: VCI, TCBS, MSN)

Unified class: `Quote(symbol, source='vci'|'tcbs'|'msn')`

Common methods
- history(...): historical OHLC
- intraday(...): tick-level trades (VCI, TCBS)
- price_depth(...): orderbook depth (VCI)

Parameter reference by provider

- VCI
  - history(start, end=None, interval='1D', to_df=True, show_log=False, count_back=None, floating=2)
  - intraday(page_size=100, last_time=None, to_df=True, show_log=False)
  - price_depth(to_df=True, show_log=False)

- TCBS
  - history(start, end=None, interval='1D', to_df=True, show_log=False, count_back=365, asset_type=None, _skip_long_check=False)
  - intraday(page_size=100, page=0, to_df=True, show_log=False)

- MSN
  - history(start, end, interval in {'1D','1W','1M'}, to_df=True, show_log=False, count_back=365)

Examples

```python
# VCI
from vnstock import Quote
Quote(symbol='ACB', source='vci').history(start='2024-01-01', end='2025-03-19', interval='1D')
Quote(symbol='ACB', source='vci').intraday(page_size=10_000)
Quote(symbol='ACB', source='vci').price_depth()

# VCI - other asset types
Quote(symbol='VN30F1M', source='vci').history(start='2024-01-02', end='2025-03-19', interval='1D')  # derivatives
Quote(symbol='VNINDEX', source='vci').history(start='2024-01-02', end='2025-03-19', interval='1D')  # index
Quote(symbol='CFPT2314', source='vci').history(start='2024-01-02', end='2025-03-19', interval='1D')  # CW
Quote(symbol='CII424002', source='vci').history(start='2024-01-02', end='2025-03-19', interval='1D')  # listed bond

# TCBS
Quote(symbol='VNINDEX', source='tcbs').history(start='2024-01-02', end='2024-11-01', interval='1D')

# MSN (via unified)
from vnstock import Vnstock
fx = Vnstock().fx(symbol='JPYVND', source='MSN')
fx.quote.history(start='2025-01-02', end='2025-03-20', interval='1D')
```

Notes
- VCI supports multiple asset types (stock, index, derivatives, covered warrants, listed bonds) using the same method signature.
- TCBS history auto-chunks long ranges (>365 days) per year.
- MSN requires `symbol_id` if called directly by provider; unified helpers map known symbols.

---

## Company (sources: VCI, TCBS)

Unified class: `Company(symbol, source='vci'|'tcbs')`

- VCI methods
  - overview()
  - shareholders()
  - officers(filter_by='working'|'resigned'|'all')
  - subsidiaries(filter_by='all'|'subsidiary')
  - affiliate()
  - news()
  - events()
  - reports()
  - ratio_summary()
  - trading_stats()

- TCBS methods (as shown in docs)
  - overview(), profile(), shareholders(), officers(), subsidiaries(), events(), news(), dividends(), insider_deals()

Examples

```python
from vnstock import Company
Company(symbol='ACB', source='vci').officers(filter_by='all')

from vnstock import Vnstock
Vnstock().stock(symbol='VCB', source='TCBS').company.dividends()

# TCBS notebook examples
tcbs_company = Vnstock().stock(symbol='VCB', source='TCBS').company
tcbs_company.overview()
tcbs_company.profile()
tcbs_company.shareholders()
tcbs_company.insider_deals()
tcbs_company.subsidiaries()
tcbs_company.officers()
tcbs_company.events()
tcbs_company.news()
```

Notes
- `affiliate()` is VCI-specific; TCBS has `dividends()` and `insider_deals()` in notebooks.

---

## Finance (sources: VCI, TCBS)

Unified class: `Finance(source='vci'|'tcbs', symbol, period='quarter', get_all=True, show_log=False)`

Methods
- balance_sheet(period={'year','quarter'}, lang={'vi','en'}, dropna=True, show_log=False)
- income_statement(period, lang, dropna, show_log)
- cash_flow(period, lang, dropna, show_log)
- ratio(period, lang, dropna=True, show_log=False, flatten_columns=False, separator='_', drop_levels=None)

Examples

```python
from vnstock import Finance
Finance(source='vci', symbol='VCI').balance_sheet(period='year', lang='vi', dropna=True)
Finance(source='vci', symbol='VCI').ratio(period='quarter', lang='en', flatten_columns=True, drop_levels=[0])

from vnstock import Vnstock
Vnstock().stock(symbol='VCI', source='TCBS').finance.balance_sheet(period='year')
Vnstock().stock(symbol='VCI', source='TCBS').finance.income_statement(period='quarter')
Vnstock().stock(symbol='VCI', source='TCBS').finance.cash_flow(period='year')
Vnstock().stock(symbol='VCI', source='TCBS').finance.ratio(period='quarter')
```

Notes
- TCBS may not support `dropna` (a warning is shown in notebooks).
- VCI provides multi-index ratios with optional flattening.

---

## Trading (sources: VCI, TCBS)

Unified class: `Trading(source='vci'|'tcbs', symbol=None)`

- VCI
  - price_board(symbols_list: list[str], to_df=True, show_log=False, flatten_columns=False, separator='_', drop_levels=None)

- TCBS
  - price_board(symbol_ls: list[str], std_columns=True, to_df=True, show_log=False)

Examples

```python
from vnstock import Trading
Trading(source='vci').price_board(['VCB','ACB','TCB','BID'])
Trading(source='tcbs').price_board(['VCB','ACB'], std_columns=False)

# VCI: display matrix with flattening options
Trading(source='vci').price_board(
    ['VCB','ACB','TCB','BID'],
    flatten_columns=True,
    drop_levels=[0]
).T  # remove .T to see original board orientation
```

---

## Screener (source: TCBS)

Class: `Screener(source='tcbs')`

- stock(params=None, limit=50, id=None, lang='vi')

Example

```python
from vnstock import Screener
Screener(source='tcbs').stock(params={"exchangeName":"HOSE,HNX,UPCOM"}, limit=1700)
```

---

## International Markets via MSN

Using unified helpers that map friendly symbols to MSN `symbol_id`:

```python
from vnstock import Vnstock
fx = Vnstock().fx(symbol='JPYVND', source='MSN')
fx.quote.history(start='2025-01-02', end='2025-03-20', interval='1D')

crypto = Vnstock().crypto(symbol='BTC', source='MSN')
crypto.quote.history(start='2023-01-01', end='2024-12-31', interval='1D')

index = Vnstock().world_index(symbol='DJI', source='MSN')
index.quote.history(start='2023-01-01', end='2024-12-31', interval='1D')
```

If you need direct `symbol_id`:

```python
from vnstock.explorer.msn import Listing
from vnstock.explorer.msn.quote import Quote as MSNQuote

sid = Listing().search_symbol_id('USDEUR', locale='en-us').iloc[0]['symbol_id']
MSNQuote(symbol_id=sid).history(start='2024-01-01', end='2024-12-31', interval='1D')
```

---

## ForeignTrade (sources: VCI, TCBS)

Unified class: `ForeignTrade(source='vci'|'tcbs', symbol=None)`

- daily(symbol, start, end) -> DataFrame
  - Expected columns: `date, buy_vol, sell_vol, buy_val, sell_val, net_vol, net_val`

Status
- In this repository, provider implementations are placeholders and raise clear `NotImplementedError` messages because historical endpoints are not wired yet.
- Once provider endpoints are available, this API will return daily foreign buy/sell metrics.

Example (current behavior)

```python
from vnstock import ForeignTrade
ft = ForeignTrade(source='vci')
try:
    ft.daily(symbol='PDR', start='2025-01-01', end='2025-09-25')
except NotImplementedError as e:
    print(e)
```

---

# StockAI Pipeline Reference

This section documents the StockAI data processing and analysis pipelines for automated stock data management and technical analysis.

## Overview

StockAI provides several pipeline modules for:
- Automated VN100 data updates from SSI API
- Technical indicator calculations
- Signal generation and analysis
- Database integration with tracking and error handling

## Pipeline Modules

### 1. VN100 Analysis Pipeline (`vn100_analysis_pipeline.py`)

**Purpose**: Integrated pipeline for daily VN100 data updates and automatic technical analysis.

**Features**:
- Fetches latest stock price and foreign trade data from SSI API
- Automatically calculates technical indicators for updated symbols
- Generates trading signals and analysis results
- Saves all results to modular database schema
- Includes comprehensive error handling and success tracking

**Usage**:
```bash
# Run with default settings (batch size 3, analyze last 30 days)
python fastapi/pipeline/vn100_analysis_pipeline.py

# Run with custom batch size and analysis days
python fastapi/pipeline/vn100_analysis_pipeline.py --batch 5 --analysis-days 60
```

**Parameters**:
- `--batch <int>`: Number of symbols to process concurrently (default: 3)
- `--analysis-days <int>`: Number of recent days to analyze (default: 30)

**Output**:
- Updates `stockai.stock_prices` and `stockai.foreign_trades` tables
- Calculates and stores indicators in `stockai.indicator_calculations`
- Generates analysis results in `stockai.analysis_results`
- Creates trading signals in `stockai.signal_results`
- Saves detailed summary to `output/pipeline_results_YYYYMMDD_HHMMSS.json`

### 2. VN100 Indicators Pipeline (`vn100_indicators_pipeline.py`)

**Purpose**: Dedicated pipeline for calculating and storing technical indicators only.

**Features**:
- Calculates comprehensive technical indicators for all VN100 symbols
- Supports historical data processing from specified start date
- Includes duplicate prevention mechanism
- Batch processing with configurable delays

**Usage**:
```bash
# Calculate indicators from 2014-01-01 to present
python fastapi/pipeline/vn100_indicators_pipeline.py --batch 3 --start-date 2014-01-01

# Calculate indicators for specific date range
python fastapi/pipeline/vn100_indicators_pipeline.py --batch 5 --start-date 2024-01-01
```

**Parameters**:
- `--batch <int>`: Batch size for processing symbols (default: 3)
- `--start-date <YYYY-MM-DD>`: Start date for indicator calculation (default: 2010-01-01)

**Output**:
- Stores indicator calculations in `stockai.indicator_calculations`
- Saves results summary to `output/indicators_results_YYYYMMDD_HHMMSS.json`

### 3. SSI VN100 Update with Tracking (`ssi_vn100_update_with_tracking.py`)

**Purpose**: Dedicated pipeline for incremental VN100 data updates using tracking system.

**Features**:
- Uses `StockUpdateTracking` table for incremental updates
- Fetches only new data since last update
- Prevents duplicate data insertion
- Comprehensive error handling and logging

**Usage**:
```bash
# Run with default batch size
python fastapi/pipeline/ssi_vn100_update_with_tracking.py

# Run with custom batch size
python fastapi/pipeline/ssi_vn100_update_with_tracking.py --batch 5
```

**Parameters**:
- `--batch <int>`: Batch size for processing symbols (default: 3)

**Output**:
- Updates `stockai.stock_prices` and `stockai.foreign_trades` tables
- Updates `stockai.stock_update_tracking` table
- Provides detailed console output with success/failure statistics

### 4. Force Overwrite Recent (`force_overwrite_recent.py`)

**Purpose**: Utility script to overwrite recent N days of data for VN100 symbols.

**Features**:
- Re-fetches and overwrites last N days of data
- Useful for correcting data errors
- Includes cleanup mechanism to remove duplicates
- Ensures data consistency for recent periods

**Usage**:
```bash
# Overwrite last 3 days of data (default)
python fastapi/pipeline/force_overwrite_recent.py

# Overwrite last 7 days of data
python fastapi/pipeline/force_overwrite_recent.py --days 7
```

**Parameters**:
- `--days <int>`: Number of recent days to overwrite (default: 3)

**Output**:
- Overwrites data in `stockai.stock_prices` and `stockai.foreign_trades`
- Removes duplicate records
- Provides summary of overwritten records

## Core Utilities

### Upsert Manager (`upsert_manager.py`)

**Purpose**: Handles batch insertion and updating of stock data with duplicate prevention.

**Key Methods**:
- `upsert_stock_prices_batch()`: Batch upsert for stock prices
- `upsert_foreign_trades_batch()`: Batch upsert for foreign trades
- `ensure_stock_exists()`: Ensures stock metadata exists

**Features**:
- Prevents duplicates based on `symbol` and `time`
- Handles batch processing efficiently
- Comprehensive error handling
- Transaction management

## Database Integration

### Tracking System

All pipelines integrate with the `stockai.stock_update_tracking` table to:
- Track last successful update for each symbol and data source
- Enable incremental updates
- Prevent unnecessary data fetching
- Monitor update success/failure rates

### Modular Analysis Database

Pipelines store analysis results in separate tables:
- `stockai.analysis_configurations`: Analysis configurations
- `stockai.indicator_calculations`: Technical indicator calculations
- `stockai.analysis_results`: Analysis results and summaries
- `stockai.signal_results`: Individual trading signals

## Error Handling & Monitoring

### Success Confirmation

All pipelines include comprehensive success confirmation:
- `success_count`: Number of successfully processed symbols
- `failed_symbols`: List of symbols that failed processing
- `total_records`: Total number of records updated
- `success_rate`: Percentage of successful operations
- `pipeline_duration_seconds`: Total execution time

### Error Handling

- Try-catch blocks around all operations
- Detailed error logging with context
- Graceful degradation (continues processing other symbols if one fails)
- Database transaction rollback on errors
- Comprehensive error reporting in output

### Logging

- Console output with progress indicators
- Detailed success/failure messages
- Timing information for performance monitoring
- Error details for troubleshooting

## Performance Optimization

### Batch Processing

- Configurable batch sizes to manage API rate limits
- Concurrent processing within batches using `asyncio.gather()`
- Delays between batches to prevent API blocking

### Rate Limiting

- 2-second delays between individual symbol processing
- 5-second delays between batches
- Configurable delays for different API endpoints

### Database Optimization

- Batch insertions for better performance
- Upsert operations to prevent duplicates
- Connection pooling for concurrent operations
- Transaction management for data integrity

## Configuration

### SSI API Configuration

Pipelines use centralized configuration in `assets/config/ssi_api_config.json`:
- API endpoints and URLs
- Headers and authentication
- Rate limiting settings
- Fallback configurations

### Analysis Configuration

Technical analysis uses `analytis.config.AnalysisConfig`:
- Indicator parameters (MA periods, RSI settings, etc.)
- Scoring thresholds
- Signal generation rules
- Data validation settings

## Output Files

### Pipeline Results

All pipelines generate JSON summary files in `output/` directory:
- `pipeline_results_YYYYMMDD_HHMMSS.json`: Complete pipeline results
- `indicators_results_YYYYMMDD_HHMMSS.json`: Indicator calculation results

### Web Interface

Analysis results can be viewed via web interface:
- `output/web/vn100_analytis_view/index.html`: VN100 analysis signals
- `output/web/stock_view/index.html`: Individual stock analysis

## Best Practices

### Daily Operations

1. **Use VN100 Analysis Pipeline** for daily operations:
   ```bash
   python fastapi/pipeline/vn100_analysis_pipeline.py --batch 3 --analysis-days 30
   ```

2. **Monitor success rates** and failed symbols
3. **Check output files** for detailed results
4. **Review web interface** for signal analysis

### Historical Data

1. **Use Indicators Pipeline** for historical indicator calculation:
   ```bash
   python fastapi/pipeline/vn100_indicators_pipeline.py --start-date 2014-01-01
   ```

2. **Use appropriate batch sizes** based on system resources
3. **Monitor progress** through console output

### Data Correction

1. **Use Force Overwrite** for recent data corrections:
   ```bash
   python fastapi/pipeline/force_overwrite_recent.py --days 3
   ```

2. **Verify data consistency** after corrections
3. **Check tracking table** for update status

## Troubleshooting

### Common Issues

1. **API Rate Limiting**: Reduce batch size or increase delays
2. **Database Connection**: Check database configuration and connectivity
3. **Memory Issues**: Process smaller batches or reduce analysis days
4. **Data Inconsistency**: Use force overwrite for recent data

### Monitoring

1. **Check console output** for error messages
2. **Review output JSON files** for detailed results
3. **Monitor database tables** for data consistency
4. **Use web interface** to verify analysis results

---

## Error Handling & Export Tips
- Market-session constraints: Intraday endpoints (VCI/TCBS) may be unavailable during pre-open preparation windows.
- Parameter support varies by provider. For example, TCBS `finance.ratio` may ignore `dropna` (warning in notebook); prefer provider defaults.
- Date formats: Use `YYYY-MM-DD`. VCI also accepts `YYYY-MM-DD HH:MM:SS` windows for higher precision.
- Large ranges: TCBS automatically chunks long daily history (>365 days). VCI supports `count_back` to limit rows.
- Export: Any DataFrame can be exported via `df.to_csv(...)` or `df.to_excel(...)`.

## Tips & Notes
- Prefer unified classes for stability; you can change `source` without changing call sites.
- Date strings should be `YYYY-MM-DD`; VCI also accepts `YYYY-MM-DD HH:MM:SS` for higher precision windows.
- Intraday endpoints depend on market session; providers may block during pre-open preparation.
- All returns are Pandas DataFrame/Series; use `.to_csv()`/`.to_excel()` to export.


