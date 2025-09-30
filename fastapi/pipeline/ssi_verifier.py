"""
SSI Verifier - Verify updated data against SSI statistics API

Endpoint example:
https://iboard-api.ssi.com.vn/statistics/company/ssmi/stock-info
  ?symbol=ACB&page=1&pageSize=10&fromDate=02%2F01%2F2020&toDate=29%2F09%2F2025

This module calls the SSI API for a symbol and date range to verify
that data exists for the specified period. It returns lightweight
verification results for logging and monitoring in the pipeline.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, Optional

import asyncio
import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://iboard-api.ssi.com.vn/statistics/company/ssmi/stock-info"

# Some endpoints enforce anti-bot protections; realistic headers help reduce 403s
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


def _fmt_ddmmyyyy(d: str | date) -> str:
    if isinstance(d, str):
        # Expect ISO yyyy-mm-dd
        try:
            dt = datetime.fromisoformat(d).date()
        except Exception:
            return d
    else:
        dt = d
    return dt.strftime("%d/%m/%Y")


async def verify_with_ssi(symbol: str, from_date: str, to_date: str) -> Dict[str, Any]:
    """
    Verify a symbol has SSI statistics within [from_date, to_date].

    Returns:
        {
          'ok': bool,
          'symbol': str,
          'from_date': str,
          'to_date': str,
          'status_code': int,
          'items': int,
          'message': str
        }
    """
    params = {
        "symbol": symbol.upper(),
        "page": 1,
        "pageSize": 10,
        "fromDate": _fmt_ddmmyyyy(from_date),
        "toDate": _fmt_ddmmyyyy(to_date),
    }

    try:
        timeout = httpx.Timeout(10.0, connect=5.0)
        retries = 3
        backoff = 0.5
        last_exc: Optional[Exception] = None
        status = -1
        data = None

        async with httpx.AsyncClient(timeout=timeout, headers=DEFAULT_HEADERS, http2=True) as client:
            for attempt in range(retries):
                try:
                    resp = await client.get(BASE_URL, params=params)
                    status = resp.status_code
                    if status == 200:
                        data = resp.json()
                        break
                    # If forbidden, backoff and retry (anti-bot)
                    if status in (403, 429, 503):
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        continue
                    # Other statuses: don't retry aggressively
                    break
                except Exception as e:
                    last_exc = e
                    await asyncio.sleep(backoff)
                    backoff *= 2

        if data is None and status != 200 and last_exc:
            raise last_exc

        if status != 200:
            msg = f"SSI API returned {status}"
            logger.warning(f"⚠️ {msg} for {symbol} {params}")
            return {
                "ok": False,
                "symbol": symbol,
                "from_date": from_date,
                "to_date": to_date,
                "status_code": status,
                "items": 0,
                "message": msg,
            }

        # The response structure may include list under 'data' or direct list
        items = 0
        if isinstance(data, dict):
            if "data" in data and isinstance(data["data"], list):
                items = len(data["data"])
            elif "items" in data and isinstance(data["items"], list):
                items = len(data["items"])
        elif isinstance(data, list):
            items = len(data)

        ok = items > 0
        if not ok:
            logger.warning(
                f"⚠️ SSI verifier found no items for {symbol} in {from_date}..{to_date}"
            )
        else:
            logger.info(
                f"🔎 SSI verifier: {symbol} has {items} items in {from_date}..{to_date}"
            )
        return {
            "ok": ok,
            "symbol": symbol,
            "from_date": from_date,
            "to_date": to_date,
            "status_code": status,
            "items": items,
            "message": "ok" if ok else "no_items",
        }
    except Exception as e:
        msg = f"SSI verify error: {e}"
        logger.warning(f"⚠️ {msg} for {symbol} {params}")
        return {
            "ok": False,
            "symbol": symbol,
            "from_date": from_date,
            "to_date": to_date,
            "status_code": -1,
            "items": 0,
            "message": msg,
        }


