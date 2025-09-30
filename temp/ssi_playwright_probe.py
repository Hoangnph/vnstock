#!/usr/bin/env python3
"""
Playwright probe for SSI: capture network logs when calling SSI statistics API

Usage:
  python temp/ssi_playwright_probe.py ACB 2020-01-02 2025-09-29

Outputs:
  - temp/ssi_playwright_log.json  (filtered requests/responses)
  - temp/ssi.har                  (HAR with embedded content)
"""

import asyncio
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List

from playwright.async_api import async_playwright

BASE_PAGE = "https://iboard.ssi.com.vn/"
API_HOST = "iboard-api.ssi.com.vn"
API_PATH = "/statistics/company/ssmi/stock-info"


def fmt_ddmmyyyy(d: str) -> str:
    try:
        dt = datetime.fromisoformat(d).date()
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return d


async def run(symbol: str, from_date: str, to_date: str) -> None:
    out_dir = Path("temp")
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "ssi_playwright_log.json"
    har_path = out_dir / "ssi.har"

    logs: List[Dict[str, Any]] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            record_har_path=str(har_path),
            record_har_content="embed",
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        def include_req(url: str) -> bool:
            return API_HOST in url and API_PATH in url

        page.on("request", lambda req: logs.append({
            "type": "request",
            "method": req.method,
            "url": req.url,
            "headers": req.headers,
            "post_data": req.post_data,
            "ts": datetime.utcnow().isoformat(),
        }) if include_req(req.url) else None)

        async def on_response(res):
            if include_req(res.url):
                try:
                    body = await res.text()
                except Exception:
                    body = None
                logs.append({
                    "type": "response",
                    "url": res.url,
                    "status": res.status,
                    "headers": await res.all_headers(),
                    "body": body[:2000] if isinstance(body, str) else None,
                    "ts": datetime.utcnow().isoformat(),
                })

        page.on("response", lambda r: asyncio.create_task(on_response(r)))

        # Go to the site first (to get any cookies/headers the app may use)
        await page.goto(BASE_PAGE, wait_until="domcontentloaded")

        # Trigger the API call from page context with realistic headers
        fd = fmt_ddmmyyyy(from_date)
        td = fmt_ddmmyyyy(to_date)
        url = f"https://{API_HOST}{API_PATH}?symbol={symbol}&page=1&pageSize=10&fromDate={fd}&toDate={td}"

        await page.evaluate(
            "async (url) => {\n"
            "  await fetch(url, {\n"
            "    method: 'GET',\n"
            "    headers: {\n"
            "      'Accept': 'application/json, text/plain, */*',\n"
            "      'Referer': 'https://iboard.ssi.com.vn/',\n"
            "    }\n"
            "  });\n"
            "}",
            url,
        )

        # small wait to allow response capture
        await page.wait_for_timeout(1500)

        await context.close()
        await browser.close()

    log_path.write_text(json.dumps(logs, ensure_ascii=False, indent=2))
    print("LOG_SAVED", str(log_path))
    print("HAR_SAVED", str(har_path))


if __name__ == "__main__":
    sym = sys.argv[1] if len(sys.argv) > 1 else "ACB"
    frm = sys.argv[2] if len(sys.argv) > 2 else "2020-01-02"
    to = sys.argv[3] if len(sys.argv) > 3 else date.today().isoformat()
    asyncio.run(run(sym, frm, to))



