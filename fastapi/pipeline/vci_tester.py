"""
VCI Data Tester

Module để test khả năng lấy dữ liệu từ VCI cho các mã chứng khoán
để đảm bảo có thể fetch được dữ liệu lịch sử trước khi thêm vào VN100.
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import pandas as pd

# Import existing VCI functionality
from fastapi.func.stock_data_fetcher import StockDataFetcher

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class VCITestResult:
    """Kết quả test VCI cho một mã"""
    symbol: str
    success: bool
    data_points: int = 0
    date_range: Optional[Tuple[date, date]] = None
    error_message: Optional[str] = None
    test_duration: float = 0.0
    has_foreign_data: bool = False
    avg_volume: Optional[float] = None
    avg_price: Optional[float] = None

class VCITester:
    """
    VCI Data Tester
    
    Test khả năng lấy dữ liệu từ VCI cho các mã chứng khoán:
    - Kiểm tra có thể fetch được dữ liệu không
    - Đo chất lượng dữ liệu (số điểm, khoảng thời gian)
    - Kiểm tra dữ liệu foreign trading
    - Đánh giá độ tin cậy của mã
    """
    
    def __init__(self):
        self.fetcher = StockDataFetcher()
        self.test_results: Dict[str, VCITestResult] = {}
        
    async def test_symbol(self, symbol: str, test_days: int = 30) -> VCITestResult:
        """
        Test một mã chứng khoán với VCI
        
        Args:
            symbol: Symbol to test
            test_days: Number of days to test (default 30)
            
        Returns:
            VCITestResult object
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"🧪 Testing VCI data for {symbol}...")
            
            # Calculate test date range
            end_date = date.today()
            start_date = end_date - timedelta(days=test_days)
            
            # Test with VCI
            success, df, metadata = self.fetcher.fetch_stock_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                source='VCI'
            )
            
            test_duration = (datetime.now() - start_time).total_seconds()
            
            if success and df is not None and not df.empty:
                # Analyze data quality
                data_points = len(df)
                actual_start = df['time'].min().date() if 'time' in df.columns else None
                actual_end = df['time'].max().date() if 'time' in df.columns else None
                
                # Check for foreign data
                has_foreign_data = any(col in df.columns for col in [
                    'foreign_buy_shares', 'foreign_sell_shares', 
                    'foreign_buy_value', 'foreign_sell_value'
                ])
                
                # Calculate averages
                avg_volume = df['volume'].mean() if 'volume' in df.columns else None
                avg_price = df['close'].mean() if 'close' in df.columns else None
                
                result = VCITestResult(
                    symbol=symbol,
                    success=True,
                    data_points=data_points,
                    date_range=(actual_start, actual_end) if actual_start and actual_end else None,
                    test_duration=test_duration,
                    has_foreign_data=has_foreign_data,
                    avg_volume=avg_volume,
                    avg_price=avg_price
                )
                
                logger.info(f"✅ {symbol}: {data_points} data points, {test_duration:.2f}s")
                
            else:
                error_msg = "No data returned from VCI"
                if metadata and 'error' in metadata:
                    error_msg = metadata['error']
                
                result = VCITestResult(
                    symbol=symbol,
                    success=False,
                    error_message=error_msg,
                    test_duration=test_duration
                )
                
                logger.warning(f"⚠️ {symbol}: {error_msg}")
            
            # Cache result
            self.test_results[symbol] = result
            return result
            
        except Exception as e:
            test_duration = (datetime.now() - start_time).total_seconds()
            error_msg = f"Exception: {str(e)}"
            
            result = VCITestResult(
                symbol=symbol,
                success=False,
                error_message=error_msg,
                test_duration=test_duration
            )
            
            logger.error(f"❌ {symbol}: {error_msg}")
            self.test_results[symbol] = result
            return result
    
    async def test_symbols_batch(self, symbols: List[str], test_days: int = 30, batch_size: int = 5) -> Dict[str, VCITestResult]:
        """
        Test multiple symbols với batch processing
        
        Args:
            symbols: List of symbols to test
            test_days: Number of days to test for each symbol
            batch_size: Number of symbols to process concurrently
            
        Returns:
            Dict mapping symbol to VCITestResult
        """
        logger.info(f"🧪 Starting batch VCI testing of {len(symbols)} symbols...")
        
        results = {}
        
        # Process in batches to avoid rate limiting
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            logger.info(f"📦 Testing batch {i//batch_size + 1}: {batch}")
            
            # Create tasks for concurrent processing
            tasks = [self.test_symbol(symbol, test_days) for symbol in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for symbol, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"❌ Exception testing {symbol}: {str(result)}")
                    results[symbol] = VCITestResult(
                        symbol=symbol,
                        success=False,
                        error_message=f"Exception: {str(result)}"
                    )
                else:
                    results[symbol] = result
            
            # Add delay between batches to respect rate limits
            if i + batch_size < len(symbols):
                logger.info("⏳ Waiting 10s between batches...")
                await asyncio.sleep(10)
        
        # Count results
        success_count = sum(1 for result in results.values() if result.success)
        logger.info(f"✅ Batch VCI testing completed: {success_count}/{len(symbols)} symbols successful")
        
        return results
    
    def get_test_summary(self, results: Dict[str, VCITestResult]) -> Dict[str, any]:
        """
        Tạo summary của kết quả test
        
        Args:
            results: Results from test_symbols_batch
            
        Returns:
            Summary dictionary
        """
        total_symbols = len(results)
        successful_symbols = sum(1 for result in results.values() if result.success)
        failed_symbols = total_symbols - successful_symbols
        
        successful_list = []
        failed_list = []
        
        total_data_points = 0
        total_test_time = 0
        symbols_with_foreign_data = 0
        
        for symbol, result in results.items():
            if result.success:
                successful_list.append({
                    'symbol': symbol,
                    'data_points': result.data_points,
                    'date_range': result.date_range,
                    'has_foreign_data': result.has_foreign_data,
                    'avg_volume': result.avg_volume,
                    'avg_price': result.avg_price,
                    'test_duration': result.test_duration
                })
                
                total_data_points += result.data_points
                total_test_time += result.test_duration
                if result.has_foreign_data:
                    symbols_with_foreign_data += 1
            else:
                failed_list.append({
                    'symbol': symbol,
                    'error': result.error_message,
                    'test_duration': result.test_duration
                })
        
        avg_data_points = total_data_points / successful_symbols if successful_symbols > 0 else 0
        avg_test_time = total_test_time / total_symbols if total_symbols > 0 else 0
        
        return {
            'total_symbols': total_symbols,
            'successful_symbols': successful_symbols,
            'failed_symbols': failed_symbols,
            'success_rate': successful_symbols / total_symbols if total_symbols > 0 else 0,
            'symbols_with_foreign_data': symbols_with_foreign_data,
            'foreign_data_rate': symbols_with_foreign_data / successful_symbols if successful_symbols > 0 else 0,
            'avg_data_points': avg_data_points,
            'avg_test_time': avg_test_time,
            'successful_list': successful_list,
            'failed_list': failed_list,
            'timestamp': datetime.now()
        }
    
    def filter_reliable_symbols(self, results: Dict[str, VCITestResult], 
                               min_data_points: int = 20,
                               min_avg_volume: float = 1000) -> List[str]:
        """
        Filter symbols dựa trên độ tin cậy
        
        Args:
            results: Test results
            min_data_points: Minimum data points required
            min_avg_volume: Minimum average volume required
            
        Returns:
            List of reliable symbols
        """
        reliable_symbols = []
        
        for symbol, result in results.items():
            if not result.success:
                continue
                
            # Check data quality criteria
            if result.data_points < min_data_points:
                logger.debug(f"❌ {symbol}: Insufficient data points ({result.data_points} < {min_data_points})")
                continue
                
            if result.avg_volume and result.avg_volume < min_avg_volume:
                logger.debug(f"❌ {symbol}: Low average volume ({result.avg_volume:.0f} < {min_avg_volume})")
                continue
            
            reliable_symbols.append(symbol)
            logger.debug(f"✅ {symbol}: Reliable (points: {result.data_points}, volume: {result.avg_volume:.0f})")
        
        logger.info(f"🎯 Filtered {len(reliable_symbols)}/{len(results)} symbols as reliable")
        return reliable_symbols

