"""Test send via clicking submit button, handle SPA navigation."""
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
                    "type": "request", "url": url[:200],
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
                    "type": "response", "url": url[:200],
                    "status": resp.status, "body": body[:3000],
                })
        page.on("request", on_request)
        page.on("response", on_response)

        await page.goto("https://chat.z.ai", timeout=20000)
        await page.evaluate(f"localStorage.setItem('token', '{TOKEN}')")
        await page.reload(timeout=30000)
        await asyncio.sleep(3)
        print(f"URL: {page.url}")

        # Type and click send
        textarea = await page.wait_for_selector("#chat-input", timeout=5000)
        await textarea.click()
        await page.keyboard.type("Count from 1 to 5", delay=50)
        await asyncio.sleep(0.3)

        send_btn = await page.query_selector("button[type='submit']:has(svg)")
        if send_btn:
            disabled = await send_btn.get_attribute("disabled")
            print(f"Send button disabled attr: {disabled}")
            if disabled is None:
                await send_btn.click()
                print("Clicked send button")
            else:
                await page.keyboard.press("Enter")
                print("Pressed Enter")
        else:
            await page.keyboard.press("Enter")
            print("Pressed Enter (no button)")

        # Wait and check for URL change or new content
        for i in range(60):
            await asyncio.sleep(1)
            try:
                cur_url = page.url
                has_msgs = await page.evaluate("document.querySelectorAll('[data-message-author-role=\"assistant\"]').length")
                body_text = await page.evaluate("document.body.innerText.substring(0, 300)")
                print(f"  [{i}] URL: {cur_url[-40:]} | msgs: {has_msgs} | body: {body_text[:100].replace(chr(10), ' ')}")

                if has_msgs > 0:
                    text = await page.evaluate("""
                        () => {
                            const last = document.querySelectorAll('[data-message-author-role="assistant"]');
                            const t = last[last.length-1].textContent || '';
                            return {trimmed: t.trim().substring(0, 2000), raw: t.substring(0, 2000)};
                        }
                    """)
                    if text["trimmed"]:
                        print(f"\n=== RESPONSE ===\n{text['raw']}")
                        break
            except Exception as e:
                print(f"  [{i}] Error: {e}")
                break
        else:
            print("\nTimeout")

        # Print intercepted traffic
        print(f"\n=== INTERCEPTED ({len(intercepted)} events) ===")
        for item in intercepted:
            if item['type'] == 'request':
                print(f"\n[REQ] {item['url'][:80]}")
                print(f"  X-Signature: {item['headers'].get('x-signature', 'N/A')}")
                print(f"  Body keys: {list(json.loads(item['post_data']).keys()) if item['post_data'] else 'N/A'}")
            else:
                print(f"\n[RES] {item['url'][:80]} -> {item['status']}")
                body = item.get('body', '')
                if body and body != '(unreadable)':
                    print(f"  Body: {body[:500]}")

        await asyncio.sleep(5)
        await browser.close()

asyncio.run(run())
