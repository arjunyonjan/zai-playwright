"""Full send+receive test via CDP — let the page handle everything."""
import asyncio, json
from playwright.async_api import async_playwright

TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3MTAxMDVmLTA4ZDUtNGMzZi1iNzA0LTdjZjUwZWM0NmVkNCIsImVtYWlsIjoiYXJqdW4ueW9uemFuQGdtYWlsLmNvbSJ9.DaYGdldHCFsPbofOx11tHr-vo8nRJ5sOFeEBO3HKOBL8rz4CUQz0qi3Mi84RJ4XV62J5hUieuMr1w-Jcdo1inw"

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        intercepted = []
        async def on_request(req):
            url = str(req.url)
            if "/chat/completions" in url:
                intercepted.append({
                    "type": "request",
                    "url": url[:200],
                    "method": req.method,
                    "headers": {k: v for k, v in req.headers.items() if k.lower() in ("x-signature", "content-type", "authorization")},
                    "post_data": (req.post_data or "")[:2000],
                })
        async def on_response(resp):
            url = str(resp.url)
            if "/chat/completions" in url:
                try:
                    body = await resp.text()
                except:
                    body = "(unreadable)"
                intercepted.append({
                    "type": "response",
                    "url": url[:200],
                    "status": resp.status,
                    "headers": dict(resp.headers),
                    "body": body[:3000],
                })

        page.on("request", on_request)
        page.on("response", on_response)

        # Load and auth
        await page.goto("https://chat.z.ai", timeout=20000)
        await page.evaluate(f"localStorage.setItem('token', '{TOKEN}')")
        await page.reload(timeout=30000)
        await asyncio.sleep(3)

        print("Typing message...")
        textarea = await page.wait_for_selector("#chat-input", timeout=5000)
        await textarea.click()
        await page.keyboard.type("Count from 1 to 5", delay=50)
        await asyncio.sleep(0.5)

        # Press Enter to send
        await page.keyboard.press("Enter")
        print("Message sent via Enter key. Waiting for response...")

        # Wait for assistant message in DOM
        for _ in range(90):
            result = await page.evaluate("""
                () => {
                    const msgs = document.querySelectorAll('[data-message-author-role="assistant"]');
                    if (!msgs.length) return {state: 'no_msgs'};
                    const last = msgs[msgs.length - 1];
                    const text = last.textContent || last.innerText || '';
                    const html = last.innerHTML?.substring(0, 500) || '';
                    return {state: text.trim() ? 'done' : 'streaming', text: text.trim().substring(0, 2000), html: html};
                }
            """)
            if result["state"] == "done":
                print(f"\n=== RESPONSE ===\n{result['text']}")
                break
            elif result["state"] == "streaming":
                print(".", end="", flush=True)
            else:
                print(".", end="", flush=True)
            await asyncio.sleep(1)
        else:
            print("\nTimeout - dumping page content")
            body = await page.evaluate("document.body.innerText.substring(0, 2000)")
            print(body[:2000])

        # Print all intercepted traffic
        print(f"\n\n=== INTERCEPTED TRAFFIC ({len(intercepted)} events) ===")
        for item in intercepted:
            print(f"\n--- [{item['type']}] {item['url'][:80]}")
            if item['type'] == 'request':
                print(f"  Headers: {json.dumps(item.get('headers', {}))}")
                print(f"  Body: {(item.get('post_data') or '')[:500]}")
            else:
                print(f"  Status: {item['status']}")
                print(f"  Body: {(item.get('body') or '')[:500]}")

        await asyncio.sleep(5)
        await browser.close()

asyncio.run(run())