async def test_vci_symbols(symbols: List[str], test_days: int = 30) -> Dict[str, any]:
    """
    Convenience function để test symbols với VCI
    
    Args:
        symbols: List of symbols to test
        test_days: Number of days to test
        
    Returns:
        Test summary
    """
    try:
        tester = VCITester()
        results = await tester.test_symbols_batch(symbols, test_days)
        summary = tester.get_test_summary(results)
        return summary
        
    except Exception as e:
        logger.error(f"❌ Error in test_vci_symbols: {str(e)}")
        return {
            'total_symbols': len(symbols),
            'successful_symbols': 0,
            'failed_symbols': len(symbols),
            'success_rate': 0,
            'symbols_with_foreign_data': 0,
            'foreign_data_rate': 0,
            'avg_data_points': 0,
            'avg_test_time': 0,
            'successful_list': [],
            'failed_list': [{'symbol': s, 'error': f'Error: {str(e)}'} for s in symbols],
            'timestamp': datetime.now()
        }

if __name__ == "__main__":
    async def main():
        """Test function"""
        test_symbols = ['VCB', 'BID', 'CTG', 'TCB', 'MBB', 'ACB', 'HDB', 'TPB', 'STB', 'EIB']
        
        print(f"\n{'='*50}")
        print(f"VCI Data Testing")
        print(f"{'='*50}")
        
        summary = await test_vci_symbols(test_symbols, test_days=7)  # Test with 7 days
        
        print(f"\n📊 VCI Test Summary:")
        print(f"  Total symbols: {summary['total_symbols']}")
        print(f"  Successful symbols: {summary['successful_symbols']}")
        print(f"  Failed symbols: {summary['failed_symbols']}")
        print(f"  Success rate: {summary['success_rate']:.1%}")
        print(f"  Symbols with foreign data: {summary['symbols_with_foreign_data']}")
        print(f"  Foreign data rate: {summary['foreign_data_rate']:.1%}")
        print(f"  Average data points: {summary['avg_data_points']:.1f}")
        print(f"  Average test time: {summary['avg_test_time']:.2f}s")
        
        if summary['successful_list']:
            print(f"\n✅ Successful symbols:")
            for item in summary['successful_list'][:5]:
                print(f"  {item['symbol']}: {item['data_points']} points, "
                      f"volume: {item['avg_volume']:.0f}, "
                      f"foreign: {'Yes' if item['has_foreign_data'] else 'No'}")
        
        if summary['failed_list']:
            print(f"\n❌ Failed symbols:")
            for item in summary['failed_list'][:5]:
                print(f"  {item['symbol']}: {item['error']}")
        
        print(f"\n{'='*50}")
    
    asyncio.run(main())
