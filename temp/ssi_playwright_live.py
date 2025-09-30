#!/usr/bin/env python3
"""
Launch a headed Chromium window to iboard.ssi.com.vn and live-capture
network traffic to files while you interact manually.

Outputs (under temp/):
  - ssi_live_log.jsonl  (newline-delimited JSON of requests/responses)
  - ssi_live.har        (HAR with embedded content)

Stop by closing the browser window or pressing Ctrl+C in the terminal.
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from playwright.async_api import async_playwright


def ts() -> str:
    return datetime.now(timezone.utc).isoformat()


async def main() -> None:
    out_dir = Path("temp")
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "ssi_live_log.jsonl"
    har_path = out_dir / "ssi_live.har"

    print("Opening Chromium... (a window will appear)")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
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

        # Live append logs
        log_file = log_path.open("a", encoding="utf-8")

        def write_event(ev: Dict[str, Any]) -> None:
            ev["ts"] = ts()
            log_file.write(json.dumps(ev, ensure_ascii=False) + "\n")
            log_file.flush()

        page.on(
            "request",
            lambda req: write_event(
                {
                    "type": "request",
                    "method": req.method,
                    "url": req.url,
                    "headers": req.headers,
                    "post_data": req.post_data,
                }
            ),
        )

        async def on_response(res):
            try:
                body = await res.text()
            except Exception:
                body = None
            write_event(
                {
                    "type": "response",
                    "url": res.url,
                    "status": res.status,
                    "headers": await res.all_headers(),
                    "body": body[:2000] if isinstance(body, str) else None,
                }
            )

        page.on("response", lambda r: asyncio.create_task(on_response(r)))

        await page.goto("https://iboard.ssi.com.vn/", wait_until="domcontentloaded")
        print("Ready. Interact with the website. Logs ->", log_path)
        print("Close the window to stop.")

        # Wait until the page (window) is closed (no timeout)
        await page.wait_for_event("close", timeout=0)
        log_file.close()
        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())


