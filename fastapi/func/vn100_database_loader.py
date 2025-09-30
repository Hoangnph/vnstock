"""
VN100 Database Loader

Module để load VN100 symbols từ database thay vì từ CSV files
"""

import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from database.api.database import DatabaseManager
from database.api.repositories import RepositoryFactory
from database.schema.models import VN100Current, VN100Status, Stock, MarketExchange

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VN100DatabaseLoader:
    """VN100 Database Loader - Load VN100 symbols from database"""
    
    def __init__(self):
        """Initialize the VN100 database loader"""
        self.db_manager = DatabaseManager()
        self.db_manager.initialize()
    
    async def get_vn100_symbols_from_db(self, status: Optional[VN100Status] = None) -> List[str]:
        """
        Lấy danh sách VN100 symbols từ database
        
        Args:
            status: Filter theo status (NEW, ACTIVE, INACTIVE, UNKNOWN)
        
        Returns:
            List[str]: Danh sách symbols VN100
        """
        try:
            async with self.db_manager.get_async_session() as session:
                vn100_repo = RepositoryFactory.create_vn100_current_repository(session)
                
                if status:
                    vn100_records = await vn100_repo.get_by_status(status)
                else:
                    vn100_records = await vn100_repo.get_all()
                
                symbols = [record.symbol for record in vn100_records]
                
                logger.info(f"✅ Loaded {len(symbols)} VN100 symbols from database")
                if status:
                    logger.info(f"   Filtered by status: {status}")
                
                return symbols
                
        except Exception as e:
            logger.error(f"❌ Error loading VN100 symbols from database: {str(e)}")
            return []
    
    async def get_active_vn100_symbols(self) -> List[str]:
        """
        Lấy danh sách VN100 symbols đang active
        
        Returns:
            List[str]: Danh sách symbols VN100 đang active
        """
        return await self.get_vn100_symbols_from_db(VN100Status.ACTIVE)
    
    async def get_vn100_symbols_with_details(self, status: Optional[VN100Status] = None) -> List[Dict]:
        """
        Lấy danh sách VN100 symbols với thông tin chi tiết từ database
        
        Args:
            status: Filter theo status
        
        Returns:
            List[Dict]: Danh sách symbols với thông tin chi tiết
        """
        try:
            async with self.db_manager.get_async_session() as session:
                vn100_repo = RepositoryFactory.create_vn100_current_repository(session)
                
                if status:
                    vn100_records = await vn100_repo.get_by_status(status)
                else:
                    vn100_records = await vn100_repo.get_all()
                
                symbols_details = []
                for record in vn100_records:
                    symbols_details.append({
                        'symbol': record.symbol,
                        'rank': record.rank,
                        'sector': record.sector,
                        'market_cap_tier': record.market_cap_tier,
                        'status': record.status,
                        'first_appeared': record.first_appeared,
                        'last_updated': record.last_updated,
                        'weeks_active': record.weeks_active,
                        'verified': record.verified,
                        'data_available': record.data_available
                    })
                
                logger.info(f"✅ Loaded {len(symbols_details)} VN100 symbols with details from database")
                return symbols_details
                
        except Exception as e:
            logger.error(f"❌ Error loading VN100 symbols with details from database: {str(e)}")
            return []
    
    async def get_vn100_by_sector_from_db(self) -> Dict[str, List[str]]:
        """
        Lấy VN100 symbols theo sector từ database
        
        Returns:
            Dict[str, List[str]]: Mapping sector -> list of symbols
        """
        try:
            symbols_details = await self.get_vn100_symbols_with_details()
            
            vn100_by_sector = {}
            for symbol_detail in symbols_details:
                sector = symbol_detail.get('sector', 'Unknown')
                if sector not in vn100_by_sector:
                    vn100_by_sector[sector] = []
                vn100_by_sector[sector].append(symbol_detail['symbol'])
            
            logger.info(f"✅ Organized {len(symbols_details)} VN100 symbols by sector")
            return vn100_by_sector
            
        except Exception as e:
            logger.error(f"❌ Error organizing VN100 symbols by sector: {str(e)}")
            return {}
    
    async def seed_vn100_from_ssi_api(self) -> bool:
        """
        Seed VN100 symbols từ SSI API vào database
        
        Returns:
            bool: True nếu thành công
        """
        try:
            logger.info("🌱 Seeding VN100 symbols from SSI API to database...")
            
            # Load SSI API data
            import pandas as pd
            df_ssi = pd.read_csv('assets/data/vn100_official_ssi.csv')
            
            async with self.db_manager.get_async_session() as session:
                vn100_repo = RepositoryFactory.create_vn100_current_repository(session)
                stock_repo = RepositoryFactory.create_stock_repository(session)
                
                # Clear existing VN100 data
                existing_records = await vn100_repo.get_all()
                for record in existing_records:
                    await vn100_repo.delete(record.id)
                
                logger.info(f"🗑️ Cleared {len(existing_records)} existing VN100 records")
                
                # Seed new VN100 data
                for i, row in df_ssi.iterrows():
                    # Create stock record if not exists
                    stock = await stock_repo.get_by_symbol(row['symbol'])
                    if not stock:
                        stock_data = {
                            'symbol': row['symbol'],
                            'name': row['company_name_vi'],
                            'exchange': MarketExchange.HOSE,
                            'is_active': True,
                            'created_at': datetime.now(),
                            'updated_at': datetime.now()
                        }
                        stock = await stock_repo.create(stock_data)
                        logger.info(f"🌱 Created stock record for {row['symbol']}")
                    
                    # Create VN100 record
                    vn100_data = {
                        'symbol': row['symbol'],
                        'rank': i + 1,
                        'sector': self._determine_sector(row['company_name_vi']),
                        'market_cap_tier': self._determine_market_cap_tier(row['ref_price']),
                        'status': VN100Status.ACTIVE,
                        'first_appeared': date.today(),
                        'last_updated': datetime.now(),
                        'weeks_active': 1,
                        'verified': True,
                        'data_available': True
                    }
                    
                    await vn100_repo.create(vn100_data)
                
                logger.info(f"✅ Successfully seeded {len(df_ssi)} VN100 symbols from SSI API")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error seeding VN100 from SSI API: {str(e)}")
            return False
    
    def _determine_sector(self, company_name: str) -> str:
        """Determine sector from company name"""
        company_name_lower = company_name.lower()
        
        if any(word in company_name_lower for word in ['ngân hàng', 'bank']):
            return 'Banking'
        elif any(word in company_name_lower for word in ['bất động sản', 'đầu tư', 'phát triển']):
            return 'Real Estate'
        elif any(word in company_name_lower for word in ['thép', 'hóa chất', 'phân bón']):
            return 'Basic Resources'
        elif any(word in company_name_lower for word in ['điện', 'khí', 'nước']):
            return 'Utilities'
        elif any(word in company_name_lower for word in ['bia', 'rượu', 'sữa', 'thực phẩm']):
            return 'Food & Beverage'
        elif any(word in company_name_lower for word in ['dầu khí', 'xăng dầu']):
            return 'Oil & Gas'
        elif any(word in company_name_lower for word in ['bán lẻ', 'thương mại', 'vàng bạc']):
            return 'Retail'
        elif any(word in company_name_lower for word in ['công nghệ', 'phần mềm', 'fpt']):
            return 'Technology'
        else:
            return 'Other'
    
    def _determine_market_cap_tier(self, ref_price: float) -> str:
        """Determine market cap tier from reference price"""
        if ref_price >= 100000:  # >= 100k VND
            return 'Large'
        elif ref_price >= 50000:  # >= 50k VND
            return 'Medium'
        else:
            return 'Small'

