#!/usr/bin/env python3
"""
SSI Fetcher with Update Tracking

Enhanced SSI fetcher that uses update tracking for incremental updates.
This fetcher checks the tracking table to determine the start date for updates,
avoiding duplicate data and enabling efficient incremental updates.

Author: StockAI Team
Version: 1.0.0
"""

import asyncio
import logging
import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import httpx
from playwright.async_api import async_playwright
from fastapi.func.ssi_config import SSIAPIConfig, get_endpoint_url

from database.api.database import get_async_session
from database.api.repositories import RepositoryFactory
from database.schema.models import DataSource, StockPrice
from sqlalchemy import select, func

logger = logging.getLogger(__name__)

def _merge_headers(base: Dict[str, str], override: Dict[str, str]) -> Dict[str, str]:
    merged = dict(base or {})
    for k, v in (override or {}).items():
        merged[k] = v
    return merged

def _fmt_ddmmyyyy(d: str | date) -> str:
    if isinstance(d, str):
        try:
            dt = datetime.fromisoformat(d).date()
        except ValueError:
            return d
    else:
        dt = d
    return dt.strftime("%d/%m/%Y")

def _to_unix_timestamp(d: str | date) -> int:
    if isinstance(d, str):
        dt = datetime.fromisoformat(d)
    else:
        dt = datetime(d.year, d.month, d.day)
    return int(dt.timestamp())

