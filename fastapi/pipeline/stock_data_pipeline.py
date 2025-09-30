#!/usr/bin/env python3
"""
StockAI Data Pipeline
Pipeline để lấy dữ liệu giao dịch chứng khoán và lưu vào database

Pipeline này sẽ:
1. Lấy danh sách VN100
2. Lấy dữ liệu giao dịch cho từng mã
3. Lưu vào database với TimescaleDB
4. Xử lý lỗi và retry logic
5. Logging và monitoring

Author: StockAI Team
Version: 1.0.0
"""

import asyncio
import logging
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi.func.stock_data_fetcher import StockDataFetcher
from fastapi.func.vn100_fetcher import VN100Fetcher
from database.api.database import get_async_session, get_database_manager
from database.api.repositories import RepositoryFactory
from database.schema import DataSource
from .upsert_manager import UpsertManager, ensure_stock_exists
from .ssi_verifier import verify_with_ssi

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StockDataPipeline:
    """Pipeline để lấy và lưu dữ liệu chứng khoán"""
    
    def __init__(self, source: str = "VCI"):
        """
        Khởi tạo pipeline
        
        Args:
            source (str): Nguồn dữ liệu ('VCI', 'TCBS', etc.)
        """
        self.source = source
        self.stock_fetcher = StockDataFetcher(source=source)
        self.vn100_fetcher = VN100Fetcher()
        self.processed_count = 0
        self.error_count = 0
        self.start_time = None
        
    async def run_pipeline(
        self,
        symbols: Optional[List[str]] = None,
        start_date: str = "2010-01-01",
        end_date: Optional[str] = None,
        max_retries: int = 3,
        batch_size: int = 10
    ) -> Dict[str, Any]:
        """
        Chạy pipeline để lấy và lưu dữ liệu
        
        Args:
            symbols: Danh sách mã cần lấy (None = lấy tất cả VN100)
            start_date: Ngày bắt đầu
            end_date: Ngày kết thúc (None = hôm nay)
            max_retries: Số lần retry tối đa
            batch_size: Số mã xử lý đồng thời
            
        Returns:
            Dict với thống kê kết quả
        """
        self.start_time = datetime.now()
        logger.info(f"🚀 Bắt đầu pipeline với source: {self.source}")
        
        try:
            # Lấy danh sách mã cần xử lý
            if symbols is None:
                # Lấy tất cả VN100 từ database
                from ..func.vn100_database_loader import get_active_vn100_symbols_from_db
                symbols = await get_active_vn100_symbols_from_db()
                logger.info(f"📊 Loaded {len(symbols)} VN100 symbols from database")
            else:
                logger.info(f"📊 Xử lý {len(symbols)} mã được chỉ định")
            
            # Ensure DB is initialized once per run
            get_database_manager().initialize()
            results = []
            # One shared session for the entire run
            async with get_async_session() as session:
                for i in range(0, len(symbols), batch_size):
                    batch = symbols[i:i + batch_size]
                    logger.info(f"🔄 Xử lý batch {i//batch_size + 1}: {batch}")
                    batch_results = await self._process_batch(
                        batch, start_date, end_date, max_retries, session
                    )
                    results.extend(batch_results)
                    if i + batch_size < len(symbols):
                        await asyncio.sleep(2)
            
            # Tổng kết
            end_time = datetime.now()
            duration = end_time - self.start_time
            
            summary = {
                'total_symbols': len(symbols),
                'processed_count': self.processed_count,
                'error_count': self.error_count,
                'success_rate': (self.processed_count / len(symbols)) * 100 if symbols else 0,
                'duration_seconds': duration.total_seconds(),
                'start_time': self.start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'results': results
            }
            
            logger.info(f"✅ Pipeline hoàn thành: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"❌ Pipeline thất bại: {str(e)}")
            raise
    
    async def _process_batch(
        self,
        symbols: List[str],
        start_date: str,
        end_date: Optional[str],
        max_retries: int,
        session
    ) -> List[Dict[str, Any]]:
        """Xử lý một batch mã chứng khoán"""
        tasks = []
        for symbol in symbols:
            task = self._process_symbol(symbol, start_date, end_date, max_retries, session)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Xử lý kết quả
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"❌ Lỗi xử lý {symbols[i]}: {str(result)}")
                processed_results.append({
                    'symbol': symbols[i],
                    'success': False,
                    'error': str(result)
                })
                self.error_count += 1
            else:
                processed_results.append(result)
                if result['success']:
                    self.processed_count += 1
                else:
                    self.error_count += 1
        
        return processed_results
    
    async def _process_symbol(
        self,
        symbol: str,
        start_date: str,
        end_date: Optional[str],
        max_retries: int,
        session
    ) -> Dict[str, Any]:
        """
        Xử lý một mã chứng khoán
        
        Args:
            symbol: Mã chứng khoán
            start_date: Ngày bắt đầu
            end_date: Ngày kết thúc
            max_retries: Số lần retry
            
        Returns:
            Dict với kết quả xử lý
        """
        logger.info(f"📈 Xử lý {symbol} từ {start_date} đến {end_date or 'hôm nay'}")
        
        for attempt in range(max_retries):
            try:
                # Prefetch check to avoid unnecessary API calls
                from database.api.repositories import RepositoryFactory
                price_repo = RepositoryFactory.create_stock_price_repository(session)
                latest = await price_repo.get_latest_price(symbol)
                effective_start = start_date
                if latest and latest.time:
                    try:
                        latest_date_str = latest.time.date().isoformat()
                        # move next day
                        from datetime import datetime as _dt, timedelta as _td
                        next_day = (_dt.fromisoformat(latest_date_str) + _td(days=1)).date().isoformat()
                        effective_start = max(start_date, next_day)
                    except Exception:
                        effective_start = start_date
                if end_date is None:
                    end_date_effective = date.today().isoformat()
                else:
                    end_date_effective = end_date
                if effective_start > end_date_effective:
                    logger.info(f"⏭️ Skip {symbol}: database up to date until {latest.time if latest else 'N/A'}")
                    return {
                        'symbol': symbol,
                        'success': True,
                        'records_count': 0,
                        'skipped': True,
                        'reason': 'up_to_date'
                    }

                # Lấy dữ liệu
                success, df, metadata = self.stock_fetcher.fetch_stock_data(
                    symbol=symbol,
                    start_date=effective_start,
                    end_date=end_date_effective,
                    include_foreign=True,
                    output_dir=None  # Không lưu file
                )
                
                if not success or df is None or df.empty:
                    logger.warning(f"⚠️ Không có dữ liệu cho {symbol}")
                    return {
                        'symbol': symbol,
                        'success': False,
                        'error': 'No data available',
                        'attempt': attempt + 1
                    }
                
                # Lưu vào database với shared session
                await self._save_to_database(symbol, df, metadata, session)

                # Verify with SSI API (best-effort)
                ssi_verify = None
                try:
                    to_date_effective = end_date_effective
                    # reduce verification window to last 30 days to avoid large payloads
                    try:
                        from datetime import datetime as _dt, timedelta as _td
                        ed = _dt.fromisoformat(to_date_effective)
                        fd = max(_dt.fromisoformat(effective_start), ed - _td(days=30))
                        ver_from = fd.date().isoformat()
                    except Exception:
                        ver_from = effective_start
                    ssi_verify = await verify_with_ssi(symbol, ver_from, to_date_effective)
                    logger.info(
                        f"🧪 SSI verify {symbol}: ok={ssi_verify['ok']} items={ssi_verify['items']} status={ssi_verify['status_code']}"
                    )
                except Exception as _e:
                    logger.warning(f"⚠️ SSI verify skipped for {symbol}: {_e}")
                
                logger.info(f"✅ Hoàn thành {symbol}: {len(df)} records")
                return {
                    'symbol': symbol,
                    'success': True,
                    'records_count': len(df),
                    'date_range': {
                        'start': str(df['time'].min()),
                        'end': str(df['time'].max())
                    },
                    'metadata': metadata,
                    'attempt': attempt + 1,
                    'ssi_verify': ssi_verify
                }
                
            except Exception as e:
                logger.warning(f"⚠️ Lỗi lần {attempt + 1} cho {symbol}: {str(e)}")
                if attempt == max_retries - 1:
                    logger.error(f"❌ Thất bại hoàn toàn {symbol} sau {max_retries} lần thử")
                    return {
                        'symbol': symbol,
                        'success': False,
                        'error': str(e),
                        'attempt': attempt + 1
                    }
                
                # Nghỉ trước khi retry
                await asyncio.sleep(2 ** attempt)
        
        return {
            'symbol': symbol,
            'success': False,
            'error': 'Max retries exceeded',
            'attempt': max_retries
        }
    
    def _validate_and_clean_ohlcv_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate và làm sạch dữ liệu OHLCV để tránh constraint violations
        
        Args:
            df: DataFrame với dữ liệu OHLCV
            
        Returns:
            DataFrame đã được làm sạch
        """
        logger.info(f"🧹 Validating và cleaning OHLCV data...")
        
        original_count = len(df)
        cleaned_df = df.copy()
        
        # 1. Fix close = 0 cases (thay bằng open price)
        zero_close_mask = cleaned_df['close'] <= 0
        if zero_close_mask.any():
            logger.warning(f"⚠️ Found {zero_close_mask.sum()} records with close <= 0, fixing...")
            cleaned_df.loc[zero_close_mask, 'close'] = cleaned_df.loc[zero_close_mask, 'open']
        
        # 2. Fix low > close cases (đặt low = close)
        low_gt_close_mask = cleaned_df['low'] > cleaned_df['close']
        if low_gt_close_mask.any():
            logger.warning(f"⚠️ Found {low_gt_close_mask.sum()} records with low > close, fixing...")
            cleaned_df.loc[low_gt_close_mask, 'low'] = cleaned_df.loc[low_gt_close_mask, 'close']
        
        # 3. Fix high < close cases (đặt high = close)
        high_lt_close_mask = cleaned_df['high'] < cleaned_df['close']
        if high_lt_close_mask.any():
            logger.warning(f"⚠️ Found {high_lt_close_mask.sum()} records with high < close, fixing...")
            cleaned_df.loc[high_lt_close_mask, 'high'] = cleaned_df.loc[high_lt_close_mask, 'close']
        
        # 4. Fix low > open cases (đặt low = open)
        low_gt_open_mask = cleaned_df['low'] > cleaned_df['open']
        if low_gt_open_mask.any():
            logger.warning(f"⚠️ Found {low_gt_open_mask.sum()} records with low > open, fixing...")
            cleaned_df.loc[low_gt_open_mask, 'low'] = cleaned_df.loc[low_gt_open_mask, 'open']
        
        # 5. Fix high < open cases (đặt high = open)
        high_lt_open_mask = cleaned_df['high'] < cleaned_df['open']
        if high_lt_open_mask.any():
            logger.warning(f"⚠️ Found {high_lt_open_mask.sum()} records with high < open, fixing...")
            cleaned_df.loc[high_lt_open_mask, 'high'] = cleaned_df.loc[high_lt_open_mask, 'open']
        
        # 6. Ensure high >= low (đặt high = max(high, low))
        high_lt_low_mask = cleaned_df['high'] < cleaned_df['low']
        if high_lt_low_mask.any():
            logger.warning(f"⚠️ Found {high_lt_low_mask.sum()} records with high < low, fixing...")
            cleaned_df.loc[high_lt_low_mask, 'high'] = cleaned_df.loc[high_lt_low_mask, 'low']
        
        # 7. Final validation - remove any remaining invalid records
        invalid_mask = (
            (cleaned_df['close'] <= 0) |
            (cleaned_df['low'] > cleaned_df['close']) |
            (cleaned_df['high'] < cleaned_df['close']) |
            (cleaned_df['low'] > cleaned_df['open']) |
            (cleaned_df['high'] < cleaned_df['open']) |
            (cleaned_df['high'] < cleaned_df['low'])
        )
        
        if invalid_mask.any():
            logger.warning(f"⚠️ Removing {invalid_mask.sum()} records that still have invalid data...")
            cleaned_df = cleaned_df[~invalid_mask]
        
        final_count = len(cleaned_df)
        if final_count < original_count:
            logger.warning(f"⚠️ Data cleaning removed {original_count - final_count} invalid records")
        
        logger.info(f"✅ Data validation completed: {final_count}/{original_count} records kept")
        return cleaned_df

    async def _save_to_database(
        self,
        symbol: str,
        df: pd.DataFrame,
        metadata: Dict[str, Any],
        session
    ) -> None:
        """
        Lưu dữ liệu vào database
        
        Args:
            symbol: Mã chứng khoán
            df: DataFrame với dữ liệu
            metadata: Metadata từ fetcher
        """
        # Validate và clean data trước khi lưu
        cleaned_df = self._validate_and_clean_ohlcv_data(df)
        
        try:
            # Lấy thông tin stock
            stock_repo = RepositoryFactory.create_stock_repository(session)
            stock = await stock_repo.get_by_symbol(symbol)
            if not stock:
                from .upsert_manager import ensure_stock_exists
                created = await ensure_stock_exists(session, symbol, metadata.get('company_name', None), metadata.get('exchange', 'HOSE'))
                if not created:
                    logger.warning(f"⚠️ Không thể tạo stock {symbol} trong database")
                    return
                stock = await stock_repo.get_by_symbol(symbol)
            
            # Chuẩn bị dữ liệu price
            price_repo = RepositoryFactory.create_stock_price_repository(session)
            prices_data = []
            
            for _, row in cleaned_df.iterrows():
                close_price = float(row['close'])
                volume = int(row['volume'])
                
                price_data = {
                    'stock_id': stock.id,
                    'symbol': symbol.upper(),
                    'time': row['time'],
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': close_price,
                    'volume': volume,
                    'value': close_price * volume,  # Tính toán value
                    'source': DataSource.VCI if self.source == 'VCI' else DataSource.TCBS
                }
                prices_data.append(price_data)
            
            # Sử dụng upsert để tránh duplicate
            upsert_manager = UpsertManager(session)
            
            # Chuẩn bị dữ liệu price không có stock_id (sẽ được thêm trong upsert_manager)
            upsert_prices_data = []
            for price_data in prices_data:
                upsert_price_data = {k: v for k, v in price_data.items() if k != 'stock_id'}
                upsert_prices_data.append(upsert_price_data)
            
            # Upsert prices
            if upsert_prices_data:
                price_inserted, price_updated, price_failed = await upsert_manager.upsert_stock_prices_batch(
                    upsert_prices_data, self.source
                )
                logger.info(f"💾 Upsert prices cho {symbol}: {price_inserted} inserted, {price_updated} updated, {len(price_failed)} failed")
            
            # Chuẩn bị dữ liệu foreign trade
            foreign_repo = RepositoryFactory.create_foreign_trade_repository(session)
            foreign_data = []
            
            for _, row in cleaned_df.iterrows():
                # Kiểm tra xem có dữ liệu foreign trade không
                if 'foreign_buy_shares' in row and 'foreign_sell_shares' in row:
                    buy_volume = int(row['foreign_buy_shares'])
                    sell_volume = int(row['foreign_sell_shares'])
                    buy_value = float(row['foreign_buy_shares']) * float(row['close'])
                    sell_value = float(row['foreign_sell_shares']) * float(row['close'])
                    
                    foreign_trade_data = {
                        'symbol': symbol.upper(),
                        'time': row['time'],
                        'buy_volume': buy_volume,
                        'sell_volume': sell_volume,
                        'net_volume': buy_volume - sell_volume,  # Tính toán net_volume
                        'buy_value': buy_value,
                        'sell_value': sell_value,
                        'net_value': buy_value - sell_value,  # Tính toán net_value
                        'source': DataSource.VCI if self.source == 'VCI' else DataSource.TCBS
                    }
                    foreign_data.append(foreign_trade_data)
            
            # Upsert foreign trades
            if foreign_data:
                trade_inserted, trade_updated, trade_failed = await upsert_manager.upsert_foreign_trades_batch(
                    foreign_data, self.source
                )
                logger.info(f"🌍 Upsert foreign trades cho {symbol}: {trade_inserted} inserted, {trade_updated} updated, {len(trade_failed)} failed")
            
            logger.info(f"✅ Hoàn thành lưu dữ liệu {symbol} vào database")
            
        except Exception as e:
            logger.error(f"❌ Lỗi lưu dữ liệu {symbol}: {str(e)}")
            raise

    async def get_pipeline_status(self) -> Dict[str, Any]:
        """Lấy trạng thái pipeline"""
        if self.start_time is None:
            return {'status': 'not_started'}
        
        current_time = datetime.now()
        duration = current_time - self.start_time
        
        return {
            'status': 'running',
            'start_time': self.start_time.isoformat(),
            'current_time': current_time.isoformat(),
            'duration_seconds': duration.total_seconds(),
            'processed_count': self.processed_count,
            'error_count': self.error_count
        }

# Utility functions
async def run_single_symbol_pipeline(
    symbol: str,
    start_date: str = "2010-01-01",
    end_date: Optional[str] = None,
    source: str = "VCI"
) -> Dict[str, Any]:
    """
    Chạy pipeline cho một mã duy nhất
    
    Args:
        symbol: Mã chứng khoán
        start_date: Ngày bắt đầu
        end_date: Ngày kết thúc
        source: Nguồn dữ liệu
        
    Returns:
        Dict với kết quả
    """
    pipeline = StockDataPipeline(source=source)
    return await pipeline.run_pipeline(
        symbols=[symbol],
        start_date=start_date,
        end_date=end_date
    )

async def run_vn100_pipeline(
    start_date: str = "2010-01-01",
    end_date: Optional[str] = None,
    source: str = "VCI",
    batch_size: int = 10
) -> Dict[str, Any]:
    """
    Chạy pipeline cho tất cả VN100
    
    Args:
        start_date: Ngày bắt đầu
        end_date: Ngày kết thúc
        source: Nguồn dữ liệu
        batch_size: Kích thước batch
        
    Returns:
        Dict với kết quả
    """
    pipeline = StockDataPipeline(source=source)
    return await pipeline.run_pipeline(
        symbols=None,  # Lấy tất cả VN100
        start_date=start_date,
        end_date=end_date,
        batch_size=batch_size
    )

# Export main classes and functions
__all__ = [
    'StockDataPipeline',
    'run_single_symbol_pipeline',
    'run_vn100_pipeline'
]
