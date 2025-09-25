import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

ALL_REQ = Path('/Users/macintoshhd/Project/Project/stockAI/output/network_all.jsonl')
HIT_REQ = Path('/Users/macintoshhd/Project/Project/stockAI/output/network_hits_foreign.jsonl')
HIT_RESP = Path('/Users/macintoshhd/Project/Project/stockAI/output/network_hits_foreign_resp.jsonl')

KEYWORDS = [
    'data-mt/graphql', 'graphql', 'foreign', 'Foreign', 'ownership', 'ownership/foreign',
    '/iq-insight-service/', '/market-data-service/'
]

def looks_like_foreign_text(txt: str) -> bool:
    if not txt:
        return False
    needles = ['foreign', 'buyVol', 'sellVol', 'netVal', 'netVol', 'nuoc ngoai', 'nước ngoài']
    return any(k.lower() in txt.lower() for k in needles)

def is_hit(url: str, body: str | None) -> bool:
    hay = (url or '') + ' ' + (body or '')
    return any(k in hay for k in KEYWORDS)

async def main():
    # reset logs
    for p in (ALL_REQ, HIT_REQ, HIT_RESP):
        if p.exists():
            p.unlink()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        async def on_request(request):
            rec = {'method': request.method, 'url': request.url}
            try:
                rec['post_data'] = request.post_data
            except Exception:
                rec['post_data'] = None
            with ALL_REQ.open('a') as f:
                f.write(json.dumps(rec, ensure_ascii=False) + '\n')
            if is_hit(rec['url'], rec.get('post_data')):
                with HIT_REQ.open('a') as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + '\n')

        async def on_response(response):
            try:
                url = response.url
                if not any(k in url for k in KEYWORDS):
                    return
                ct = response.headers.get('content-type', '')
                if 'application/json' in ct or 'text' in ct:
                    body = await response.text()
                    if looks_like_foreign_text(body):
                        rec = {
                            'url': url,
                            'status': response.status,
                            'content_type': ct,
                            'body': body[:20000],  # cap for size
                        }
                        with HIT_RESP.open('a') as f:
                            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
            except Exception:
                pass

        page.on('request', on_request)
        page.on('response', on_response)

        await page.goto('https://trading.vietcap.com.vn/iq/company?ticker=PDR&tab=information&informationTab=foreign', wait_until='domcontentloaded')
        print('Capture started. Interact with the page (switch timeframe/scroll). Logs in output/*.jsonl')
        await page.wait_for_timeout(5 * 60 * 1000)
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())



