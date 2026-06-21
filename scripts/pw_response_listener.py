"""Playwright response listener — no JS interference."""
import asyncio
from playwright.async_api import async_playwright

TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3MTAxMDVmLTA4ZDUtNGMzZi1iNzA0LTdjZjUwZWM0NmVkNCIsImVtYWlsIjoiYXJqdW4ueW9uemFuQGdtYWlsLmNvbSJ9.DaYGdldHCFsPbofOx11tHr-vo8nRJ5sOFeEBO3HKOBL8rz4CUQz0qi3Mi84RJ4XV62J5hUieuMr1w-Jcdo1inw"

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})

        # Set up response listener (CDP level, no JS interference)
        chat_response = None
        chat_response_event = asyncio.Event()

        async def on_response(response):
            nonlocal chat_response
            if '/api/v2/chat/completions' in response.url:
                chat_response = response
                chat_response_event.set()

        page.on('response', on_response)

        await page.goto("https://chat.z.ai", timeout=30000)
        await page.evaluate(f"localStorage.setItem('token', '{TOKEN}')")
        await page.reload(timeout=30000)
        await asyncio.sleep(3)

        ta = await page.wait_for_selector("#chat-input", timeout=5000)
        await ta.click()
        await ta.fill("Count from 1 to 5")
        await asyncio.sleep(0.3)
        send_btn = await page.query_selector("button[type='submit']:has(svg)")
        await send_btn.click()
        print("Sent, waiting for response...")

        try:
            await asyncio.wait_for(chat_response_event.wait(), timeout=60)
        except asyncio.TimeoutError:
            print("Timeout waiting for response")
            await browser.close()
            return

        status = chat_response.status
        url = chat_response.url
        print(f"Response: HTTP {status}, URL: {url[:80]}...")

        body = await chat_response.text()
        print(f"Body ({len(body)} bytes)")

        # Parse SSE
        answer = ''
        for line in body.split('\n'):
            if line.startswith('data: ') and line != 'data: [DONE]':
                import json
                try:
                    ev = json.loads(line[6:])
                    if ev.get('type') == 'chat:completion':
                        answer += ev['data'].get('delta_content', '')
                except:
                    pass

        if answer:
            print(f"\n=== ANSWER ===\n{answer[:1000]}")
        else:
            print(f"\n=== RAW BODY ===\n{body[:800]}")

        await browser.close()

asyncio.run(run())
