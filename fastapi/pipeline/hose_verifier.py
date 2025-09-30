"""
HOSE Verifier

Module để verify mã chứng khoán với HOSE (Ho Chi Minh Stock Exchange)
để đảm bảo tính chính xác của danh sách VN100.
"""

import asyncio
import logging
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
import aiohttp
from bs4 import BeautifulSoup
import re

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class HOSESymbolInfo:
    """Thông tin mã chứng khoán từ HOSE"""
    symbol: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    listing_date: Optional[date] = None
    is_active: bool = True
    market_cap: Optional[float] = None
    last_price: Optional[float] = None

class HOSEVerifier:
    """
    HOSE Symbol Verifier
    
    Verify mã chứng khoán với HOSE để đảm bảo:
    - Mã tồn tại và đang giao dịch
    - Thông tin cơ bản chính xác
    - Market cap và sector information
    """
    
    def __init__(self):
        self.base_url = "https://www.hsx.vn"
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'vi-VN,vi;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
        }
        
        # Cache để tránh request trùng lặp
        self._symbol_cache: Dict[str, HOSESymbolInfo] = {}
        
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
    
    async def _make_request(self, url: str, retries: int = 3) -> Optional[str]:
        """
        Make HTTP request với retry mechanism
        
        Args:
            url: URL to request
            retries: Number of retries
            
        Returns:
            HTML content or None if failed
        """
        for attempt in range(retries):
            try:
                logger.debug(f"🌐 Requesting {url} (attempt {attempt + 1}/{retries})")
                
                async with self.session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        logger.debug(f"✅ Successfully fetched {url}")
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
    
    def _parse_symbol_info(self, html: str, symbol: str) -> Optional[HOSESymbolInfo]:
        """
        Parse thông tin mã chứng khoán từ HTML
        
        Args:
            html: HTML content
            symbol: Symbol to parse
            
        Returns:
            HOSESymbolInfo object or None
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Tìm thông tin cơ bản
            name = None
            sector = None
            industry = None
            listing_date = None
            market_cap = None
            last_price = None
            
            # Tìm tên công ty
            name_selectors = [
                'h1', 'h2', '.company-name', '.stock-name', 
                '.symbol-name', '[class*="name"]'
            ]
            
            for selector in name_selectors:
                name_elem = soup.select_one(selector)
                if name_elem:
                    name_text = name_elem.get_text(strip=True)
                    if name_text and len(name_text) > 5:  # Avoid short text
                        name = name_text
                        break
            
            # Tìm sector/industry
            sector_selectors = [
                '.sector', '.industry', '.nganh', '.linh-vuc',
                '[class*="sector"]', '[class*="industry"]'
            ]
            
            for selector in sector_selectors:
                sector_elem = soup.select_one(selector)
                if sector_elem:
                    sector_text = sector_elem.get_text(strip=True)
                    if sector_text:
                        sector = sector_text
                        break
            
            # Tìm market cap
            market_cap_patterns = [
                r'vốn hóa[:\s]*([\d,]+\.?\d*)\s*(tỷ|billion|trillion)?',
                r'market cap[:\s]*([\d,]+\.?\d*)\s*(billion|trillion)?',
                r'capitalization[:\s]*([\d,]+\.?\d*)\s*(billion|trillion)?'
            ]
            
            text_content = soup.get_text()
            for pattern in market_cap_patterns:
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    try:
                        market_cap = float(match.group(1).replace(',', ''))
                        unit = match.group(2).lower() if match.group(2) else ''
                        if 'trillion' in unit:
                            market_cap *= 1000
                        elif 'tỷ' in unit:
                            market_cap *= 1
                        break
                    except ValueError:
                        continue
            
            # Tìm giá cuối
            price_patterns = [
                r'giá[:\s]*([\d,]+\.?\d*)',
                r'price[:\s]*([\d,]+\.?\d*)',
                r'last[:\s]*([\d,]+\.?\d*)'
            ]
            
            for pattern in price_patterns:
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    try:
                        last_price = float(match.group(1).replace(',', ''))
                        break
                    except ValueError:
                        continue
            
            # Tìm ngày niêm yết
            date_patterns = [
                r'niêm yết[:\s]*(\d{1,2}/\d{1,2}/\d{4})',
                r'listing[:\s]*(\d{1,2}/\d{1,2}/\d{4})',
                r'ngày[:\s]*(\d{1,2}/\d{1,2}/\d{4})'
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    try:
                        date_str = match.group(1)
                        listing_date = datetime.strptime(date_str, '%d/%m/%Y').date()
                        break
                    except ValueError:
                        continue
            
            # Kiểm tra mã có đang hoạt động không
            is_active = True
            inactive_indicators = [
                'tạm dừng', 'suspended', 'delisted', 'ngừng giao dịch',
                'không hoạt động', 'inactive'
            ]
            
            text_lower = text_content.lower()
            for indicator in inactive_indicators:
                if indicator in text_lower:
                    is_active = False
                    break
            
            symbol_info = HOSESymbolInfo(
                symbol=symbol,
                name=name or f"Unknown {symbol}",
                sector=sector,
                industry=industry,
                listing_date=listing_date,
                is_active=is_active,
                market_cap=market_cap,
                last_price=last_price
            )
            
            logger.debug(f"✅ Parsed HOSE info for {symbol}: {name}, {sector}")
            return symbol_info
            
        except Exception as e:
            logger.error(f"❌ Error parsing HOSE info for {symbol}: {str(e)}")
            return None
    
    async def verify_symbol(self, symbol: str) -> Tuple[bool, Optional[HOSESymbolInfo], str]:
        """
        Verify một mã chứng khoán với HOSE
        
        Args:
            symbol: Symbol to verify
            
        Returns:
            Tuple of (is_valid, symbol_info, message)
        """
        # Check cache first
        if symbol in self._symbol_cache:
            cached_info = self._symbol_cache[symbol]
            return True, cached_info, f"Cached info for {symbol}"
        
        try:
            # Try multiple URL patterns
            url_patterns = [
                f"{self.base_url}/en/Modules/Listed/Web/StockDetail/{symbol}",
                f"{self.base_url}/Modules/Listed/Web/StockDetail/{symbol}",
                f"{self.base_url}/stock/{symbol}",
                f"{self.base_url}/en/stock/{symbol}",
                f"{self.base_url}/Modules/Listed/Web/StockDetail.aspx?symbol={symbol}",
            ]
            
            for url in url_patterns:
                html = await self._make_request(url)
                if html:
                    symbol_info = self._parse_symbol_info(html, symbol)
                    if symbol_info:
                        # Cache the result
                        self._symbol_cache[symbol] = symbol_info
                        return True, symbol_info, f"Successfully verified {symbol}"
            
            # If no URL worked, try to verify by checking if symbol exists in listings
            listings_url = f"{self.base_url}/Modules/Listed/Web/StockList"
            html = await self._make_request(listings_url)
            if html and symbol.lower() in html.lower():
                # Symbol exists but couldn't get detailed info
                symbol_info = HOSESymbolInfo(
                    symbol=symbol,
                    name=f"Unknown {symbol}",
                    is_active=True
                )
                self._symbol_cache[symbol] = symbol_info
                return True, symbol_info, f"Symbol {symbol} exists but limited info"
            
            return False, None, f"Symbol {symbol} not found on HOSE"
            
        except Exception as e:
            logger.error(f"❌ Error verifying {symbol}: {str(e)}")
            return False, None, f"Error verifying {symbol}: {str(e)}"
    
    async def verify_symbols_batch(self, symbols: List[str], batch_size: int = 10) -> Dict[str, Tuple[bool, Optional[HOSESymbolInfo], str]]:
        """
        Verify multiple symbols với batch processing
        
        Args:
            symbols: List of symbols to verify
            batch_size: Number of symbols to process concurrently
            
        Returns:
            Dict mapping symbol to (is_valid, symbol_info, message)
        """
        logger.info(f"🔍 Starting batch verification of {len(symbols)} symbols...")
        
        results = {}
        
        # Process in batches to avoid overwhelming the server
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            logger.info(f"📦 Processing batch {i//batch_size + 1}: {batch}")
            
            # Create tasks for concurrent processing
            tasks = [self.verify_symbol(symbol) for symbol in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for symbol, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"❌ Exception verifying {symbol}: {str(result)}")
                    results[symbol] = (False, None, f"Exception: {str(result)}")
                else:
                    results[symbol] = result
            
            # Add delay between batches
            if i + batch_size < len(symbols):
                await asyncio.sleep(2)
        
        # Count results
        valid_count = sum(1 for is_valid, _, _ in results.values() if is_valid)
        logger.info(f"✅ Batch verification completed: {valid_count}/{len(symbols)} symbols valid")
        
        return results
    
    def get_verification_summary(self, results: Dict[str, Tuple[bool, Optional[HOSESymbolInfo], str]]) -> Dict[str, any]:
        """
        Tạo summary của kết quả verification
        
        Args:
            results: Results from verify_symbols_batch
            
        Returns:
            Summary dictionary
        """
        total_symbols = len(results)
        valid_symbols = sum(1 for is_valid, _, _ in results.values() if is_valid)
        invalid_symbols = total_symbols - valid_symbols
        
        valid_list = []
        invalid_list = []
        
        for symbol, (is_valid, symbol_info, message) in results.items():
            if is_valid and symbol_info:
                valid_list.append({
                    'symbol': symbol,
                    'name': symbol_info.name,
                    'sector': symbol_info.sector,
                    'is_active': symbol_info.is_active,
                    'market_cap': symbol_info.market_cap
                })
            else:
                invalid_list.append({
                    'symbol': symbol,
                    'reason': message
                })
        
        return {
            'total_symbols': total_symbols,
            'valid_symbols': valid_symbols,
            'invalid_symbols': invalid_symbols,
            'success_rate': valid_symbols / total_symbols if total_symbols > 0 else 0,
            'valid_list': valid_list,
            'invalid_list': invalid_list,
            'timestamp': datetime.now()
        }

async def verify_hose_symbols(symbols: List[str]) -> Dict[str, any]:
    """
    Convenience function để verify symbols với HOSE
    
    Args:
        symbols: List of symbols to verify
        
    Returns:
        Verification summary
    """
    try:
        async with HOSEVerifier() as verifier:
            results = await verifier.verify_symbols_batch(symbols)
            summary = verifier.get_verification_summary(results)
            return summary
            
    except Exception as e:
        logger.error(f"❌ Error in verify_hose_symbols: {str(e)}")
        return {
            'total_symbols': len(symbols),
            'valid_symbols': 0,
            'invalid_symbols': len(symbols),
            'success_rate': 0,
            'valid_list': [],
            'invalid_list': [{'symbol': s, 'reason': f'Error: {str(e)}'} for s in symbols],
            'timestamp': datetime.now()
        }

if __name__ == "__main__":
    async def main():
        """Test function"""
        test_symbols = ['VCB', 'BID', 'CTG', 'TCB', 'MBB', 'ACB', 'HDB', 'TPB', 'STB', 'EIB']
        
        print(f"\n{'='*50}")
        print(f"HOSE Verification Test")
        print(f"{'='*50}")
        
        summary = await verify_hose_symbols(test_symbols)
        
        print(f"\n📊 Verification Summary:")
        print(f"  Total symbols: {summary['total_symbols']}")
        print(f"  Valid symbols: {summary['valid_symbols']}")
        print(f"  Invalid symbols: {summary['invalid_symbols']}")
        print(f"  Success rate: {summary['success_rate']:.1%}")
        
        if summary['valid_list']:
            print(f"\n✅ Valid symbols:")
            for item in summary['valid_list'][:5]:
                print(f"  {item['symbol']}: {item['name']} - {item['sector'] or 'N/A'}")
        
        if summary['invalid_list']:
            print(f"\n❌ Invalid symbols:")
            for item in summary['invalid_list'][:5]:
                print(f"  {item['symbol']}: {item['reason']}")
        
        print(f"\n{'='*50}")
    
    asyncio.run(main())
