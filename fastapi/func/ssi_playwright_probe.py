from __future__ import annotations

import asyncio
from pathlib import Path
from datetime import datetime

from playwright.async_api import async_playwright


HAR_DIR = Path("assets/logs")
HAR_DIR.mkdir(parents=True, exist_ok=True)
HAR_PATH = HAR_DIR / f"ssi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.har"


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"]) 
        context = await browser.new_context(
            record_har_path=str(HAR_PATH),
            record_har_mode="minimal",
        )
        page = await context.new_page()
        print(f"Opening https://iboard.ssi.com.vn, HAR will be saved to: {HAR_PATH}")
        await page.goto("https://iboard.ssi.com.vn", wait_until="domcontentloaded")
        print("Perform your actions (login, navigate to symbols, etc.).")
        print("When finished, return to this terminal and press Enter to close and save HAR.")
        try:
            input()
        except KeyboardInterrupt:
            pass
        await context.close()
        await browser.close()
        print(f"HAR saved: {HAR_PATH}")


if __name__ == "__main__":
    asyncio.run(main())


