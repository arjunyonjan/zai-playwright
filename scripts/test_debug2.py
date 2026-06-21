"""Check why DOM doesn't render — no interceptor, just monitor console errors."""
import asyncio, json
from playwright.async_api import async_playwright

TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3MTAxMDVmLTA4ZDUtNGMzZi1iNzA0LTdjZjUwZWM0NmVkNCIsImVtYWlsIjoiYXJqdW4ueW9uemFuQGdtYWlsLmNvbSJ9.DaYGdldHCFsPbofOx11tHr-vo8nRJ5sOFeEBO3HKOBL8rz4CUQz0qi3Mi84RJ4XV62J5hUieuMr1w-Jcdo1inw"

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--auto-open-devtools-for-tabs"])
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        # Collect console logs
        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

        # Collect errors
        page_errors = []
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        # Track API (headers only)
        api_req = api_res = None
        async def on_request(req):
            nonlocal api_req
            if "/chat/completions" in req.url:
                api_req = {
                    "url": req.url[:200],
                    "headers": dict(req.headers),
                    "body_keys": list(json.loads(req.post_data).keys()) if req.post_data else [],
                }
        async def on_response(resp):
            nonlocal api_res
            if "/chat/completions" in resp.url:
                api_res = {"status": resp.status, "headers": dict(resp.headers)}
        page.on("request", on_request)
        page.on("response", on_response)

        await page.goto("https://chat.z.ai", timeout=20000)
        await page.evaluate(f"localStorage.setItem('token', '{TOKEN}')")
        await page.reload(timeout=30000)
        await asyncio.sleep(3)
        print(f"URL: {page.url}")

        textarea = await page.wait_for_selector("#chat-input", timeout=5000)
        await textarea.click()
        await page.keyboard.type("Say hello in one word", delay=50)
        await asyncio.sleep(0.2)

        send_btn = await page.query_selector("button[type='submit']:has(svg)")
        if send_btn:
            await send_btn.click()
            print("Sent!")

        # Wait and watch
        for i in range(30):
            await asyncio.sleep(1)
            try:
                msgs = await page.evaluate("""() => {
                    const els = document.querySelectorAll('[data-message-author-role="assistant"]');
                    return els.length ? {count: els.length, text: (els[els.length-1].textContent||'').trim().slice(0,200)} : {count: 0};
                }""")
                # Check URL for any error params
                cur_url = page.url
                print(f"[{i}] msgs:{msgs['count']} url:{cur_url[-30:]}")
                if msgs.get('text'):
                    print(f"  RESPONSE: {msgs['text']}")
                    break
                # Check for any toast/error
                toast = await page.evaluate("""() => {
                    const t = document.querySelector('[role="alert"], .toast, .notification, [class*="Error"], [class*="error"]');
                    return t ? (t.textContent||'').trim().slice(0,200) : '';
                }""")
                if toast:
                    print(f"  TOAST: {toast}")
            except Exception as e:
                print(f"[{i}] Error: {e}")
                break
        else:
            print("No DOM response. Waiting 10s more for logs...")
            await asyncio.sleep(10)
            # Dump page state
            state = await page.evaluate("""() => ({
                url: location.href,
                chats: document.querySelectorAll('[data-message-author-role]').length,
                chatInput: document.querySelector('#chat-input') ? 'exists' : 'missing',
                bodyPreview: document.body.innerText.slice(0, 500),
                htmlPreview: document.body.innerHTML.slice(0, 1000),
            })""")
            print(json.dumps(state, indent=2)[:2000])

        print(f"\n=== CONSOLE LOGS ({len(console_logs)}) ===")
        # Show errors and warnings
        for log in console_logs[-30:]:
            if 'error' in log.lower() or 'warn' in log.lower() or 'captcha' in log.lower() or 'fail' in log.lower():
                print(f"  {log[:200]}")
        
        if page_errors:
            print(f"\n=== PAGE ERRORS ({len(page_errors)}) ===")
            for e in page_errors[-5:]:
                print(f"  {e[:300]}")

        if api_req:
            print(f"\n=== API REQ ===")
            print(f"  X-Signature: {api_req['headers'].get('x-signature','')[:40]}")
            print(f"  Body keys: {api_req['body_keys']}")
        if api_res:
            print(f"\n=== API RES ({api_res['status']}) ===")
            print(f"  Content-Type: {api_res['headers'].get('content-type','')}")
            print(f"  x-request-id: {api_res['headers'].get('x-request-id','N/A')}")

        await asyncio.sleep(5)
        await browser.close()

asyncio.run(run())
