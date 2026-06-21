"""Track ALL console messages during API call to find JS errors."""
import asyncio, json
from playwright.async_api import async_playwright

TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3MTAxMDVmLTA4ZDUtNGMzZi1iNzA0LTdjZjUwZWM0NmVkNCIsImVtYWlsIjoiYXJqdW4ueW9uemFuQGdtYWlsLmNvbSJ9.DaYGdldHCFsPbofOx11tHr-vo8nRJ5sOFeEBO3HKOBL8rz4CUQz0qi3Mi84RJ4XV62J5hUieuMr1w-Jcdo1inw"

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        console_logs = []
        page.on("console", lambda msg: console_logs.append({"type": msg.type, "text": msg.text, "args": [str(a) for a in msg.args]}))
        page_errors = []
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        await page.goto("https://chat.z.ai", timeout=20000)
        await page.evaluate(f"localStorage.setItem('token', '{TOKEN}')")
        await page.reload(timeout=30000)
        await asyncio.sleep(3)

        # Inject non-blocking interceptor to capture response body
        await page.evaluate("""
            () => {
                window.__chatResponse = null;
                const orig = window.fetch;
                window.fetch = (...args) => {
                    const respPromise = orig(...args);
                    if (typeof args[0] === 'string' && args[0].includes('/chat/completions')) {
                        respPromise.then(resp => {
                            const ct = resp.headers.get('content-type') || '';
                            const clone = resp.clone();
                            clone.text().then(t => { window.__chatResponse = t; }).catch(e => { window.__chatFetchError = e.message; });
                        }).catch(e => { window.__chatFetchError = e.message; });
                    }
                    return respPromise;
                };
            }
        """)

        textarea = await page.wait_for_selector("#chat-input", timeout=5000)
        await textarea.click()
        await page.keyboard.type("Say hello", delay=50)
        await asyncio.sleep(0.2)

        send_btn = await page.query_selector("button[type='submit']:has(svg)")
        if send_btn:
            await send_btn.click()
            print("Sent!")

        # Wait for response
        for i in range(40):
            await asyncio.sleep(1)
            captured = await page.evaluate("window.__chatResponse")
            if captured:
                print(f"  Response captured at {i}s ({len(captured)} bytes)")
                break
        else:
            print("  No response captured")

        # Wait a bit more for DOM to update
        await asyncio.sleep(3)

        # Get DOM state
        dom = await page.evaluate("""
            () => {
                // Find all elements that might contain messages
                const all = document.body.querySelectorAll('div');
                const textContents = [];
                for (const el of all) {
                    const text = (el.textContent || '').trim();
                    if (text.length > 5 && text.length < 300 && !textContents.includes(text)) {
                        // Only collect unique texts from the main area (not sidebar)
                        textContents.push(text);
                    }
                }
                return {
                    url: location.href,
                    htmlSnippet: document.body.innerHTML.substring(0, 5000),
                    uniqueTexts: textContents.slice(0, 30),
                };
            }
        """)

        print("\n=== DOM STATE ===")
        print(f"URL: {dom['url'][-40:]}")
        print(f"Unique texts: {json.dumps(dom['uniqueTexts'], indent=2)}")

        # Show errors and warnings from console
        print(f"\n=== CONSOLE ({len(console_logs)} messages) ===")
        for log in console_logs[-40:]:
            if log['type'] in ('error', 'warning', 'assert'):
                print(f"  [{log['type']}] {log['text'][:150]}")
                for a in log['args'][:3]:
                    print(f"    arg: {a[:200]}")

        if page_errors:
            print(f"\n=== PAGE ERRORS ===")
            for e in page_errors[-5:]:
                print(f"  {e[:300]}")

        # Show captured response
        captured = await page.evaluate("window.__chatResponse")
        if captured:
            print(f"\n=== RESPONSE ({len(captured)} bytes) ===")
            print(captured[:1000])

        await asyncio.sleep(5)
        await browser.close()

asyncio.run(run())
