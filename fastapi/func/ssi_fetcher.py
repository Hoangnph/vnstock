#!/usr/bin/env python3
"""
SSI Daily Fetcher

Fetch daily OHLCV and foreign trading data from SSI iBoard endpoints.
This module focuses on reliability with retries and returns a normalized
pandas DataFrame with columns: time, open, high, low, close, volume,
foreign_buy_shares, foreign_sell_shares.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import httpx
from contextlib import asynccontextmanager
try:
    from playwright.async_api import async_playwright
except Exception:
    async_playwright = None  # optional fallback if not installed
import pandas as pd

logger = logging.getLogger(__name__)


def _fmt_ddmmyyyy(d: str) -> str:
    try:
        dt = datetime.fromisoformat(d).date()
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return d


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://iboard.ssi.com.vn",
    "Referer": "https://iboard.ssi.com.vn/",
    "Connection": "keep-alive",
}


class SSIDailyFetcher:
    """Fetch daily OHLCV and foreign from SSI.

    Note: SSI APIs are not public docs. We use iBoard endpoints observed from
    network logs. If endpoints change, adjust here.
    """

    # Working iBoard endpoint (observed from Playwright logs)
    STOCK_INFO_URL = "https://iboard-api.ssi.com.vn/statistics/company/ssmi/stock-info"
    DCHART_URL = "https://iboard.ssi.com.vn/dchart/api/1.1/default/history"

    async def _get_json(self, url: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        timeout = httpx.Timeout(20.0, connect=5.0)
        retries = 3
        backoff = 0.8
        async with httpx.AsyncClient(timeout=timeout, headers=DEFAULT_HEADERS, http2=True) as client:
            last_exc: Optional[Exception] = None
            for _ in range(retries):
                try:
                    resp = await client.get(url, params=params)
                    if resp.status_code == 200:
                        return resp.json()
                    if resp.status_code in (403, 429, 503):
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        continue
                    logger.warning(f"SSI GET {url} returned {resp.status_code}")
                    return None
                except Exception as e:
                    last_exc = e
                    await asyncio.sleep(backoff)
                    backoff *= 2
            if last_exc:
                logger.warning(f"SSI GET {url} failed: {last_exc}")
        return None

    @asynccontextmanager
    async def _playwright_context(self):
        if async_playwright is None:
            yield None, None
            return
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=DEFAULT_HEADERS["User-Agent"],
        )
        page = await context.new_page()
        try:
            yield page, context
        finally:
            await context.close()
            await browser.close()
            await pw.stop()

    async def _get_json_playwright(self, url: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if async_playwright is None:
            return None
        query = "&".join([f"{k}={httpx.QueryParams({k: v})[k]}" for k, v in params.items()])
        full_url = f"{url}?{query}"
        async with self._playwright_context() as (page, _ctx):
            if page is None:
                return None
            try:
                # Visit iBoard domain first to acquire cookies
                await page.goto("https://iboard.ssi.com.vn/", wait_until="domcontentloaded")
                js = (
                    "async (u) => {\n"
                    "  const r = await fetch(u, {\n"
                    "    method: 'GET',\n"
                    "    headers: {\n"
                    "      'Accept': 'application/json, text/plain, */*',\n"
                    "      'Referer': 'https://iboard.ssi.com.vn/',\n"
                    "    }\n"
                    "  });\n"
                    "  if (!r.ok) return { ok: false, status: r.status };\n"
                    "  let d = null;\n"
                    "  try { d = await r.json(); } catch(e) { d = null; }\n"
                    "  return { ok: true, status: r.status, data: d };\n"
                    "}"
                )
                res = await page.evaluate(js, full_url)
                if res and res.get("ok") and res.get("data") is not None:
                    return res["data"]
            except Exception as e:
                logger.warning(f"Playwright fallback failed for {full_url}: {e}")
        return None

    async def fetch_daily(self, symbol: str, start_date: str, end_date: Optional[str]) -> Tuple[bool, Optional[pd.DataFrame]]:
        if end_date is None:
            end_date = datetime.now().date().isoformat()
        # 1) Pull full OHLCV via dchart (supports long range)
        try:
            import time as _time
            from datetime import datetime as _dt
            ts_from = int(_dt.fromisoformat(start_date).timestamp())
            ts_to = int(_dt.fromisoformat(end_date).timestamp())
        except Exception:
            return False, None

        dparams = {
            "symbol": symbol.upper(),
            "resolution": "1D",
            "from": ts_from,
            "to": ts_to,
        }
        # Prefer Playwright for dchart to bypass Cloudflare/CORS
        df_price: Optional[pd.DataFrame] = None
        djson = await self._get_json_playwright(self.DCHART_URL, dparams)
        if not djson:
            djson = await self._get_json(self.DCHART_URL, dparams)
        if djson and isinstance(djson, dict) and djson.get("t"):
            try:
                df_price = pd.DataFrame({
                    "time": pd.to_datetime(pd.Series(djson["t"], dtype="int64"), unit="s").dt.tz_localize("UTC"),
                    "open": pd.Series(djson.get("o", []), dtype="float"),
                    "high": pd.Series(djson.get("h", []), dtype="float"),
                    "low": pd.Series(djson.get("l", []), dtype="float"),
                    "close": pd.Series(djson.get("c", []), dtype="float"),
                    "volume": pd.Series(djson.get("v", []), dtype="int64").fillna(0).astype(int),
                })
            except Exception:
                df_price = None

        # Fallback: windowed stock-info to reconstruct OHLCV if dchart blocked
        if df_price is None:
            try:
                from datetime import datetime as _dt, timedelta as _td
                acc_rows: list[dict] = []
                cur_to = _dt.fromisoformat(end_date).date()
                start_dt = _dt.fromisoformat(start_date).date()
                window_days = 365
                while cur_to >= start_dt:
                    cur_from = max(start_dt, cur_to - _td(days=window_days - 1))
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
                        data = await self._get_json(self.STOCK_INFO_URL, params)
                        if (not data) or (isinstance(data, dict) and data.get("code") != "SUCCESS"):
                            data = await self._get_json_playwright(self.STOCK_INFO_URL, params)
                            if (not data) or (isinstance(data, dict) and data.get("code") != "SUCCESS"):
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
                        # move back to avoid infinite loop
                        cur_to = cur_to - _td(days=window_days)
                    else:
                        # step to the day before the oldest we just got
                        try:
                            oldest = min(items, key=lambda it: it.get("tradingDate", "")).get("tradingDate", None)
                            if oldest:
                                od = _dt.strptime(oldest, "%d/%m/%Y").date()
                                cur_to = od - _td(days=1)
                            else:
                                cur_to = cur_to - _td(days=window_days)
                        except Exception:
                            cur_to = cur_to - _td(days=window_days)
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
            except Exception:
                df_price = None

        if df_price is None or df_price.empty:
            return False, None

        # 2) Pull foreign totals via stock-info (recent window), then merge
        page = 1
        page_size = 1000
        rows: list[dict] = []
        while True:
            params = {
                "symbol": symbol.upper(),
                "page": page,
                "pageSize": page_size,
                "fromDate": _fmt_ddmmyyyy(start_date),
                "toDate": _fmt_ddmmyyyy(end_date),
            }
            data = await self._get_json(self.STOCK_INFO_URL, params)
            if (not data) or (isinstance(data, dict) and data.get("code") != "SUCCESS"):
                # Try Playwright fallback for this page
                data = await self._get_json_playwright(self.STOCK_INFO_URL, params)
                if (not data) or (isinstance(data, dict) and data.get("code") != "SUCCESS"):
                    break
            items = data.get("data") if isinstance(data, dict) else data
            if not items:
                break
            rows.extend(items)
            if len(items) < page_size:
                break
            page += 1
        df = df_price.copy()
        if rows:
            df_si = pd.DataFrame(rows)
            # map fields
            si_map = {
                "tradingDate": "time",
                "foreignBuyVolTotal": "foreign_buy_shares",
                "foreignSellVolTotal": "foreign_sell_shares",
            }
            for k, v in si_map.items():
                if k in df_si.columns and v not in df_si.columns:
                    df_si = df_si.rename(columns={k: v})
            if "time" in df_si.columns:
                df_si["time"] = pd.to_datetime(df_si["time"], format="%d/%m/%Y", errors="coerce").dt.tz_localize("Asia/Ho_Chi_Minh", nonexistent="shift_forward", ambiguous="NaT").dt.tz_convert("UTC")
                df_foreign = df_si[[c for c in ["time", "foreign_buy_shares", "foreign_sell_shares"] if c in df_si.columns]].copy()
                df = pd.merge(df, df_foreign, on="time", how="left")
            else:
                df["foreign_buy_shares"] = 0
                df["foreign_sell_shares"] = 0
        else:
            df["foreign_buy_shares"] = 0
            df["foreign_sell_shares"] = 0

        # Drop duplicate columns if any (can happen after merges)
        df = df.loc[:, ~df.columns.duplicated()]

        # Sort by time ascending
        if "time" in df.columns:
            df = df.sort_values("time").reset_index(drop=True)

        # Fill NA with safe defaults
        df["volume"] = df.get("volume", 0).fillna(0).astype(int)
        df["open"] = df.get("open", 0).fillna(0).astype(float)
        df["high"] = df.get("high", 0).fillna(0).astype(float)
        df["low"] = df.get("low", 0).fillna(0).astype(float)
        df["close"] = df.get("close", 0).fillna(0).astype(float)
        df["foreign_buy_shares"] = df.get("foreign_buy_shares", 0).fillna(0).astype(int)
        df["foreign_sell_shares"] = df.get("foreign_sell_shares", 0).fillna(0).astype(int)

        # Constraint-friendly cleaning (match pipeline rules)
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

        return True, df


