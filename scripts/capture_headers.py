"""Intercept a real UI chat request to see headers."""
import asyncio, json
from playwright.async_api import async_playwright

TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3MTAxMDVmLTA4ZDUtNGMzZi1iNzA0LTdjZjUwZWM0NmVkNCIsImVtYWlsIjoiYXJqdW4ueW9uemFuQGdtYWlsLmNvbSJ9.DaYGdldHCFsPbofOx11tHr-vo8nRJ5sOFeEBO3HKOBL8rz4CUQz0qi3Mi84RJ4XV62J5hUieuMr1w-Jcdo1inw"

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})

        # Intercept BEFORE loading page (to catch wrapped fetch headers)
        chat_req = None
        async def on_request(req):
            nonlocal chat_req
            if 'chat/completions' in req.url:
                chat_req = {
                    'url': req.url,
                    'method': req.method,
                    'headers': dict(req.headers),
                    'post_data': req.post_data,
                }
        page.on('request', on_request)

        await page.goto("https://chat.z.ai", timeout=30000)
        await page.evaluate(f"localStorage.setItem('token', '{TOKEN}')")
        await page.reload(timeout=30000)
        await asyncio.sleep(3)

        # Type and send via UI
        ta = await page.wait_for_selector("#chat-input", timeout=5000)
        await ta.click()
        await ta.fill("hi")
        await asyncio.sleep(0.3)
        send_btn = await page.query_selector("button[type='submit']:has(svg)")
        if send_btn:
            await send_btn.click()
            print("Sent from UI, waiting 8s...")
            await asyncio.sleep(8)

        # Try one more from page context
        if not chat_req:
            print("UI request not captured, trying page fetch...")
            # Unwrap page's fetch wrapper and get original headers
            hdrs = await page.evaluate("""
                async () => {
                    const orig = window.fetch;
                    let captured = null;
                    window.fetch = (...args) => {
                        captured = {
                            url: args[0],
                            headers: Object.fromEntries(
                                new Headers(args[1]?.headers || (args[0] instanceof Request ? args[0].headers : {})).entries()
                            ),
                            body: args[1]?.body || null,
                        };
                        return orig(...args);
                    };
                    const ta2 = document.querySelector('#chat-input');
                    if (ta2) {
                        const nativeSetter = Object.getOwnPropertyDescriptor(
                            window.HTMLTextAreaElement.prototype, 'value'
                        ).set;
                        nativeSetter.call(ta2, 'hello2');
                        ta2.dispatchEvent(new Event('input', {bubbles: true}));
                        await new Promise(r => setTimeout(r, 200));
                        const btn2 = document.querySelector("button[type='submit']:has(svg)");
                        if (btn2) btn2.click();
                        await new Promise(r => setTimeout(r, 5000));
                    }
                    window.fetch = orig;
                    return captured;
                }
            """)
            if hdrs:
                chat_req = hdrs

        if chat_req:
            print(f"\n=== CHAT REQUEST ===")
            print(f"URL: {chat_req.get('url', '')}")
            print(f"Method: {chat_req.get('method', '')}")
            print(f"Headers:")
            for k, v in (chat_req.get('headers') or {}).items():
                print(f"  {k}: {v}")
            body = chat_req.get('post_data') or chat_req.get('body', '')
            if body:
                try:
                    parsed = json.loads(body)
                    print(f"Body (parsed): {json.dumps(parsed, indent=2)[:2000]}")
                except:
                    print(f"Body (raw): {body[:500]}")
        else:
            print("No request captured")

        await browser.close()

asyncio.run(run())
