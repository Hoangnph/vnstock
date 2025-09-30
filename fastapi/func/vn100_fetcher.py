#!/usr/bin/env python3
"""
VN100 Fetcher - Get VN100 stock symbols
Hàm lấy danh sách mã VN100

VN100 là chỉ số 100 cổ phiếu có vốn hóa lớn nhất và thanh khoản cao nhất trên HOSE

Author: StockAI Team
Version: 1.0.0
"""

import pandas as pd
import requests
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VN100Fetcher:
    """VN100 symbols fetcher for Vietnamese stock market"""
    
    def __init__(self):
        """Initialize the VN100 fetcher"""
        self.vn100_symbols = []
        self.vn100_by_sector = {}
        self.industry_map: Dict[str, str] = {}

    def load_industry_mapping(self, industries_csv_path: str = "assets/data/symbols_by_industries.csv") -> Dict[str, str]:
        """
        Load symbol -> icb_name2 mapping from industries CSV
        
        Args:
            industries_csv_path (str): Path to industries csv with columns including 'symbol' and 'icb_name2'
        
        Returns:
            Dict[str, str]: Mapping from symbol (upper) to icb_name2
        """
        try:
            df_ind = pd.read_csv(industries_csv_path)
            if 'symbol' in df_ind.columns and 'icb_name2' in df_ind.columns:
                # Normalize symbol to upper and strip
                df_ind['symbol'] = df_ind['symbol'].astype(str).str.upper().str.strip()
                df_ind['icb_name2'] = df_ind['icb_name2'].astype(str).str.strip()
                mapping = dict(zip(df_ind['symbol'], df_ind['icb_name2']))
                self.industry_map = mapping
                logger.info(f"✅ Loaded industry mapping for {len(mapping)} symbols from {industries_csv_path}")
                return mapping
            else:
                logger.warning("⚠️ industries CSV missing required columns 'symbol'/'icb_name2'")
                return {}
        except Exception as e:
            logger.warning(f"⚠️ Failed to load industries CSV: {str(e)}")
            return {}
        
    async def get_vn100_symbols(self) -> List[str]:
        """
        Lấy danh sách mã VN100 từ database
        
        Returns:
            List[str]: Danh sách mã chứng khoán VN100 từ database
        """
        try:
            # Import VN100DatabaseLoader
            from .vn100_database_loader import VN100DatabaseLoader
            
            loader = VN100DatabaseLoader()
            vn100_symbols = await loader.get_active_vn100_symbols()
            
            if not vn100_symbols:
                logger.warning("⚠️ No VN100 symbols found in database, falling back to SSI API list")
                # Fallback to SSI API list if database is empty
                import pandas as pd
                try:
                    df_ssi = pd.read_csv('assets/data/vn100_official_ssi.csv')
                    vn100_symbols = df_ssi['symbol'].tolist()
                    logger.info(f"✅ Loaded {len(vn100_symbols)} VN100 symbols from SSI API fallback")
                except Exception as e:
                    logger.error(f"❌ Failed to load SSI API fallback: {str(e)}")
                    return []
            
            self.vn100_symbols = vn100_symbols
            logger.info(f"✅ Loaded {len(vn100_symbols)} VN100 symbols from database")
            return vn100_symbols
            
        except Exception as e:
            logger.error(f"❌ Error loading VN100 symbols from database: {str(e)}")
            # Fallback to SSI API list
            try:
                import pandas as pd
                df_ssi = pd.read_csv('assets/data/vn100_official_ssi.csv')
                vn100_symbols = df_ssi['symbol'].tolist()
                logger.info(f"✅ Fallback: Loaded {len(vn100_symbols)} VN100 symbols from SSI API")
                self.vn100_symbols = vn100_symbols
                return vn100_symbols
            except Exception as e2:
                logger.error(f"❌ Fallback also failed: {str(e2)}")
                return []
    
    async def get_vn100_by_sector(self) -> Dict[str, List[str]]:
        """
        Lấy VN100 phân loại theo ngành từ database
        
        Returns:
            Dict[str, List[str]]: Dictionary với key là ngành, value là danh sách mã
        """
        try:
            # Import VN100DatabaseLoader
            from .vn100_database_loader import VN100DatabaseLoader
            
            loader = VN100DatabaseLoader()
            vn100_by_sector = await loader.get_vn100_by_sector_from_db()
            
            if not vn100_by_sector:
                logger.warning("⚠️ No VN100 sectors found in database, falling back to SSI API list")
                # Fallback to SSI API list if database is empty
                import pandas as pd
                try:
                    df_ssi = pd.read_csv('assets/data/vn100_official_ssi.csv')
                    vn100_by_sector = {}
                    for _, row in df_ssi.iterrows():
                        sector = self._determine_sector(row['company_name_vi'])
                        if sector not in vn100_by_sector:
                            vn100_by_sector[sector] = []
                        vn100_by_sector[sector].append(row['symbol'])
                    logger.info(f"✅ Loaded VN100 by sector from SSI API fallback")
                except Exception as e:
                    logger.error(f"❌ Failed to load SSI API fallback: {str(e)}")
                    return {}
            
            self.vn100_by_sector = vn100_by_sector
            logger.info(f"✅ Loaded VN100 by sector from database: {len(vn100_by_sector)} sectors")
            return vn100_by_sector
            
        except Exception as e:
            logger.error(f"❌ Error loading VN100 by sector from database: {str(e)}")
            # Fallback to SSI API list
            try:
                import pandas as pd
                df_ssi = pd.read_csv('assets/data/vn100_official_ssi.csv')
                vn100_by_sector = {}
                for _, row in df_ssi.iterrows():
                    sector = self._determine_sector(row['company_name_vi'])
                    if sector not in vn100_by_sector:
                        vn100_by_sector[sector] = []
                    vn100_by_sector[sector].append(row['symbol'])
                logger.info(f"✅ Fallback: Loaded VN100 by sector from SSI API")
                self.vn100_by_sector = vn100_by_sector
                return vn100_by_sector
            except Exception as e2:
                logger.error(f"❌ Fallback also failed: {str(e2)}")
                return {}
    
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
    
    def get_vn100_from_screener(self) -> List[str]:
        """
        Lấy danh sách VN100 từ vnstock screener
        
        Returns:
            List[str]: Danh sách mã từ screener
        """
        
        logger.info("🔄 Đang lấy VN100 từ vnstock screener...")
        
        try:
            from vnstock import Screener
            
            # Tạo screener instance
            screener = Screener()
            
            # Lấy danh sách VN100 (top 100 by market cap)
            vn100_data = screener.get_top_stocks(
                exchange='HOSE',
                limit=100,
                sort_by='market_cap',
                ascending=False
            )
            
            if vn100_data is not None and not vn100_data.empty:
                symbols = vn100_data['symbol'].tolist()
                logger.info(f"✅ Lấy được {len(symbols)} mã từ screener")
                return symbols
            else:
                logger.warning("⚠️ Không lấy được dữ liệu từ screener")
                return []
                
        except ImportError:
            logger.warning("⚠️ vnstock không có sẵn, sử dụng danh sách thủ công")
            return []
        except Exception as e:
            logger.warning(f"⚠️ Lỗi khi lấy dữ liệu từ screener: {str(e)}")
            return []
    
    def get_vn100_from_api(self) -> List[str]:
        """
        Lấy danh sách VN100 từ API công khai
        
        Returns:
            List[str]: Danh sách mã từ API
        """
        
        logger.info("🔄 Đang lấy VN100 từ API...")
        
        # Thử các API khác nhau
        apis = [
            {
                'name': 'HOSE API',
                'url': 'https://api.hose.vn/api/v1/indices/VN100',
                'parser': lambda x: [item['symbol'] for item in x.get('data', [])]
            },
            {
                'name': 'SSI API',
                'url': 'https://iboard.ssi.com.vn/dchart/api/1.1/default/history',
                'parser': lambda x: []
            }
        ]
        
        for api in apis:
            try:
                logger.info(f"   Thử {api['name']}...")
                response = requests.get(api['url'], timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    symbols = api['parser'](data)
                    
                    if symbols:
                        logger.info(f"✅ Lấy được {len(symbols)} mã từ {api['name']}")
                        return symbols
                        
            except Exception as e:
                logger.warning(f"   ❌ Lỗi {api['name']}: {str(e)}")
                continue
        
        logger.warning("⚠️ Không lấy được dữ liệu từ API")
        return []
    
    def create_vn100_dataframe(self) -> pd.DataFrame:
        """
        Tạo DataFrame chứa thông tin VN100
        
        Returns:
            pd.DataFrame: DataFrame với thông tin VN100
        """
        
        # Lấy danh sách VN100
        vn100_symbols = self.get_vn100_symbols()
        # Load industry mapping (symbol -> icb_name2)
        if not self.industry_map:
            self.load_industry_mapping()
        vn100_by_sector = self.get_vn100_by_sector()
        
        # Tạo DataFrame
        data = []
        for i, symbol in enumerate(vn100_symbols, 1):
            # Ưu tiên dùng icb_name2 từ file industries
            sector = self.industry_map.get(symbol)
            if not sector or pd.isna(sector):
                # Fallback: phân loại thủ công nếu không có trong mapping
                sector = 'Other'
                for sector_name, symbols in vn100_by_sector.items():
                    if symbol in symbols:
                        sector = sector_name
                        break
            
            # Xác định tier
            if i <= 30:
                tier = 'Tier 1'
            elif i <= 60:
                tier = 'Tier 2'
            else:
                tier = 'Tier 3'
            
            data.append({
                'symbol': symbol,
                'rank': i,
                'sector': sector,
                'market_cap_tier': tier,
                'updated_date': datetime.now().strftime('%Y-%m-%d')
            })
        
        df = pd.DataFrame(data)
        return df
    
    def save_vn100_csv(self, output_path: str) -> bool:
        """
        Lưu danh sách VN100 vào file CSV
        
        Args:
            output_path (str): Đường dẫn file CSV
            
        Returns:
            bool: Thành công hay không
        """
        
        try:
            # Tạo DataFrame
            df = self.create_vn100_dataframe()
            
            # Tạo thư mục nếu chưa có
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Lưu file CSV
            df.to_csv(output_path, index=False)
            
            logger.info(f"✅ Đã lưu {len(df)} mã VN100 vào {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi lưu file CSV: {str(e)}")
            return False
    
    def get_vn100_statistics(self) -> Dict[str, any]:
        """
        Lấy thống kê VN100
        
        Returns:
            Dict[str, any]: Thống kê VN100
        """
        
        df = self.create_vn100_dataframe()
        
        stats = {
            'total_symbols': len(df),
            'updated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'sector_distribution': df['sector'].value_counts().to_dict(),
            'tier_distribution': df['market_cap_tier'].value_counts().to_dict(),
            'top_20': df.head(20)[['rank', 'symbol', 'sector']].to_dict('records')
        }
        
        return stats
    
    def print_statistics(self):
        """In thống kê VN100"""
        
        stats = self.get_vn100_statistics()
        
        print(f"\n📊 Thống kê VN100:")
        print(f"   📈 Tổng số mã: {stats['total_symbols']}")
        print(f"   📅 Cập nhật: {stats['updated_date']}")
        
        # Thống kê theo ngành
        print(f"\n📊 Phân bố theo ngành:")
        for sector, count in stats['sector_distribution'].items():
            print(f"   {sector}: {count} mã")
        
        # Thống kê theo tier
        print(f"\n📊 Phân bố theo tier:")
        for tier, count in stats['tier_distribution'].items():
            print(f"   {tier}: {count} mã")
        
        # Hiển thị top 20
        print(f"\n🏆 Top 20 VN100:")
        for item in stats['top_20']:
            print(f"   {item['rank']:2d}. {item['symbol']} ({item['sector']})")


def get_vn100_symbols() -> List[str]:
    """
    Convenience function to get VN100 symbols
    
    Returns:
        List[str]: Danh sách 100 mã chứng khoán VN100
        
    Example:
        >>> symbols = get_vn100_symbols()
        >>> print(f"VN100 có {len(symbols)} mã")
    """
    
    fetcher = VN100Fetcher()
    return fetcher.get_vn100_symbols()


def get_vn100_dataframe() -> pd.DataFrame:
    """
    Convenience function to get VN100 DataFrame
    
    Returns:
        pd.DataFrame: DataFrame với thông tin VN100
        
    Example:
        >>> df = get_vn100_dataframe()
        >>> print(df.head())
    """
    
    fetcher = VN100Fetcher()
    return fetcher.create_vn100_dataframe()


def save_vn100_csv(output_path: str = "assets/data/vn100_symbols.csv") -> bool:
    """
    Convenience function to save VN100 to CSV
    
    Args:
        output_path (str): Đường dẫn file CSV
        
    Returns:
        bool: Thành công hay không
        
    Example:
        >>> success = save_vn100_csv("data/vn100.csv")
        >>> if success:
        ...     print("Đã lưu VN100 thành công")
    """
    
    fetcher = VN100Fetcher()
    return fetcher.save_vn100_csv(output_path)


def get_vn100_by_sector(sector: str) -> List[str]:
    """
    Lấy danh sách mã VN100 theo ngành
    
    Args:
        sector (str): Tên ngành (Banking, Real Estate, etc.)
        
    Returns:
        List[str]: Danh sách mã theo ngành
        
    Example:
        >>> banking_symbols = get_vn100_by_sector('Banking')
        >>> print(f"Ngân hàng có {len(banking_symbols)} mã")
    """
    
    fetcher = VN100Fetcher()
    vn100_by_sector = fetcher.get_vn100_by_sector()
    
    return vn100_by_sector.get(sector, [])


def get_vn100_top_n(n: int = 20) -> List[str]:
    """
    Lấy top N mã VN100
    
    Args:
        n (int): Số lượng mã cần lấy
        
    Returns:
        List[str]: Danh sách top N mã
        
    Example:
        >>> top_10 = get_vn100_top_n(10)
        >>> print(f"Top 10: {top_10}")
    """
    
    fetcher = VN100Fetcher()
    symbols = fetcher.get_vn100_symbols()
    
    return symbols[:n]


# Example usage and testing
if __name__ == "__main__":
    print("🚀 Testing VN100 Fetcher...")
    
    # Test basic functions
    fetcher = VN100Fetcher()
    
    # Get symbols
    symbols = fetcher.get_vn100_symbols()
    print(f"✅ VN100 có {len(symbols)} mã")
    
    # Get by sector
    banking_symbols = fetcher.get_vn100_by_sector()['Banking']
    print(f"✅ Ngân hàng có {len(banking_symbols)} mã: {banking_symbols[:5]}...")
    
    # Create DataFrame
    df = fetcher.create_vn100_dataframe()
    print(f"✅ DataFrame có {len(df)} dòng, {len(df.columns)} cột")
    
    # Print statistics
    fetcher.print_statistics()
    
    # Save to CSV
    success = fetcher.save_vn100_csv("test_vn100.csv")
    if success:
        print("✅ Đã lưu file test_vn100.csv")
    
    print("\n🎉 Test hoàn thành!")
