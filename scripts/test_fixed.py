"""Fixed interceptor — don't block return, read clone asynchronously."""
import asyncio, json
from playwright.async_api import async_playwright

TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3MTAxMDVmLTA4ZDUtNGMzZi1iNzA0LTdjZjUwZWM0NmVkNCIsImVtYWlsIjoiYXJqdW4ueW9uemFuQGdtYWlsLmNvbSJ9.DaYGdldHCFsPbofOx11tHr-vo8nRJ5sOFeEBO3HKOBL8rz4CUQz0qi3Mi84RJ4XV62J5hUieuMr1w-Jcdo1inw"

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        api_req = {}
        async def on_request(req):
            if "/chat/completions" in req.url and "/api/v1/chats" not in req.url:
                try:
                    api_req["body"] = json.loads(req.post_data) if req.post_data else {}
                    api_req["headers"] = dict(req.headers)
                except: pass
        page.on("request", on_request)

        await page.goto("https://chat.z.ai", timeout=20000)
        await page.evaluate(f"localStorage.setItem('token', '{TOKEN}')")
        await page.reload(timeout=30000)
        await asyncio.sleep(3)

        # Inject fixed interceptor — returns immediately, reads clone in background
        await page.evaluate("""
            () => {
                window.__chatResponse = null;
                const orig = window.fetch;
                window.fetch = (...args) => {
                    const respPromise = orig(...args);
                    if (typeof args[0] === 'string' && args[0].includes('/chat/completions')) {
                        respPromise.then(resp => {
                            const clone = resp.clone();
                            clone.text().then(t => { window.__chatResponse = t; }).catch(() => {});
                        });
                    }
                    return respPromise;
                };
            }
        """)

        textarea = await page.wait_for_selector("#chat-input", timeout=5000)
        await textarea.click()
        await page.keyboard.type("Say hello in one word", delay=50)
        await asyncio.sleep(0.2)

        send_btn = await page.query_selector("button[type='submit']:has(svg)")
        if send_btn:
            await send_btn.click()
            print("Sent!")

        # Wait for DOM response OR captured body
        for i in range(40):
            await asyncio.sleep(1)
            try:
                state = await page.evaluate("""
                    () => {
                        // Check DOM for messages
                        const domMsgs = document.querySelectorAll('[class*="message"]');
                        // Check for any element containing "Hello" after the user message
                        const allDivs = document.querySelectorAll('div');
                        let responseText = '';
                        for (const d of allDivs) {
                            const t = (d.textContent || '').trim();
                            // Look for markers of response area
                            if (d.hasAttribute('data-message-type') || d.getAttribute('role') === 'message') {
                                responseText = t.substring(0, 200);
                                break;
                            }
                        }
                        return {
                            domMsgCount: domMsgs.length,
                            responseText,
                            bodySnippet: document.body.innerText.substring(0, 400),
                            captured: window.__chatResponse || null,
                        };
                    }
                """)
                
                print(f"[{i}] domMsgs:{state['domMsgCount']} cap:{bool(state['captured'])}")
                
                if state['captured']:
                    cap = state['captured']
                    print(f"  CAPTURED ({len(cap)} bytes): {cap[:200]}")
                    break
                    
                if state['responseText']:
                    print(f"  DOM: {state['responseText']}")
                    break
            except Exception as e:
                print(f"[{i}] Error: {e}")
                break
        else:
            print("Timeout")

        # Print final captured response if any
        final = await page.evaluate("window.__chatResponse")
        if final:
            print(f"\n=== FULL RESPONSE ({len(final)} bytes) ===\n{final[:2000]}")

        # Print request details
        if api_req:
            print(f"\n=== REQUEST BODY ===")
            print(json.dumps({k: v for k, v in api_req.get('body', {}).items() if k in ('model', 'stream', 'messages', 'signature_prompt', 'captcha_verify_param')}, indent=2)[:500])

        await asyncio.sleep(10)
        await browser.close()

asyncio.run(run())
