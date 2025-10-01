# StockAI Function Reference

This document provides comprehensive documentation for all functions and classes in the `/fastapi/func` module of StockAI.

## Table of Contents

1. [Overview](#overview)
2. [Data Fetching Functions](#data-fetching-functions)
3. [VN100 Management](#vn100-management)
4. [SSI API Integration](#ssi-api-integration)
5. [Data Processing](#data-processing)
6. [Configuration Management](#configuration-management)
7. [Database Integration](#database-integration)
8. [Utility Functions](#utility-functions)
9. [Examples](#examples)
10. [Error Handling](#error-handling)

## Overview

The `/fastapi/func` module contains core functionality for:
- Stock data fetching from multiple sources (VCI, TCBS, SSI)
- VN100 symbol management and database operations
- SSI API integration with tracking and incremental updates
- Data normalization and processing
- Configuration management
- Database integration utilities

## Data Fetching Functions

### `stock_data_fetcher.py`

#### `fetch_stock_data()`

**Purpose**: Main function to fetch comprehensive stock data including OHLCV and foreign trading data.

**Signature**:
```python
def fetch_stock_data(
    symbol: str,
    start_date: str = '2010-01-01',
    end_date: Optional[str] = None,
    source: str = 'VCI',
    include_foreign: bool = True,
    output_dir: Optional[str] = None,
    save_csv: bool = True,
    save_json: bool = True,
    web_json: bool = False,
    print_stats: bool = True
) -> Tuple[bool, pd.DataFrame, Dict[str, Any]]
```

**Parameters**:
- `symbol` (str): Stock symbol (e.g., 'PDR', 'VIC', 'VCB')
- `start_date` (str): Start date in YYYY-MM-DD format
- `end_date` (str, optional): End date in YYYY-MM-DD format, None for today
- `source` (str): Data source ('VCI', 'TCBS')
- `include_foreign` (bool): Include foreign trading data
- `output_dir` (str, optional): Output directory for saved files
- `save_csv` (bool): Save data as CSV file
- `save_json` (bool): Save data as JSON file
- `web_json` (bool): Save web-formatted JSON
- `print_stats` (bool): Print data statistics

**Returns**:
- `success` (bool): Whether the operation succeeded
- `df` (pd.DataFrame): Stock data with OHLCV and foreign trading
- `metadata` (dict): Metadata including statistics and file paths

**Example**:
```python
from fastapi.func.stock_data_fetcher import fetch_stock_data

success, df, metadata = fetch_stock_data(
    symbol='PDR',
    start_date='2020-01-01',
    end_date='2024-12-31',
    source='VCI',
    include_foreign=True,
    output_dir='./data/pdr',
    save_csv=True,
    save_json=True
)

if success:
    print(f"Fetched {len(df)} records for {metadata['symbol']}")
    print(f"Date range: {metadata['date_range']['start']} to {metadata['date_range']['end']}")
```

#### `StockDataFetcher` Class

**Purpose**: Object-oriented interface for stock data fetching with additional options.

**Methods**:

##### `__init__(source: str = 'VCI')`
Initialize the fetcher with a specific data source.

##### `fetch_stock_data(symbol, start_date, end_date=None) -> Tuple[bool, pd.DataFrame, Dict]`
Fetch stock data for a single symbol.

##### `save_data(df, symbol, start_date, end_date, output_dir, save_csv=True, save_json=True, web_json=False) -> Dict[str, str]`
Save DataFrame to files in various formats.

**Example**:
```python
from fastapi.func.stock_data_fetcher import StockDataFetcher

fetcher = StockDataFetcher(source='VCI')
success, df, metadata = fetcher.fetch_stock_data(
    symbol='PDR',
    start_date='2020-01-01',
    end_date='2024-12-31'
)

if success:
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
    print(f"Files saved: {saved_files}")
```

## VN100 Management

### `vn100_fetcher.py`

#### `get_vn100_symbols() -> List[str]`

**Purpose**: Get list of VN100 stock symbols.

**Returns**: List of 100 stock symbols with highest market cap and liquidity.

**Example**:
```python
from fastapi.func.vn100_fetcher import get_vn100_symbols

symbols = get_vn100_symbols()
print(f"VN100 contains {len(symbols)} symbols")
print(f"First 10: {symbols[:10]}")
```

#### `get_vn100_dataframe() -> pd.DataFrame`

**Purpose**: Get VN100 symbols as a DataFrame with additional information.

**Returns**: DataFrame with columns: symbol, name, sector, industry, market_cap, etc.

**Example**:
```python
from fastapi.func.vn100_fetcher import get_vn100_dataframe

df = get_vn100_dataframe()
print(f"VN100 DataFrame shape: {df.shape}")
print(df.head())
```

#### `get_vn100_by_sector(sector: str) -> List[str]`

**Purpose**: Get VN100 symbols filtered by sector.

**Parameters**:
- `sector` (str): Sector name (e.g., 'Banking', 'Technology')

**Returns**: List of symbols in the specified sector.

**Example**:
```python
from fastapi.func.vn100_fetcher import get_vn100_by_sector

banking_symbols = get_vn100_by_sector('Banking')
print(f"Banking sector: {banking_symbols}")
```

#### `get_vn100_top_n(n: int) -> List[str]`

**Purpose**: Get top N VN100 symbols by market cap.

**Parameters**:
- `n` (int): Number of top symbols to return

**Returns**: List of top N symbols.

**Example**:
```python
from fastapi.func.vn100_fetcher import get_vn100_top_n

top_20 = get_vn100_top_n(20)
print(f"Top 20 VN100: {top_20}")
```

#### `save_vn100_csv(file_path: str) -> bool`

**Purpose**: Save VN100 symbols to CSV file.

**Parameters**:
- `file_path` (str): Path to save CSV file

**Returns**: True if successful, False otherwise.

**Example**:
```python
from fastapi.func.vn100_fetcher import save_vn100_csv

success = save_vn100_csv('data/vn100.csv')
if success:
    print("VN100 saved to CSV successfully")
```

#### `VN100Fetcher` Class

**Purpose**: Object-oriented interface for VN100 operations.

**Methods**:
- `get_symbols()`: Get list of symbols
- `get_dataframe()`: Get DataFrame with symbol information
- `get_by_sector(sector)`: Get symbols by sector
- `get_top_n(n)`: Get top N symbols
- `save_csv(file_path)`: Save to CSV file

### `vn100_database_loader.py`

#### `VN100DatabaseLoader` Class

**Purpose**: Load VN100 symbols from database instead of CSV files.

**Methods**:

##### `get_vn100_symbols_from_db(status: Optional[VN100Status] = None) -> List[str]`

**Purpose**: Get VN100 symbols from database with optional status filter.

**Parameters**:
- `status` (VN100Status, optional): Filter by status (NEW, ACTIVE, INACTIVE, UNKNOWN)

**Returns**: List of VN100 symbols from database.

**Example**:
```python
from fastapi.func.vn100_database_loader import VN100DatabaseLoader
from database.schema.models import VN100Status

loader = VN100DatabaseLoader()
active_symbols = await loader.get_vn100_symbols_from_db(VN100Status.ACTIVE)
print(f"Active VN100 symbols: {len(active_symbols)}")
```

##### `get_active_vn100_symbols() -> List[str]`

**Purpose**: Get only active VN100 symbols from database.

**Returns**: List of active VN100 symbols.

**Example**:
```python
from fastapi.func.vn100_database_loader import VN100DatabaseLoader

loader = VN100DatabaseLoader()
symbols = await loader.get_active_vn100_symbols()
print(f"Active VN100: {symbols}")
```

##### `get_vn100_with_details() -> List[Dict[str, Any]]`

**Purpose**: Get VN100 symbols with detailed information from database.

**Returns**: List of dictionaries with symbol details.

**Example**:
```python
from fastapi.func.vn100_database_loader import VN100DatabaseLoader

loader = VN100DatabaseLoader()
details = await loader.get_vn100_with_details()
for detail in details[:5]:
    print(f"{detail['symbol']}: {detail['name']} - {detail['sector']}")
```

## SSI API Integration

### `ssi_fetcher_with_tracking.py`

#### `SSIFetcherWithTracking` Class

**Purpose**: Enhanced SSI fetcher with update tracking for incremental updates.

**Key Features**:
- Uses tracking table to determine start date for updates
- Prevents duplicate data insertion
- Enables efficient incremental updates
- Comprehensive error handling and logging

**Methods**:

##### `fetch_daily_with_tracking(symbol: str, target_end_date: date) -> Tuple[bool, Optional[pd.DataFrame], Optional[date]]`

**Purpose**: Fetch daily stock data with tracking integration.

**Parameters**:
- `symbol` (str): Stock symbol
- `target_end_date` (date): Target end date for data fetching

**Returns**:
- `success` (bool): Whether the operation succeeded
- `df` (pd.DataFrame, optional): Stock data DataFrame
- `last_updated_date` (date, optional): Last updated date

**Example**:
```python
from fastapi.func.ssi_fetcher_with_tracking import SSIFetcherWithTracking
from datetime import date

fetcher = SSIFetcherWithTracking()
success, df, last_date = await fetcher.fetch_daily_with_tracking('PDR', date.today())

if success and df is not None:
    print(f"Fetched {len(df)} records for PDR")
    print(f"Last updated: {last_date}")
```

##### `update_tracking_success(symbol: str, last_updated_date: date, records_count: int, duration_seconds: int) -> None`

**Purpose**: Update tracking table with successful operation details.

**Parameters**:
- `symbol` (str): Stock symbol
- `last_updated_date` (date): Last updated date
- `records_count` (int): Number of records processed
- `duration_seconds` (int): Operation duration in seconds

##### `update_tracking_error(symbol: str, error_message: str) -> None`

**Purpose**: Update tracking table with error information.

**Parameters**:
- `symbol` (str): Stock symbol
- `error_message` (str): Error message

##### `get_tracking_info(symbol: str) -> Optional[Dict[str, Any]]`

**Purpose**: Get tracking information for a symbol.

**Parameters**:
- `symbol` (str): Stock symbol

**Returns**: Dictionary with tracking information or None.

**Example**:
```python
from fastapi.func.ssi_fetcher_with_tracking import SSIFetcherWithTracking

fetcher = SSIFetcherWithTracking()
tracking_info = await fetcher.get_tracking_info('PDR')
if tracking_info:
    print(f"Last update: {tracking_info['last_updated_date']}")
    print(f"Records: {tracking_info['records_count']}")
    print(f"Status: {tracking_info['status']}")
```

### `ssi_fetcher.py`

#### `SSIFetcher` Class

**Purpose**: Basic SSI API fetcher without tracking.

**Methods**:

##### `fetch_daily_data(symbol: str, start_date: date, end_date: date) -> Tuple[bool, Optional[pd.DataFrame]]`

**Purpose**: Fetch daily stock data from SSI API.

**Parameters**:
- `symbol` (str): Stock symbol
- `start_date` (date): Start date
- `end_date` (date): End date

**Returns**:
- `success` (bool): Whether the operation succeeded
- `df` (pd.DataFrame, optional): Stock data DataFrame

**Example**:
```python
from fastapi.func.ssi_fetcher import SSIFetcher
from datetime import date

fetcher = SSIFetcher()
success, df = await fetcher.fetch_daily_data(
    'PDR', 
    date(2024, 1, 1), 
    date(2024, 12, 31)
)

if success and df is not None:
    print(f"Fetched {len(df)} records")
```

### `ssi_playwright_probe.py`

#### `main() -> None`

**Purpose**: Interactive tool to capture SSI API headers and cookies using Playwright.

**Usage**:
```bash
python fastapi/func/ssi_playwright_probe.py
```

**Features**:
- Opens SSI website in browser
- Records network requests and responses
- Saves HAR file for analysis
- Captures headers and cookies for API access

**Output**: HAR file saved to `assets/logs/ssi_YYYYMMDD_HHMMSS.har`

## Data Processing

### `normalize_foreign_data.py`

#### `normalize_foreign_data_to_shares(csv_path: str, output_json_path: str) -> None`

**Purpose**: Normalize foreign trading data from values (VND) to shares.

**Parameters**:
- `csv_path` (str): Path to input CSV file
- `output_json_path` (str): Path to output JSON file

**Example**:
```python
from fastapi.func.normalize_foreign_data import normalize_foreign_data_to_shares

normalize_foreign_data_to_shares(
    csv_path='data/pdr_raw.csv',
    output_json_path='data/pdr_normalized.json'
)
```

#### `normalize_foreign_data(raw_data: pd.DataFrame, source: str = 'VCI') -> pd.DataFrame`

**Purpose**: Normalize foreign trading data from different sources.

**Parameters**:
- `raw_data` (pd.DataFrame): Raw foreign trading data
- `source` (str): Data source ('VCI', 'TCBS')

**Returns**: Normalized DataFrame with consistent column names.

**Example**:
```python
from fastapi.func.normalize_foreign_data import normalize_foreign_data

# Assuming raw_data is loaded from CSV
normalized_df = normalize_foreign_data(raw_data, source='VCI')
print(normalized_df.columns)
```

## Configuration Management

### `ssi_config.py`

#### `SSIAPIConfig` Class

**Purpose**: Configuration management for SSI API endpoints and settings.

**Attributes**:
- `version` (int): Configuration version
- `updated_at` (str, optional): Last update timestamp
- `timezone` (str): Timezone setting
- `market_close_hour_local` (int): Market close hour
- `date_format_ssi` (str): Date format for SSI API
- `rate_limit` (dict): Rate limiting settings
- `windows` (dict): Time window settings
- `pagination` (dict): Pagination settings
- `base_urls` (dict): Base URLs for different services
- `endpoints` (dict): API endpoints
- `primary_sources` (dict): Primary data sources
- `headers` (dict): HTTP headers

**Methods**:

##### `load(path: Optional[Path] = None) -> SSIAPIConfig`

**Purpose**: Load configuration from JSON file.

**Parameters**:
- `path` (Path, optional): Path to config file, defaults to `assets/config/ssi_api_config.json`

**Returns**: SSIAPIConfig instance.

**Example**:
```python
from fastapi.func.ssi_config import SSIAPIConfig

config = SSIAPIConfig.load()
print(f"SSI API Version: {config.version}")
print(f"Base URLs: {config.base_urls}")
```

##### `dump(path: Optional[Path] = None) -> None`

**Purpose**: Save configuration to JSON file.

**Parameters**:
- `path` (Path, optional): Path to save config file

**Example**:
```python
from fastapi.func.ssi_config import SSIAPIConfig

config = SSIAPIConfig.load()
config.version = 2
config.dump()  # Save updated config
```

#### `get_endpoint_url(cfg: SSIAPIConfig, key: str) -> str`

**Purpose**: Get full URL for a specific endpoint.

**Parameters**:
- `cfg` (SSIAPIConfig): Configuration instance
- `key` (str): Endpoint key ('stock_info', 'dchart_history')

**Returns**: Full URL string.

**Example**:
```python
from fastapi.func.ssi_config import SSIAPIConfig, get_endpoint_url

config = SSIAPIConfig.load()
stock_info_url = get_endpoint_url(config, 'stock_info')
print(f"Stock info URL: {stock_info_url}")
```

## Database Integration

### Database Connection

All functions that interact with the database use the centralized database manager:

```python
from database.api.database import get_database_manager, get_async_session

# Initialize database
db_manager = get_database_manager()
db_manager.initialize()

# Use async session
async with get_async_session() as session:
    # Database operations
    pass
```

### Repository Pattern

Functions use the repository pattern for database operations:

```python
from database.api.repositories import RepositoryFactory

# Create repository instances
stock_repo = RepositoryFactory.create_stock_repository(session)
vn100_repo = RepositoryFactory.create_vn100_current_repository(session)
```

## Utility Functions

### Date and Time Utilities

#### `_fmt_ddmmyyyy(d: str | date) -> str`

**Purpose**: Format date to DD/MM/YYYY format for SSI API.

**Parameters**:
- `d` (str | date): Date to format

**Returns**: Formatted date string.

#### `_to_unix_timestamp(d: str | date) -> int`

**Purpose**: Convert date to Unix timestamp.

**Parameters**:
- `d` (str | date): Date to convert

**Returns**: Unix timestamp.

### Header Management

#### `_merge_headers(base: Dict[str, str], override: Dict[str, str]) -> Dict[str, str]`

**Purpose**: Merge HTTP headers with override priority.

**Parameters**:
- `base` (dict): Base headers
- `override` (dict): Override headers

**Returns**: Merged headers dictionary.

## Examples

### Complete VN100 Data Fetching

```python
import asyncio
from fastapi.func.vn100_database_loader import VN100DatabaseLoader
from fastapi.func.ssi_fetcher_with_tracking import SSIFetcherWithTracking
from datetime import date

async def fetch_vn100_data():
    # Load VN100 symbols
    loader = VN100DatabaseLoader()
    symbols = await loader.get_active_vn100_symbols()
    
    # Initialize fetcher
    fetcher = SSIFetcherWithTracking()
    
    results = {}
    for symbol in symbols[:5]:  # Process first 5 symbols
        print(f"Fetching {symbol}...")
        success, df, last_date = await fetcher.fetch_daily_with_tracking(
            symbol, date.today()
        )
        
        if success and df is not None:
            results[symbol] = {
                'data': df,
                'last_date': last_date,
                'records': len(df)
            }
            print(f"✅ {symbol}: {len(df)} records")
        else:
            print(f"❌ {symbol}: Failed")
    
    return results

# Run the example
results = asyncio.run(fetch_vn100_data())
print(f"Successfully fetched {len(results)} symbols")
```

### Batch Processing with Error Handling

```python
import asyncio
from fastapi.func.stock_data_fetcher import fetch_stock_data
from fastapi.func.vn100_fetcher import get_vn100_symbols

def fetch_multiple_symbols(symbols, start_date, end_date):
    results = {}
    errors = {}
    
    for symbol in symbols:
        try:
            print(f"Fetching {symbol}...")
            success, df, metadata = fetch_stock_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                source='VCI',
                include_foreign=True,
                print_stats=False
            )
            
            if success:
                results[symbol] = {
                    'data': df,
                    'metadata': metadata
                }
                print(f"✅ {symbol}: {len(df)} records")
            else:
                errors[symbol] = "Fetch failed"
                print(f"❌ {symbol}: Fetch failed")
                
        except Exception as e:
            errors[symbol] = str(e)
            print(f"❌ {symbol}: {str(e)}")
    
    return results, errors

# Example usage
vn100_symbols = get_vn100_symbols()
top_10 = vn100_symbols[:10]

results, errors = fetch_multiple_symbols(
    symbols=top_10,
    start_date='2024-01-01',
    end_date='2024-12-31'
)

print(f"Success: {len(results)} symbols")
print(f"Errors: {len(errors)} symbols")
```

### Configuration Management

```python
from fastapi.func.ssi_config import SSIAPIConfig, get_endpoint_url

# Load configuration
config = SSIAPIConfig.load()
print(f"Configuration version: {config.version}")
print(f"Market close hour: {config.market_close_hour_local}")

# Get endpoint URLs
stock_info_url = get_endpoint_url(config, 'stock_info')
dchart_url = get_endpoint_url(config, 'dchart_history')

print(f"Stock info endpoint: {stock_info_url}")
print(f"Chart endpoint: {dchart_url}")

# Update configuration
config.version = 2
config.updated_at = "2024-01-01T00:00:00Z"
config.dump()  # Save to file
```

## Error Handling

### Common Error Types

1. **Network Errors**: Connection timeouts, API rate limits
2. **Data Errors**: Invalid symbols, missing data
3. **Configuration Errors**: Missing config files, invalid settings
4. **Database Errors**: Connection failures, constraint violations

### Error Handling Patterns

```python
import logging
from typing import Optional

async def safe_fetch(symbol: str, max_retries: int = 3) -> Optional[pd.DataFrame]:
    """Fetch data with retry mechanism and error handling."""
    
    for attempt in range(max_retries):
        try:
            from fastapi.func.ssi_fetcher_with_tracking import SSIFetcherWithTracking
            from datetime import date
            
            fetcher = SSIFetcherWithTracking()
            success, df, last_date = await fetcher.fetch_daily_with_tracking(
                symbol, date.today()
            )
            
            if success and df is not None:
                return df
            else:
                logging.warning(f"Attempt {attempt + 1} failed for {symbol}")
                
        except Exception as e:
            logging.error(f"Attempt {attempt + 1} error for {symbol}: {str(e)}")
            
        if attempt < max_retries - 1:
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    logging.error(f"All attempts failed for {symbol}")
    return None

# Usage
df = await safe_fetch('PDR')
if df is not None:
    print(f"Successfully fetched {len(df)} records")
else:
    print("Failed to fetch data after all retries")
```

### Logging Configuration

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stockai.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Use in functions
logger.info(f"Starting data fetch for {symbol}")
logger.error(f"Failed to fetch data: {error_message}")
```

## Performance Tips

1. **Use async/await** for I/O operations
2. **Batch processing** for multiple symbols
3. **Connection pooling** for database operations
4. **Caching** for frequently accessed data
5. **Rate limiting** to avoid API blocks
6. **Error handling** with retry mechanisms

## Dependencies

Required packages:
- `pandas`: Data manipulation
- `httpx`: HTTP client for API calls
- `playwright`: Browser automation for SSI
- `asyncio`: Asynchronous programming
- `sqlalchemy`: Database ORM
- `asyncpg`: PostgreSQL async driver

Install with:
```bash
pip install pandas httpx playwright sqlalchemy asyncpg
```

---

**StockAI Team** - Comprehensive stock data processing and analysis tools
