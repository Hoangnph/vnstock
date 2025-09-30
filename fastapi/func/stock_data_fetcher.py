#!/usr/bin/env python3
"""
Stock Data Fetcher - Universal function to fetch complete stock data
Hàm tổng quát để lấy dữ liệu đầy đủ của bất kỳ mã chứng khoán nào

Features:
- Fetch OHLCV data (Open, High, Low, Close, Volume)
- Fetch foreign trading data (buy/sell volumes)
- Merge and clean data
- Save to CSV and JSON formats
- Support multiple data sources (VCI, TCBS, etc.)
- Configurable date ranges
- Error handling and logging

Author: StockAI Team
Version: 1.0.0
"""

import pandas as pd
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockDataFetcher:
    """Universal stock data fetcher for Vietnamese stock market"""
    
    def __init__(self, source: str = "VCI"):
        """
        Initialize the fetcher
        
        Args:
            source (str): Data source ('VCI', 'TCBS', etc.)
        """
        self.source = source
        self.quote = None
        self.foreign_trade = None
        
    def _initialize_objects(self, symbol: str):
        """Initialize vnstock objects for the given symbol"""
        try:
            from vnstock import Quote, ForeignTrade
            self.quote = Quote(symbol=symbol, source=self.source)
            self.foreign_trade = ForeignTrade(symbol=symbol, source=self.source)
            return True
        except ImportError:
            logger.error("vnstock library not found. Please install: pip install vnstock")
            return False
        except Exception as e:
            logger.error(f"Error initializing vnstock objects: {str(e)}")
            return False
    
    def fetch_stock_data(
        self,
        symbol: str,
        start_date: str = "2010-01-01",
        end_date: Optional[str] = None,
        interval: str = "1D",
        include_foreign: bool = True,
        output_dir: Optional[str] = None
    ) -> Tuple[bool, Optional[pd.DataFrame], Dict[str, Any]]:
        """
        Fetch complete stock data for a given symbol
        
        Args:
            symbol (str): Stock symbol (e.g., 'PDR', 'VIC', 'VCB')
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str, optional): End date in YYYY-MM-DD format. Defaults to today
            interval (str): Data interval ('1D', '1H', etc.)
            include_foreign (bool): Whether to include foreign trading data
            output_dir (str, optional): Output directory. Defaults to current directory
            
        Returns:
            Tuple[bool, Optional[pd.DataFrame], Dict[str, Any]]:
                - Success status
                - DataFrame with merged data
                - Metadata dictionary
        """
        
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
            
        if output_dir is None:
            output_dir = Path.cwd()
        else:
            output_dir = Path(output_dir)
            
        metadata = {
            'symbol': symbol,
            'start_date': start_date,
            'end_date': end_date,
            'interval': interval,
            'source': self.source,
            'include_foreign': include_foreign,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            logger.info(f"🔄 Fetching data for {symbol} from {start_date} to {end_date}")
            
            # Initialize vnstock objects
            if not self._initialize_objects(symbol):
                return False, None, metadata
            
            # 1. Fetch price data
            logger.info("📈 Fetching stock price data...")
            price_data = self.quote.history(
                start=start_date,
                end=end_date,
                interval=interval,
                show_log=False
            )
            
            if price_data is None or price_data.empty:
                logger.error(f"❌ No price data found for {symbol}")
                return False, None, metadata
                
            logger.info(f"✅ Retrieved {len(price_data)} price records")
            metadata['price_records'] = len(price_data)
            
            # 2. Fetch foreign trading data (if requested)
            foreign_data = pd.DataFrame()
            if include_foreign:
                logger.info("🌍 Fetching foreign trading data...")
                try:
                    foreign_data = self.foreign_trade.daily(
                        symbol=symbol,
                        start=start_date,
                        end=end_date
                    )
                    
                    if foreign_data is not None and not foreign_data.empty:
                        logger.info(f"✅ Retrieved {len(foreign_data)} foreign trading records")
                        metadata['foreign_records'] = len(foreign_data)
                    else:
                        logger.warning("⚠️ No foreign trading data found")
                        metadata['foreign_records'] = 0
                        
                except Exception as e:
                    logger.warning(f"⚠️ Error fetching foreign data: {str(e)}")
                    metadata['foreign_records'] = 0
            
            # 3. Merge data
            logger.info("🔗 Merging data...")
            merged_df = self._merge_data(price_data, foreign_data, include_foreign)
            
            # 4. Clean and prepare final data
            logger.info("🧹 Cleaning data...")
            final_df = self._clean_data(merged_df)
            
            metadata.update({
                'final_records': len(final_df),
                'columns': list(final_df.columns),
                'date_range': {
                    'start': str(final_df['time'].min()),
                    'end': str(final_df['time'].max())
                },
                'price_stats': {
                    'high_max': float(final_df['high'].max()),
                    'low_min': float(final_df['low'].min()),
                    'volume_avg': float(final_df['volume'].mean())
                }
            })
            
            if include_foreign and not foreign_data.empty:
                metadata['foreign_stats'] = {
                    'buy_avg': float(final_df['foreign_buy_shares'].mean()),
                    'sell_avg': float(final_df['foreign_sell_shares'].mean())
                }
            
            return True, final_df, metadata
            
        except Exception as e:
            logger.error(f"❌ Error fetching data for {symbol}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, None, metadata
    
    def _merge_data(self, price_data: pd.DataFrame, foreign_data: pd.DataFrame, include_foreign: bool) -> pd.DataFrame:
        """Merge price and foreign trading data"""
        
        # Prepare price data
        price_df = price_data.copy()
        price_df['time'] = pd.to_datetime(price_df['time']).dt.date
        
        if include_foreign and not foreign_data.empty:
            # Prepare foreign data
            foreign_df = foreign_data.copy()
            foreign_df['time'] = pd.to_datetime(foreign_df['date']).dt.date
            
            # Merge on date
            merged_df = pd.merge(
                price_df, 
                foreign_df, 
                on='time', 
                how='left'
            )
            
            # Map foreign columns to expected names
            merged_df['foreign_buy_shares'] = merged_df.get('buy_vol', 0)
            merged_df['foreign_sell_shares'] = merged_df.get('sell_vol', 0)
            merged_df['foreign_net_shares'] = merged_df.get('net_vol', 0)
            
        else:
            # No foreign data, create empty columns
            merged_df = price_df.copy()
            merged_df['foreign_buy_shares'] = 0
            merged_df['foreign_sell_shares'] = 0
            merged_df['foreign_net_shares'] = 0
        
        return merged_df
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and prepare final data"""
        
        # Select and rename columns
        final_df = df[[
            'time', 'open', 'high', 'low', 'close', 'volume',
            'foreign_buy_shares', 'foreign_sell_shares', 'foreign_net_shares'
        ]].copy()
        
        # Fill NaN values
        final_df['foreign_buy_shares'] = final_df['foreign_buy_shares'].fillna(0)
        final_df['foreign_sell_shares'] = final_df['foreign_sell_shares'].fillna(0)
        final_df['foreign_net_shares'] = final_df['foreign_net_shares'].fillna(0)
        
        # Convert to proper types
        final_df['foreign_buy_shares'] = final_df['foreign_buy_shares'].astype(int)
        final_df['foreign_sell_shares'] = final_df['foreign_sell_shares'].astype(int)
        final_df['foreign_net_shares'] = final_df['foreign_net_shares'].astype(int)
        
        return final_df
    
    def save_data(
        self,
        df: pd.DataFrame,
        symbol: str,
        start_date: str,
        end_date: str,
        output_dir: Path,
        save_csv: bool = True,
        save_json: bool = True,
        web_json: bool = False
    ) -> Dict[str, str]:
        """
        Save data to files
        
        Args:
            df: DataFrame to save
            symbol: Stock symbol
            start_date: Start date
            end_date: End date
            output_dir: Output directory
            save_csv: Whether to save CSV
            save_json: Whether to save JSON
            web_json: Whether to save web-friendly JSON
            
        Returns:
            Dict[str, str]: Paths of saved files
        """
        
        saved_files = {}
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if save_csv:
            csv_path = output_dir / f"{symbol}_daily_{start_date}_to_{end_date}.csv"
            df.to_csv(csv_path, index=False)
            saved_files['csv'] = str(csv_path)
            logger.info(f"💾 Saved CSV: {csv_path}")
        
        if save_json:
            json_path = output_dir / f"{symbol}_daily_{start_date}_to_{end_date}.json"
            records = self._prepare_json_data(df)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, allow_nan=False, indent=2)
            
            saved_files['json'] = str(json_path)
            logger.info(f"💾 Saved JSON: {json_path}")
        
        if web_json:
            web_json_path = output_dir / f"{symbol}_daily_normalized.json"
            records = self._prepare_json_data(df)
            
            with open(web_json_path, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, allow_nan=False, indent=2)
            
            saved_files['web_json'] = str(web_json_path)
            logger.info(f"🌐 Saved Web JSON: {web_json_path}")
        
        return saved_files
    
    def _prepare_json_data(self, df: pd.DataFrame) -> list:
        """Prepare DataFrame for JSON serialization"""
        
        # Convert to records
        records = df.to_dict(orient='records')
        
        # Deep sanitize: replace NaN/Inf with None for JSON compatibility
        for rec in records:
            for k, v in list(rec.items()):
                if isinstance(v, float):
                    if math.isnan(v) or math.isinf(v):
                        rec[k] = None
                # Convert time to string
                if k == 'time' and v is not None:
                    rec[k] = v.strftime('%Y-%m-%d') if hasattr(v, 'strftime') else str(v)
        
        return records
    
    def print_statistics(self, df: pd.DataFrame, metadata: Dict[str, Any]):
        """Print data statistics"""
        
        symbol = metadata['symbol']
        print(f"\n📊 Statistics for {symbol}:")
        print(f"   📅 Date range: {metadata['date_range']['start']} to {metadata['date_range']['end']}")
        print(f"   📈 Total records: {metadata['final_records']}")
        print(f"   💰 Highest price: {metadata['price_stats']['high_max']:.2f}")
        print(f"   💰 Lowest price: {metadata['price_stats']['low_min']:.2f}")
        print(f"   📊 Average volume: {metadata['price_stats']['volume_avg']:,.0f}")
        
        if 'foreign_stats' in metadata:
            print(f"   🌍 Average foreign buy: {metadata['foreign_stats']['buy_avg']:,.0f}")
            print(f"   🌍 Average foreign sell: {metadata['foreign_stats']['sell_avg']:,.0f}")
        else:
            print(f"   🌍 No foreign trading data")
        
        print(f"\n📈 Sample data (first 5 records):")
        for i, (_, row) in enumerate(df.head(5).iterrows()):
            print(f"   {i+1}. {row['time']}: O={row['open']}, H={row['high']}, L={row['low']}, C={row['close']}, V={row['volume']}, FB={row['foreign_buy_shares']}, FS={row['foreign_sell_shares']}")


def fetch_stock_data(
    symbol: str,
    start_date: str = "2010-01-01",
    end_date: Optional[str] = None,
    source: str = "VCI",
    include_foreign: bool = True,
    output_dir: Optional[str] = None,
    save_csv: bool = True,
    save_json: bool = True,
    web_json: bool = False,
    print_stats: bool = True
) -> Tuple[bool, Optional[pd.DataFrame], Dict[str, Any]]:
    """
    Convenience function to fetch stock data
    
    Args:
        symbol (str): Stock symbol (e.g., 'PDR', 'VIC', 'VCB')
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str, optional): End date in YYYY-MM-DD format. Defaults to today
        source (str): Data source ('VCI', 'TCBS', etc.)
        include_foreign (bool): Whether to include foreign trading data
        output_dir (str, optional): Output directory. Defaults to current directory
        save_csv (bool): Whether to save CSV file
        save_json (bool): Whether to save JSON file
        web_json (bool): Whether to save web-friendly JSON file
        print_stats (bool): Whether to print statistics
        
    Returns:
        Tuple[bool, Optional[pd.DataFrame], Dict[str, Any]]:
            - Success status
            - DataFrame with merged data
            - Metadata dictionary
            
    Example:
        >>> success, df, metadata = fetch_stock_data('PDR', '2020-01-01', '2024-12-31')
        >>> if success:
        ...     print(f"Fetched {len(df)} records for {metadata['symbol']}")
    """
    
    fetcher = StockDataFetcher(source=source)
    
    success, df, metadata = fetcher.fetch_stock_data(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        include_foreign=include_foreign,
        output_dir=output_dir
    )
    
    if success and df is not None:
        # Save files if requested
        if save_csv or save_json or web_json:
            if output_dir is None:
                output_dir = Path.cwd()
            else:
                output_dir = Path(output_dir)
                
            saved_files = fetcher.save_data(
                df=df,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                output_dir=output_dir,
                save_csv=save_csv,
                save_json=save_json,
                web_json=web_json
            )
            
            metadata['saved_files'] = saved_files
        
        # Print statistics if requested
        if print_stats:
            fetcher.print_statistics(df, metadata)
    
    return success, df, metadata


# Example usage and testing
if __name__ == "__main__":
    # Test with PDR
    print("🚀 Testing Stock Data Fetcher with PDR...")
    
    success, df, metadata = fetch_stock_data(
        symbol='PDR',
        start_date='2020-01-01',
        end_date='2024-12-31',
        source='VCI',
        include_foreign=True,
        output_dir='./test_output',
        save_csv=True,
        save_json=True,
        web_json=True,
        print_stats=True
    )
    
    if success:
        print("\n✅ Test completed successfully!")
        print(f"📁 Files saved: {metadata.get('saved_files', {})}")
    else:
        print("\n❌ Test failed!")
