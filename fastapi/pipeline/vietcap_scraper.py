"""
Vietcap VN100 Scraper

Module để scrape danh sách VN100 từ Vietcap price board
với độ chính xác cao và error handling robust.
"""

import asyncio
import logging
import re
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import aiohttp
from bs4 import BeautifulSoup
import pandas as pd

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class VN100Symbol:
    """Data class cho VN100 symbol"""
    symbol: str
    rank: int
    sector: Optional[str] = None
    market_cap_tier: Optional[str] = None
    price: Optional[float] = None
    change: Optional[float] = None
    volume: Optional[int] = None

class VietcapScraper:
    """
    Vietcap VN100 Scraper
    
    Scrape danh sách VN100 từ Vietcap price board với:
    - Anti-bot protection handling
    - Rate limiting
    - Error retry mechanism
    - Data validation
    """
    
    def __init__(self):
        self.base_url = "https://trading.vietcap.com.vn"
        self.vn100_url = f"{self.base_url}/price-board"
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'vi-VN,vi;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
    async def __aenter__(self):
        """Async context manager entry"""
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.headers
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _make_request(self, url: str, params: Dict = None, retries: int = 3) -> Optional[str]:
        """
        Make HTTP request với retry mechanism
        
        Args:
            url: URL to request
            params: Query parameters
            retries: Number of retries
            
        Returns:
            HTML content or None if failed
        """
        for attempt in range(retries):
            try:
                logger.info(f"🌐 Requesting {url} (attempt {attempt + 1}/{retries})")
                
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        content = await response.text()
                        logger.info(f"✅ Successfully fetched {url}")
                        return content
                    elif response.status == 429:  # Rate limited
                        wait_time = 2 ** attempt
                        logger.warning(f"⏳ Rate limited, waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.warning(f"⚠️ HTTP {response.status} for {url}")
                        
            except asyncio.TimeoutError:
                logger.warning(f"⏰ Timeout for {url} (attempt {attempt + 1})")
            except Exception as e:
                logger.error(f"❌ Error requesting {url}: {str(e)}")
                
            if attempt < retries - 1:
                await asyncio.sleep(1)
                
        logger.error(f"❌ Failed to fetch {url} after {retries} attempts")
        return None
    
    def _parse_vn100_table(self, html: str) -> List[VN100Symbol]:
        """
        Parse VN100 table từ HTML
        
        Args:
            html: HTML content
            
        Returns:
            List of VN100Symbol objects
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            symbols = []
            
            # Tìm table chứa VN100 data
            tables = soup.find_all('table')
            logger.info(f"🔍 Found {len(tables)} tables in HTML")
            
            for table_idx, table in enumerate(tables):
                logger.info(f"📊 Processing table {table_idx + 1}")
                
                # Tìm header để xác định cột
                headers = table.find_all('th')
                if not headers:
                    continue
                    
                header_texts = [h.get_text(strip=True).lower() for h in headers]
                logger.info(f"📋 Table headers: {header_texts}")
                
                # Tìm các cột cần thiết
                symbol_col = None
                rank_col = None
                sector_col = None
                price_col = None
                change_col = None
                volume_col = None
                
                for i, header in enumerate(header_texts):
                    if any(keyword in header for keyword in ['mã', 'symbol', 'code']):
                        symbol_col = i
                    elif any(keyword in header for keyword in ['rank', 'thứ', 'hạng']):
                        rank_col = i
                    elif any(keyword in header for keyword in ['ngành', 'sector', 'industry']):
                        sector_col = i
                    elif any(keyword in header for keyword in ['giá', 'price', 'last']):
                        price_col = i
                    elif any(keyword in header for keyword in ['thay', 'change', 'đổi']):
                        change_col = i
                    elif any(keyword in header for keyword in ['khối', 'volume', 'lượng']):
                        volume_col = i
                
                logger.info(f"📍 Column mapping: symbol={symbol_col}, rank={rank_col}, sector={sector_col}")
                
                # Parse rows
                rows = table.find_all('tr')[1:]  # Skip header
                logger.info(f"📈 Found {len(rows)} data rows")
                
                for row_idx, row in enumerate(rows):
                    cells = row.find_all(['td', 'th'])
                    if len(cells) < 2:
                        continue
                        
                    try:
                        # Extract symbol
                        symbol_text = cells[symbol_col].get_text(strip=True) if symbol_col is not None else ""
                        symbol_match = re.search(r'([A-Z]{3,4})', symbol_text)
                        if not symbol_match:
                            continue
                        symbol = symbol_match.group(1)
                        
                        # Extract rank
                        rank = 0
                        if rank_col is not None:
                            rank_text = cells[rank_col].get_text(strip=True)
                            rank_match = re.search(r'(\d+)', rank_text)
                            if rank_match:
                                rank = int(rank_match.group(1))
                        
                        # Extract sector
                        sector = None
                        if sector_col is not None:
                            sector = cells[sector_col].get_text(strip=True)
                        
                        # Extract price
                        price = None
                        if price_col is not None:
                            price_text = cells[price_col].get_text(strip=True)
                            price_match = re.search(r'([\d,]+\.?\d*)', price_text.replace(',', ''))
                            if price_match:
                                price = float(price_match.group(1))
                        
                        # Extract change
                        change = None
                        if change_col is not None:
                            change_text = cells[change_col].get_text(strip=True)
                            change_match = re.search(r'([+-]?[\d,]+\.?\d*)', change_text.replace(',', ''))
                            if change_match:
                                change = float(change_match.group(1))
                        
                        # Extract volume
                        volume = None
                        if volume_col is not None:
                            volume_text = cells[volume_col].get_text(strip=True)
                            volume_match = re.search(r'([\d,]+)', volume_text.replace(',', ''))
                            if volume_match:
                                volume = int(volume_match.group(1))
                        
                        # Determine market cap tier based on rank
                        if rank <= 30:
                            market_cap_tier = "Tier 1"
                        elif rank <= 70:
                            market_cap_tier = "Tier 2"
                        else:
                            market_cap_tier = "Tier 3"
                        
                        vn100_symbol = VN100Symbol(
                            symbol=symbol,
                            rank=rank,
                            sector=sector,
                            market_cap_tier=market_cap_tier,
                            price=price,
                            change=change,
                            volume=volume
                        )
                        
                        symbols.append(vn100_symbol)
                        logger.debug(f"✅ Parsed: {symbol} (rank {rank})")
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Error parsing row {row_idx}: {str(e)}")
                        continue
                
                # Nếu tìm thấy symbols thì dừng lại
                if symbols:
                    logger.info(f"🎯 Found {len(symbols)} VN100 symbols in table {table_idx + 1}")
                    break
            
            # Sort by rank
            symbols.sort(key=lambda x: x.rank)
            
            logger.info(f"📊 Total VN100 symbols parsed: {len(symbols)}")
            return symbols
            
        except Exception as e:
            logger.error(f"❌ Error parsing VN100 table: {str(e)}")
            return []
    
    async def scrape_vn100(self) -> List[VN100Symbol]:
        """
        Scrape VN100 symbols từ Vietcap
        
        Returns:
            List of VN100Symbol objects
        """
        logger.info("🚀 Starting VN100 scraping from Vietcap...")
        
        # Parameters for VN100 filter
        params = {
            'filter-group': 'HOSE',
            'filter-value': 'VN100',
            'view-type': 'FLAT'
        }
        
        html = await self._make_request(self.vn100_url, params)
        if not html:
            logger.error("❌ Failed to fetch VN100 page")
            return []
        
        symbols = self._parse_vn100_table(html)
        
        if not symbols:
            logger.warning("⚠️ No VN100 symbols found, trying alternative approach...")
            # Try without filters
            html = await self._make_request(self.vn100_url)
            if html:
                symbols = self._parse_vn100_table(html)
        
        logger.info(f"✅ Successfully scraped {len(symbols)} VN100 symbols")
        return symbols
    
    def to_dataframe(self, symbols: List[VN100Symbol]) -> pd.DataFrame:
        """
        Convert VN100Symbol list to DataFrame
        
        Args:
            symbols: List of VN100Symbol objects
            
        Returns:
            DataFrame with VN100 data
        """
        data = []
        for symbol in symbols:
            data.append({
                'symbol': symbol.symbol,
                'rank': symbol.rank,
                'sector': symbol.sector,
                'market_cap_tier': symbol.market_cap_tier,
                'price': symbol.price,
                'change': symbol.change,
                'volume': symbol.volume,
                'scraped_at': datetime.now()
            })
        
        df = pd.DataFrame(data)
        logger.info(f"📊 Created DataFrame with {len(df)} rows")
        return df

async def scrape_vietcap_vn100() -> Tuple[bool, List[VN100Symbol], str]:
    """
    Convenience function để scrape VN100 từ Vietcap
    
    Returns:
        Tuple of (success, symbols, message)
    """
    try:
        async with VietcapScraper() as scraper:
            symbols = await scraper.scrape_vn100()
            
            if symbols:
                return True, symbols, f"Successfully scraped {len(symbols)} VN100 symbols"
            else:
                return False, [], "No VN100 symbols found"
                
    except Exception as e:
        logger.error(f"❌ Error in scrape_vietcap_vn100: {str(e)}")
        return False, [], f"Error: {str(e)}"

if __name__ == "__main__":
    async def main():
        """Test function"""
        success, symbols, message = await scrape_vietcap_vn100()
        
        print(f"\n{'='*50}")
        print(f"VN100 Scraping Result: {message}")
        print(f"{'='*50}")
        
        if success and symbols:
            print(f"\n📊 Found {len(symbols)} VN100 symbols:")
            for symbol in symbols[:10]:  # Show first 10
                print(f"  {symbol.rank:2d}. {symbol.symbol} - {symbol.sector or 'N/A'}")
            
            if len(symbols) > 10:
                print(f"  ... and {len(symbols) - 10} more")
            
            # Save to CSV
            df = VietcapScraper().to_dataframe(symbols)
            csv_path = "temp/vietcap_vn100_scraped.csv"
            df.to_csv(csv_path, index=False)
            print(f"\n💾 Saved to: {csv_path}")
        
        print(f"\n{'='*50}")
    
    asyncio.run(main())
