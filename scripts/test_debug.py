"""Fixed — inject fetch interceptor AFTER reload, don't read response body in Python handler."""
import asyncio, json
from playwright.async_api import async_playwright

TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3MTAxMDVmLTA4ZDUtNGMzZi1iNzA0LTdjZjUwZWM0NmVkNCIsImVtYWlsIjoiYXJqdW4ueW9uemFuQGdtYWlsLmNvbSJ9.DaYGdldHCFsPbofOx11tHr-vo8nRJ5sOFeEBO3HKOBL8rz4CUQz0qi3Mi84RJ4XV62J5hUieuMr1w-Jcdo1inw"

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        # Track API calls via Playwright (headers only, NOT reading body)
        req_data = res_data = None
        async def on_request(req):
            nonlocal req_data
            if "/chat/completions" in req.url:
                req_data = {
                    "url": req.url[:200],
                    "headers": dict(req.headers),
                    "post_data": (req.post_data or "")[:3000],
                }
        async def on_response(resp):
            nonlocal res_data
            if "/chat/completions" in resp.url:
                res_data = {
                    "status": resp.status,
                    "headers": dict(resp.headers),
                }
        page.on("request", on_request)
        page.on("response", on_response)

        # Load and auth
        await page.goto("https://chat.z.ai", timeout=20000)
        await page.evaluate(f"localStorage.setItem('token', '{TOKEN}')")
        await page.reload(timeout=30000)
        await asyncio.sleep(3)
        print(f"URL: {page.url}")

        # Inject fetch interceptor AFTER reload
        await page.evaluate("""
            () => {
                window.__chatResponseBody = null;
                const orig = window.fetch;
                window.fetch = async (...args) => {
                    const resp = await orig(...args);
                    if (args[0] && typeof args[0] === 'string' && args[0].includes('/chat/completions')) {
                        const ct = resp.headers.get('content-type') || '';
                        const clone = resp.clone();
                        if (ct.includes('text/event-stream') || ct.includes('text/plain')) {
                            // Streaming — collect chunks
                            const reader = clone.body.getReader();
                            const decoder = new TextDecoder();
                            let text = '';
                            while (true) {
                                const {done, value} = await reader.read();
                                if (done) break;
                                text += decoder.decode(value, {stream: true});
                            }
                            window.__chatResponseBody = text;
                        } else {
                            clone.text().then(t => { window.__chatResponseBody = t; }).catch(() => {});
                        }
                    }
                    return resp;
                };
            }
        """)

        # Type and send
        textarea = await page.wait_for_selector("#chat-input", timeout=5000)
        await textarea.click()
        await page.keyboard.type("Say 'hello' in one word", delay=50)
        await asyncio.sleep(0.3)

        send_btn = await page.query_selector("button[type='submit']:has(svg)")
        if send_btn:
            await send_btn.click()
            print("Clicked send")

        # Wait and monitor
        for i in range(40):
            await asyncio.sleep(1)
            try:
                body_snippet = await page.evaluate("document.body.innerText.substring(0, 300)")
                msgs = await page.evaluate("""
                    () => {
                        const els = document.querySelectorAll('[data-message-author-role="assistant"]');
                        return {
                            count: els.length,
                            text: els.length ? (els[els.length-1].textContent || '').trim().substring(0, 500) : ''
                        };
                    }
                """)
                captured = await page.evaluate("typeof window.__chatResponseBody === 'string' ? window.__chatResponseBody.substring(0, 1000) : null")
                error_toasts = await page.evaluate("""
                    () => {
                        const errEls = document.querySelectorAll('[role="alert"], .toast-error, .message-error, .captcha-error, [class*="error"]');
                        return Array.from(errEls).map(e => (e.textContent || '').trim()).filter(Boolean).join(' | ');
                    }
                """)

                status = f"msgs:{msgs['count']} cap:{bool(captured)} err:'{error_toasts[:60]}'"
                print(f"[{i}] {status}")
                
                if msgs['text']:
                    print(f"  DOM RESPONSE: {msgs['text']}")
                    break
                if captured and '"choices"' in captured:
                    print(f"  API RESPONSE: {captured[:500]}")
                    break
                if captured and 'error' in captured.lower():
                    print(f"  API ERROR: {captured[:500]}")
                    break
            except Exception as e:
                print(f"[{i}] Error: {e}")
                break
        else:
            print("\nTimeout")

        # Print API details
        if req_data:
            print(f"\n=== REQUEST ===")
            print(f"X-Signature: {req_data['headers'].get('x-signature', 'N/A')}")
            print(f"Content-Type: {req_data['headers'].get('content-type', 'N/A')}")
            try:
                body = json.loads(req_data['post_data'])
                print(f"Model: {body.get('model')}")
                print(f"Has captcha: {'captcha_verify_param' in body}")
            except:
                print(f"Raw body: {req_data['post_data'][:200]}")
        if res_data:
            print(f"\n=== RESPONSE ({res_data['status']}) ===")
            h = res_data['headers']
            print(f"Content-Type: {h.get('content-type', 'N/A')}")
            print(f"x-request-id: {h.get('x-request-id', 'N/A')}")

        # Print captured response
        final_captured = await page.evaluate("window.__chatResponseBody || '(not captured)'")
        print(f"\n=== CAPTURED BODY ===\n{final_captured[:2000]}")

        await asyncio.sleep(10)
        await browser.close()

asyncio.run(run())