class SSIFetcherWithTracking:
    def __init__(self):
        self.data_source = DataSource.SSI
        self.cfg = SSIAPIConfig.load()
        # Build URLs
        self.stock_info_url = get_endpoint_url(self.cfg, "stock_info")
        # Headers: default + playwright override for API host if present
        default_headers = self.cfg.headers.get("default", {})
        pw_override = self.cfg.headers.get("playwright_override", {}).get("iboard-api.ssi.com.vn", {})
        self.request_headers = _merge_headers(default_headers, pw_override)

    async def _get_json(self, url: str, params: Dict[str, Any], use_playwright: bool = False) -> Optional[Dict[str, Any]]:
        timeout = httpx.Timeout(30.0, connect=10.0)
        retries = 3
        backoff = 0.5
        last_exc: Optional[Exception] = None

        for attempt in range(retries):
            try:
                if use_playwright:
                    logger.info(f"🌐 Playwright fallback for {url} (attempt {attempt + 1})")
                    return await self._fetch_with_playwright(url, params)
                else:
                    async with httpx.AsyncClient(timeout=timeout, headers=self.request_headers, http2=True) as client:
                        resp = await client.get(url, params=params)
                        resp.raise_for_status()
                        
                        # Try to decode response with different encodings
                        try:
                            return resp.json()
                        except UnicodeDecodeError:
                            # Try with different encoding
                            text = resp.content.decode('utf-8', errors='ignore')
                            import json
                            return json.loads(text)
                        except Exception as json_error:
                            logger.warning(f"⚠️ JSON decode error for {url}: {json_error} (attempt {attempt + 1})")
                            # Check if this is a "no data" response (binary data or empty response)
                            if any(msg in str(json_error) for msg in [
                                "Expecting value: line 1 column 1 (char 0)",
                                "codec can't decode",
                                "truncated data"
                            ]):
                                logger.info(f"⏭️ No data available for this time period, skipping...")
                                return {"code": "SUCCESS", "data": []}
                            # Try playwright fallback on next attempt
                            if attempt < retries - 1:
                                use_playwright = True
                                continue
                            raise
                            
            except httpx.HTTPStatusError as e:
                logger.warning(f"⚠️ HTTP error {e.response.status_code} for {url}: {e} (attempt {attempt + 1})")
                if e.response.status_code in (403, 429, 503):
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    last_exc = e
                    continue
                raise
            except Exception as e:
                logger.warning(f"⚠️ Error fetching {url}: {e} (attempt {attempt + 1})")
                await asyncio.sleep(backoff)
                backoff *= 2
                last_exc = e
                continue
        if last_exc:
            raise last_exc
        return None

    async def _fetch_with_playwright(self, base_url: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=self.request_headers.get("user-agent", self.request_headers.get("User-Agent", "")),
                extra_http_headers={
                    "Accept-Language": self.request_headers.get("accept-language", self.request_headers.get("Accept-Language", "vi")),
                    "Origin": self.request_headers.get("origin", self.request_headers.get("Origin", "https://iboard.ssi.com.vn")),
                    "Referer": self.request_headers.get("referer", self.request_headers.get("Referer", "https://iboard.ssi.com.vn/")),
                },
            )
            page = await context.new_page()

            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            full_url = f"{base_url}?{query_string}"

            try:
                # First visit the main page to get cookies
                await page.goto("https://iboard.ssi.com.vn/", wait_until="domcontentloaded")
                await asyncio.sleep(2)  # Wait for cookies to be set
                
                # Now make the API request with proper headers
                response = await page.evaluate(
                    "async (url) => {\n"
                    "  const resp = await fetch(url, {\n"
                    "    method: 'GET',\n"
                    "    headers: {\n"
                    "      'Accept': 'application/json, text/plain, */*',\n"
                    "      'Accept-Language': document.headers && document.headers['accept-language'] || 'vi',\n"
                    "      'Origin': location.origin,\n"
                    "      'Referer': location.origin + '/',\n"
                    "      'Sec-Fetch-Dest': 'empty',\n"
                    "      'Sec-Fetch-Mode': 'cors',\n"
                    "      'Sec-Fetch-Site': 'same-site'\n"
                    "    }\n"
                    "  });\n"
                    "  return resp.json();\n"
                    "}",
                    full_url
                )
                return response
            except Exception as e:
                logger.error(f"❌ Playwright fetch failed for {full_url}: {e}")
                return None
            finally:
                await browser.close()

    async def get_update_start_date(self, symbol: str, target_end_date: date) -> date:
        """Get the start date for updates based on tracking info"""
        async with get_async_session() as session:
            tracking_repo = RepositoryFactory.create_stock_update_tracking_repository(session)
            
            # Get or create tracking info
            tracking = await tracking_repo.get_or_create_tracking(symbol, self.data_source)
            # Also read the latest price date we already have in DB to avoid duplicates
            latest_price = None
            try:
                q = select(func.max(StockPrice.time)).where(StockPrice.symbol == symbol.upper())
                res = await session.execute(q)
                latest_price = res.scalar_one_or_none()
            except Exception:
                latest_price = None
            latest_price_date: Optional[date] = None
            if latest_price is not None:
                try:
                    latest_price_date = latest_price.date()
                except Exception:
                    latest_price_date = None
            
            # Use the max between tracking and actual latest price in DB
            effective_last_updated = tracking.last_updated_date
            if latest_price_date and latest_price_date > effective_last_updated:
                effective_last_updated = latest_price_date
            
            # If last updated date is before target, start from next day
            if effective_last_updated < target_end_date:
                start_date = effective_last_updated + timedelta(days=1)
                logger.info(f"📅 {symbol}: Starting from {start_date} (last updated: {effective_last_updated})")
                return start_date
            else:
                logger.info(f"✅ {symbol}: Already up to date (last updated: {effective_last_updated})")
                return target_end_date + timedelta(days=1)  # No update needed

    async def fetch_daily_with_tracking(
        self, 
        symbol: str, 
        target_end_date: Optional[date] = None
    ) -> Tuple[bool, Optional[pd.DataFrame], Optional[date]]:
        """
        Fetch daily data with tracking support
        
        Returns:
            (success, dataframe, last_updated_date)
        """
        if target_end_date is None:
            target_end_date = date.today()
        # Adjust effective end date based on market close (16:00 Asia/Ho_Chi_Minh)
        now_local = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
        market_close_today = now_local.replace(hour=16, minute=0, second=0, microsecond=0)
        effective_end_date = target_end_date
        if now_local.date() == target_end_date and now_local < market_close_today:
            # Before close: do not fetch today's incomplete session
            effective_end_date = target_end_date - timedelta(days=1)
        
        # Get start date from tracking
        start_date = await self.get_update_start_date(symbol, effective_end_date)
        
        # If no update needed, return empty dataframe
        if start_date > effective_end_date:
            return True, pd.DataFrame(), effective_end_date
        
        # Fetch data using the original logic
        success, df = await self._fetch_daily_data(symbol, start_date, effective_end_date)
        
        if df is not None and not df.empty:
            # Get the last date from the data
            last_date = df['time'].max().date()
            return True, df, last_date
        else:
            # No new rows fetched (already up to date or no data in range)
            return True, pd.DataFrame(), start_date - timedelta(days=1)

    async def _fetch_daily_data(self, symbol: str, start_date: date, end_date: date) -> Tuple[bool, Optional[pd.DataFrame]]:
        """Fetch data using stock-info API as primary source"""
        try:
            # Use stock-info API as primary source (it includes both OHLCV and foreign trade data)
            return await self._fetch_with_stock_info_fallback(symbol, start_date, end_date)
        except Exception as e:
            logger.error(f"❌ Failed to fetch daily data for {symbol}: {e}")
            return False, None

    async def _fetch_with_stock_info_fallback(self, symbol: str, start_date: date, end_date: date) -> Tuple[bool, Optional[pd.DataFrame]]:
        """Fallback method using windowed stock-info requests"""
        try:
            acc_rows: List[Dict] = []
            cur_to = end_date
            window_days = 365
            consecutive_empty_windows = 0
            max_empty_windows = 3  # Stop after 3 consecutive empty windows
            
            while cur_to >= start_date and consecutive_empty_windows < max_empty_windows:
                cur_from = max(start_date, cur_to - timedelta(days=window_days - 1))
                page = 1
                page_size = 1000
                got_any = False
                
                while True:
                    params = {
                        "symbol": symbol.upper(),
                        "page": page,
                        "pageSize": page_size,
                        "fromDate": _fmt_ddmmyyyy(cur_from.isoformat()),
                        "toDate": _fmt_ddmmyyyy(cur_to.isoformat()),
                    }
                    
                    try:
                        data = await self._get_json(self.stock_info_url, params)
                    except Exception:
                        # Treat any exception on this page as no data for this window/page
                        data = {"code": "SUCCESS", "data": []}
                    if (not data) or (isinstance(data, dict) and data.get("code") != "SUCCESS"):
                        try:
                            data = await self._get_json(self.stock_info_url, params, use_playwright=True)
                        except Exception:
                            data = {"code": "SUCCESS", "data": []}
                        if (not data) or (isinstance(data, dict) and data.get("code") != "SUCCESS"):
                            logger.info(f"⏭️ No data available for {symbol} in window {cur_from} to {cur_to}")
                            break
                    
                    items = data.get("data") if isinstance(data, dict) else data
                    if not items:
                        break
                    
                    acc_rows.extend(items)
                    got_any = True
                    
                    if len(items) < page_size:
                        break
                    page += 1
                
                if not got_any:
                    consecutive_empty_windows += 1
                    cur_to = cur_to - timedelta(days=window_days)
                    logger.info(f"📅 {symbol}: No data in window {cur_from} to {cur_to}, moving back {window_days} days (empty window {consecutive_empty_windows}/{max_empty_windows})")
                else:
                    consecutive_empty_windows = 0  # Reset counter when we find data
                    try:
                        oldest = min(items, key=lambda it: it.get("tradingDate", "")).get("tradingDate", None)
                        if oldest:
                            od = datetime.strptime(oldest, "%d/%m/%Y").date()
                            cur_to = od - timedelta(days=1)
                            logger.info(f"📅 {symbol}: Found data from {oldest}, moving to {cur_to}")
                        else:
                            cur_to = cur_to - timedelta(days=window_days)
                    except Exception:
                        cur_to = cur_to - timedelta(days=window_days)
            
            if consecutive_empty_windows >= max_empty_windows:
                logger.info(f"⏹️ {symbol}: Stopped fetching after {max_empty_windows} consecutive empty windows - likely no more historical data")
            
            if acc_rows:
                df_si_all = pd.DataFrame(acc_rows)
                df_si_all = df_si_all.rename(columns={
                    "tradingDate": "time",
                    "open": "open",
                    "openPrice": "open",
                    "high": "high",
                    "highPrice": "high",
                    "low": "low",
                    "lowPrice": "low",
                    "close": "close",
                    "closePrice": "close",
                    "totalMatchVol": "volume",
                    "volume": "volume",
                })
                
                if "time" in df_si_all.columns:
                    df_si_all["time"] = pd.to_datetime(df_si_all["time"], format="%d/%m/%Y", errors="coerce").dt.tz_localize("Asia/Ho_Chi_Minh", nonexistent="shift_forward", ambiguous="NaT").dt.tz_convert("UTC")
                    df_price = df_si_all[["time", "open", "high", "low", "close", "volume"]].dropna(subset=["time"]).drop_duplicates(subset=["time"]).sort_values("time")
                    
                    # Add foreign trade columns
                    df_price['foreign_buy_shares'] = 0
                    df_price['foreign_sell_shares'] = 0
                    
                    df = self._clean_dataframe(df_price)
                    return True, df
            
            # No rows accumulated; still a successful, empty fetch
            return True, pd.DataFrame()
            
        except Exception as e:
            logger.error(f"❌ Stock-info fallback failed for {symbol}: {e}")
            # Return what we have if any partial rows were collected elsewhere
            return True, pd.DataFrame()

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean dataframe to ensure database constraints are met"""
        if df.empty:
            return df
        
        # Drop duplicate columns if any
        df = df.loc[:, ~df.columns.duplicated()]
        
        # Ensure numeric types
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'foreign_buy_shares', 'foreign_sell_shares']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Constraint-friendly cleaning
        zero_close_mask = df["close"] <= 0
        if zero_close_mask.any():
            df.loc[zero_close_mask, "close"] = df.loc[zero_close_mask, "open"]
        
        # low must be <= close and <= open
        low_gt_close = df["low"] > df["close"]
        if low_gt_close.any():
            df.loc[low_gt_close, "low"] = df.loc[low_gt_close, "close"]
        low_gt_open = df["low"] > df["open"]
        if low_gt_open.any():
            df.loc[low_gt_open, "low"] = df.loc[low_gt_open, "open"]
        
        # high must be >= close and >= open
        high_lt_close = df["high"] < df["close"]
        if high_lt_close.any():
            df.loc[high_lt_close, "high"] = df.loc[high_lt_close, "close"]
        high_lt_open = df["high"] < df["open"]
        if high_lt_open.any():
            df.loc[high_lt_open, "high"] = df.loc[high_lt_open, "open"]
        
        # ensure high >= low
        high_lt_low = df["high"] < df["low"]
        if high_lt_low.any():
            df.loc[high_lt_low, "high"] = df.loc[high_lt_low, "low"]
        
        # final filter of invalid rows
        invalid_mask = (
            (df["close"] <= 0) |
            (df["high"] < df["close"]) |
            (df["low"] > df["close"]) |
            (df["high"] < df["open"]) |
            (df["low"] > df["open"]) |
            (df["high"] < df["low"]) |
            (df["volume"] < 0)
        )
        if invalid_mask.any():
            df = df[~invalid_mask]
        
        # Sort by time ascending
        if "time" in df.columns:
            df = df.sort_values("time").reset_index(drop=True)
        
        return df

    async def update_tracking_success(
        self, 
        symbol: str, 
        last_updated_date: date, 
        total_records: int,
        duration_seconds: Optional[int] = None
    ) -> None:
        """Update tracking info after successful update"""
        async with get_async_session() as session:
            tracking_repo = RepositoryFactory.create_stock_update_tracking_repository(session)
            await tracking_repo.update_tracking_success(
                symbol, self.data_source, last_updated_date, total_records, duration_seconds
            )

    async def update_tracking_error(self, symbol: str, error_message: str) -> None:
        """Update tracking info after failed update"""
        async with get_async_session() as session:
            tracking_repo = RepositoryFactory.create_stock_update_tracking_repository(session)
            await tracking_repo.update_tracking_error(symbol, self.data_source, error_message)
