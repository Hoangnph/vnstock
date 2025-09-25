import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

ALL_PATH = Path('/Users/macintoshhd/Project/Project/stockAI/output/network_all.jsonl')
HITS_PATH = Path('/Users/macintoshhd/Project/Project/stockAI/output/network_hits_foreign.jsonl')

KEYWORDS = ['data-mt/graphql', 'graphql', 'foreign', 'Foreign', 'ownership', 'ownership/foreign']

def is_hit(url: str, body: str | None) -> bool:
    hay = (url or '') + ' ' + (body or '')
    return any(k in hay for k in KEYWORDS)

async def main():
    # reset logs
    for p in (ALL_PATH, HITS_PATH):
        if p.exists():
            p.unlink()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        async def on_request(request):
            try:
                rec = {
                    'method': request.method,
                    'url': request.url,
                }
                try:
                    rec['post_data'] = request.post_data
                except Exception:
                    rec['post_data'] = None
                with ALL_PATH.open('a') as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + '\n')
                if is_hit(rec['url'], rec.get('post_data')):
                    with HITS_PATH.open('a') as f:
                        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
            except Exception:
                pass

        page.on('request', on_request)

        await page.goto('https://trading.vietcap.com.vn/iq/company?ticker=PDR&tab=information&informationTab=foreign', wait_until='domcontentloaded')
        print('Playwright capture started. Interact with the page for up to 5 minutes...')
        print('Logs:')
        print(' -', ALL_PATH)
        print(' -', HITS_PATH)
        await page.wait_for_timeout(5 * 60 * 1000)
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())


