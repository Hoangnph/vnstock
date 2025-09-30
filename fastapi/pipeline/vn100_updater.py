"""
VN100 Update Logic

Module chính để cập nhật danh sách VN100 tự động với:
- Scraping từ Vietcap
- Verification với HOSE  
- Testing với VCI
- Tracking trạng thái mã (NEW, ACTIVE, INACTIVE)
- Cập nhật database với lịch sử thay đổi
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
import pandas as pd

# Import components
from fastapi.pipeline.vietcap_scraper import VietcapScraper, VN100Symbol
from fastapi.pipeline.hose_verifier import HOSEVerifier, HOSESymbolInfo
from fastapi.pipeline.vci_tester import VCITester, VCITestResult

# Import database components
from database.api.database import DatabaseManager
from database.schema.models import VN100History, VN100Current, VN100Status
from database.api.repositories import RepositoryFactory

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class VN100UpdateResult:
    """Kết quả cập nhật VN100"""
    week_start: date
    week_end: date
    total_scraped: int
    total_verified: int
    total_tested: int
    new_symbols: List[str]
    active_symbols: List[str]
    inactive_symbols: List[str]
    failed_symbols: List[str]
    update_duration: float
    success: bool
    error_message: Optional[str] = None

class VN100Updater:
    """
    VN100 Automatic Updater
    
    Hệ thống cập nhật tự động VN100 với:
    - Scraping từ Vietcap
    - Verification với HOSE
    - Testing với VCI
    - Status tracking và database updates
    """
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.scraper = None
        self.verifier = None
        self.tester = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.scraper = VietcapScraper()
        self.verifier = HOSEVerifier()
        self.tester = VCITester()
        
        await self.scraper.__aenter__()
        await self.verifier.__aenter__()
        
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.scraper:
            await self.scraper.__aexit__(exc_type, exc_val, exc_tb)
        if self.verifier:
            await self.verifier.__aexit__(exc_type, exc_val, exc_tb)
    
    def _get_week_range(self, target_date: Optional[date] = None) -> Tuple[date, date]:
        """
        Tính toán tuần hiện tại
        
        Args:
            target_date: Target date (default: today)
            
        Returns:
            Tuple of (week_start, week_end)
        """
        if target_date is None:
            target_date = date.today()
        
        # Calculate week start (Monday)
        days_since_monday = target_date.weekday()
        week_start = target_date - timedelta(days=days_since_monday)
        week_end = week_start + timedelta(days=6)
        
        return week_start, week_end
    
    async def _get_current_vn100_symbols(self) -> Set[str]:
        """
        Lấy danh sách VN100 hiện tại từ database
        
        Returns:
            Set of current VN100 symbols
        """
        try:
            self.db_manager.initialize()
            async with self.db_manager.get_async_session() as session:
                vn100_repo = RepositoryFactory.create_vn100_current_repository(session)
                current_symbols = await vn100_repo.get_all_active_symbols()
                return set(current_symbols)
        except Exception as e:
            logger.error(f"❌ Error getting current VN100 symbols: {str(e)}")
            return set()
    
    async def _determine_symbol_status(self, symbol: str, current_symbols: Set[str]) -> VN100Status:
        """
        Xác định trạng thái của một mã
        
        Args:
            symbol: Symbol to check
            current_symbols: Set of current VN100 symbols
            
        Returns:
            VN100Status
        """
        try:
            self.db_manager.initialize()
            async with self.db_manager.get_async_session() as session:
                vn100_repo = RepositoryFactory.create_vn100_current_repository(session)
                symbol_record = await vn100_repo.get_by_symbol(symbol)
                
                if not symbol_record:
                    # New symbol
                    return VN100Status.NEW
                
                # Check weeks active
                if symbol_record.weeks_active >= 2:
                    return VN100Status.ACTIVE
                else:
                    return VN100Status.NEW
                    
        except Exception as e:
            logger.error(f"❌ Error determining status for {symbol}: {str(e)}")
            return VN100Status.UNKNOWN
    
    async def _update_vn100_history(self, symbols: List[VN100Symbol], week_start: date, week_end: date) -> None:
        """
        Cập nhật bảng vn100_history
        
        Args:
            symbols: List of VN100Symbol objects
            week_start: Week start date
            week_end: Week end date
        """
        try:
            self.db_manager.initialize()
            async with self.db_manager.get_async_session() as session:
                history_repo = RepositoryFactory.create_vn100_history_repository(session)
                
                history_data = []
                for symbol in symbols:
                    status = await self._determine_symbol_status(symbol.symbol, set())
                    
                    history_data.append({
                        'symbol': symbol.symbol,
                        'rank': symbol.rank,
                        'sector': symbol.sector,
                        'market_cap_tier': symbol.market_cap_tier,
                        'status': status,
                        'week_start': week_start,
                        'week_end': week_end,
                        'source': 'vietcap',
                        'verified': False,  # Will be updated after HOSE verification
                        'data_available': False  # Will be updated after VCI testing
                    })
                
                await history_repo.create_batch(history_data)
                logger.info(f"📝 Updated vn100_history with {len(history_data)} records")
                
        except Exception as e:
            logger.error(f"❌ Error updating vn100_history: {str(e)}")
            raise
    
    async def _update_vn100_current(self, symbols: List[VN100Symbol], week_start: date) -> None:
        """
        Cập nhật bảng vn100_current
        
        Args:
            symbols: List of VN100Symbol objects
            week_start: Week start date
        """
        try:
            self.db_manager.initialize()
            async with self.db_manager.get_async_session() as session:
                current_repo = RepositoryFactory.create_vn100_current_repository(session)
                
                # Get current symbols
                current_symbols = await current_repo.get_all_symbols()
                current_set = set(current_symbols)
                
                # Process each symbol
                for symbol in symbols:
                    existing_record = await current_repo.get_by_symbol(symbol.symbol)
                    
                    if existing_record:
                        # Update existing record
                        existing_record.rank = symbol.rank
                        existing_record.sector = symbol.sector
                        existing_record.market_cap_tier = symbol.market_cap_tier
                        existing_record.last_updated = datetime.now()
                        existing_record.weeks_active += 1
                        
                        # Update status based on weeks active
                        if existing_record.weeks_active >= 2:
                            existing_record.status = VN100Status.ACTIVE
                        else:
                            existing_record.status = VN100Status.NEW
                        
                        await current_repo.update(existing_record)
                        logger.debug(f"🔄 Updated existing record for {symbol.symbol}")
                    else:
                        # Create new record
                        new_record = {
                            'symbol': symbol.symbol,
                            'rank': symbol.rank,
                            'sector': symbol.sector,
                            'market_cap_tier': symbol.market_cap_tier,
                            'status': VN100Status.NEW,
                            'first_appeared': week_start,
                            'last_updated': datetime.now(),
                            'weeks_active': 1,
                            'verified': False,
                            'data_available': False
                        }
                        
                        await current_repo.create(new_record)
                        logger.debug(f"➕ Created new record for {symbol.symbol}")
                
                # Mark symbols not in current list as inactive
                new_symbols_set = {s.symbol for s in symbols}
                inactive_symbols = current_set - new_symbols_set
                
                for symbol in inactive_symbols:
                    record = await current_repo.get_by_symbol(symbol)
                    if record:
                        record.status = VN100Status.INACTIVE
                        record.last_updated = datetime.now()
                        await current_repo.update(record)
                        logger.debug(f"❌ Marked {symbol} as inactive")
                
                logger.info(f"📊 Updated vn100_current: {len(symbols)} active, {len(inactive_symbols)} inactive")
                
        except Exception as e:
            logger.error(f"❌ Error updating vn100_current: {str(e)}")
            raise
    
    async def run_weekly_update(self, target_date: Optional[date] = None) -> VN100UpdateResult:
        """
        Chạy cập nhật VN100 hàng tuần
        
        Args:
            target_date: Target date for update (default: today)
            
        Returns:
            VN100UpdateResult object
        """
        start_time = datetime.now()
        week_start, week_end = self._get_week_range(target_date)
        
        logger.info(f"🚀 Starting VN100 weekly update for week {week_start} to {week_end}")
        
        try:
            # Step 1: Scrape VN100 from Vietcap
            logger.info("📡 Step 1: Scraping VN100 from Vietcap...")
            scraped_symbols = await self.scraper.scrape_vn100()
            
            if not scraped_symbols:
                return VN100UpdateResult(
                    week_start=week_start,
                    week_end=week_end,
                    total_scraped=0,
                    total_verified=0,
                    total_tested=0,
                    new_symbols=[],
                    active_symbols=[],
                    inactive_symbols=[],
                    failed_symbols=[],
                    update_duration=(datetime.now() - start_time).total_seconds(),
                    success=False,
                    error_message="Failed to scrape VN100 from Vietcap"
                )
            
            logger.info(f"✅ Scraped {len(scraped_symbols)} symbols from Vietcap")
            
            # Step 2: Verify with HOSE
            logger.info("🔍 Step 2: Verifying symbols with HOSE...")
            symbols_to_verify = [s.symbol for s in scraped_symbols]
            hose_results = await self.verifier.verify_symbols_batch(symbols_to_verify)
            
            verified_symbols = []
            failed_verification = []
            
            for symbol, (is_valid, symbol_info, message) in hose_results.items():
                if is_valid and symbol_info and symbol_info.is_active:
                    verified_symbols.append(symbol)
                else:
                    failed_verification.append(symbol)
            
            logger.info(f"✅ Verified {len(verified_symbols)} symbols with HOSE")
            
            # Step 3: Test with VCI
            logger.info("🧪 Step 3: Testing symbols with VCI...")
            vci_results = await self.tester.test_symbols_batch(verified_symbols)
            
            tested_symbols = []
            failed_testing = []
            
            for symbol, result in vci_results.items():
                if result.success and result.data_points >= 20:  # Minimum data points
                    tested_symbols.append(symbol)
                else:
                    failed_testing.append(symbol)
            
            logger.info(f"✅ Tested {len(tested_symbols)} symbols with VCI")
            
            # Step 4: Filter symbols for final VN100 list
            final_symbols = [s for s in scraped_symbols if s.symbol in tested_symbols]
            
            # Step 5: Update database
            logger.info("💾 Step 5: Updating database...")
            await self._update_vn100_history(final_symbols, week_start, week_end)
            await self._update_vn100_current(final_symbols, week_start)
            
            # Step 6: Determine status changes
            current_symbols = await self._get_current_vn100_symbols()
            new_symbols = []
            active_symbols = []
            inactive_symbols = []
            
            for symbol in final_symbols:
                status = await self._determine_symbol_status(symbol.symbol, current_symbols)
                if status == VN100Status.NEW:
                    new_symbols.append(symbol.symbol)
                elif status == VN100Status.ACTIVE:
                    active_symbols.append(symbol.symbol)
            
            # Find inactive symbols
            final_symbols_set = {s.symbol for s in final_symbols}
            inactive_symbols = list(current_symbols - final_symbols_set)
            
            update_duration = (datetime.now() - start_time).total_seconds()
            
            result = VN100UpdateResult(
                week_start=week_start,
                week_end=week_end,
                total_scraped=len(scraped_symbols),
                total_verified=len(verified_symbols),
                total_tested=len(tested_symbols),
                new_symbols=new_symbols,
                active_symbols=active_symbols,
                inactive_symbols=inactive_symbols,
                failed_symbols=failed_verification + failed_testing,
                update_duration=update_duration,
                success=True
            )
            
            logger.info(f"🎉 VN100 weekly update completed successfully in {update_duration:.2f}s")
            logger.info(f"📊 Results: {len(final_symbols)} symbols, {len(new_symbols)} new, {len(active_symbols)} active, {len(inactive_symbols)} inactive")
            
            return result
            
        except Exception as e:
            update_duration = (datetime.now() - start_time).total_seconds()
            error_msg = f"Error in weekly update: {str(e)}"
            logger.error(f"❌ {error_msg}")
            
            return VN100UpdateResult(
                week_start=week_start,
                week_end=week_end,
                total_scraped=0,
                total_verified=0,
                total_tested=0,
                new_symbols=[],
                active_symbols=[],
                inactive_symbols=[],
                failed_symbols=[],
                update_duration=update_duration,
                success=False,
                error_message=error_msg
            )
    
    def get_update_summary(self, result: VN100UpdateResult) -> Dict[str, any]:
        """
        Tạo summary của kết quả cập nhật
        
        Args:
            result: VN100UpdateResult object
            
        Returns:
            Summary dictionary
        """
        return {
            'week_start': result.week_start.isoformat(),
            'week_end': result.week_end.isoformat(),
            'success': result.success,
            'update_duration': result.update_duration,
            'total_scraped': result.total_scraped,
            'total_verified': result.total_verified,
            'total_tested': result.total_tested,
            'final_symbols': len(result.active_symbols) + len(result.new_symbols),
            'new_symbols': len(result.new_symbols),
            'active_symbols': len(result.active_symbols),
            'inactive_symbols': len(result.inactive_symbols),
            'failed_symbols': len(result.failed_symbols),
            'success_rate': result.total_tested / result.total_scraped if result.total_scraped > 0 else 0,
            'new_symbols_list': result.new_symbols,
            'active_symbols_list': result.active_symbols,
            'inactive_symbols_list': result.inactive_symbols,
            'failed_symbols_list': result.failed_symbols,
            'error_message': result.error_message,
            'timestamp': datetime.now()
        }

async def run_vn100_weekly_update(target_date: Optional[date] = None) -> Dict[str, any]:
    """
    Convenience function để chạy cập nhật VN100 hàng tuần
    
    Args:
        target_date: Target date for update (default: today)
        
    Returns:
        Update summary
    """
    try:
        async with VN100Updater() as updater:
            result = await updater.run_weekly_update(target_date)
            summary = updater.get_update_summary(result)
            return summary
            
    except Exception as e:
        logger.error(f"❌ Error in run_vn100_weekly_update: {str(e)}")
        return {
            'success': False,
            'error_message': f"Error: {str(e)}",
            'timestamp': datetime.now()
        }

if __name__ == "__main__":
    async def main():
        """Test function"""
        print(f"\n{'='*60}")
        print(f"VN100 Weekly Update Test")
        print(f"{'='*60}")
        
        summary = await run_vn100_weekly_update()
        
        if summary['success']:
            print(f"\n🎉 Update completed successfully!")
            print(f"📅 Week: {summary['week_start']} to {summary['week_end']}")
            print(f"⏱️ Duration: {summary['update_duration']:.2f}s")
            print(f"📊 Results:")
            print(f"  Scraped: {summary['total_scraped']}")
            print(f"  Verified: {summary['total_verified']}")
            print(f"  Tested: {summary['total_tested']}")
            print(f"  Final symbols: {summary['final_symbols']}")
            print(f"  New symbols: {summary['new_symbols']}")
            print(f"  Active symbols: {summary['active_symbols']}")
            print(f"  Inactive symbols: {summary['inactive_symbols']}")
            print(f"  Success rate: {summary['success_rate']:.1%}")
            
            if summary['new_symbols_list']:
                print(f"\n🆕 New symbols: {', '.join(summary['new_symbols_list'])}")
            
            if summary['inactive_symbols_list']:
                print(f"\n❌ Inactive symbols: {', '.join(summary['inactive_symbols_list'])}")
        else:
            print(f"\n❌ Update failed: {summary['error_message']}")
        
        print(f"\n{'='*60}")
    
    asyncio.run(main())