# Convenience functions
async def get_vn100_symbols_from_db(status: Optional[VN100Status] = None) -> List[str]:
    """Convenience function to get VN100 symbols from database"""
    loader = VN100DatabaseLoader()
    return await loader.get_vn100_symbols_from_db(status)

async def get_active_vn100_symbols_from_db() -> List[str]:
    """Convenience function to get active VN100 symbols from database"""
    loader = VN100DatabaseLoader()
    return await loader.get_active_vn100_symbols()

async def get_vn100_symbols_with_details_from_db(status: Optional[VN100Status] = None) -> List[Dict]:
    """Convenience function to get VN100 symbols with details from database"""
    loader = VN100DatabaseLoader()
    return await loader.get_vn100_symbols_with_details(status)

async def seed_vn100_from_ssi_api_to_db() -> bool:
    """Convenience function to seed VN100 from SSI API to database"""
    loader = VN100DatabaseLoader()
    return await loader.seed_vn100_from_ssi_api()

if __name__ == "__main__":
    async def main():
        """Test function"""
        print(f"\n{'='*80}")
        print(f"VN100 DATABASE LOADER TEST")
        print(f"{'='*80}")
        
        loader = VN100DatabaseLoader()
        
        # Test 1: Seed VN100 from SSI API
        print(f"\n🌱 Testing VN100 seeding from SSI API...")
        success = await loader.seed_vn100_from_ssi_api()
        print(f"   Result: {'✅ Success' if success else '❌ Failed'}")
        
        # Test 2: Get all VN100 symbols
        print(f"\n📊 Testing get all VN100 symbols...")
        all_symbols = await loader.get_vn100_symbols_from_db()
        print(f"   Found {len(all_symbols)} symbols")
        if all_symbols:
            print(f"   First 10: {', '.join(all_symbols[:10])}")
        
        # Test 3: Get active VN100 symbols
        print(f"\n✅ Testing get active VN100 symbols...")
        active_symbols = await loader.get_active_vn100_symbols()
        print(f"   Found {len(active_symbols)} active symbols")
        
        # Test 4: Get VN100 by sector
        print(f"\n📈 Testing get VN100 by sector...")
        vn100_by_sector = await loader.get_vn100_by_sector_from_db()
        print(f"   Found {len(vn100_by_sector)} sectors")
        for sector, symbols in vn100_by_sector.items():
            print(f"   {sector}: {len(symbols)} symbols")
        
        # Test 5: Get VN100 with details
        print(f"\n🔍 Testing get VN100 with details...")
        symbols_details = await loader.get_vn100_symbols_with_details()
        print(f"   Found {len(symbols_details)} symbols with details")
        if symbols_details:
            first_symbol = symbols_details[0]
            print(f"   First symbol: {first_symbol['symbol']} - {first_symbol['sector']} - {first_symbol['status']}")
        
        print(f"\n{'='*80}")
    
    asyncio.run(main())
