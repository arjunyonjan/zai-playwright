"""Minimal test: no interceptor, verify rendering."""
import asyncio
from playwright.async_api import async_playwright

TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3MTAxMDVmLTA4ZDUtNGMzZi1iNzA0LTdjZjUwZWM0NmVkNCIsImVtYWlsIjoiYXJqdW4ueW9uemFuQGdtYWlsLmNvbSJ9.DaYGdldHCFsPbofOx11tHr-vo8nRJ5sOFeEBO3HKOBL8rz4CUQz0qi3Mi84RJ4XV62J5hUieuMr1w-Jcdo1inw"

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://chat.z.ai", timeout=30000)
        await page.evaluate(f"localStorage.setItem('token', '{TOKEN}')")
        await page.reload(timeout=30000)
        await asyncio.sleep(4)

        ta = await page.wait_for_selector("#chat-input", timeout=5000)
        await ta.click()
        await page.keyboard.type("Count from 1 to 3", delay=30)
        btn = await page.query_selector("button[type='submit']:has(svg)")
        if btn:
            await btn.click()
            print("Sent, waiting 20s...")

        # Poll DOM every 2s
        for i in range(10):
            await asyncio.sleep(2)
            sc = await page.evaluate("document.querySelector('.overflow-y-scroll.flex-col')?.innerText || ''")
            body = await page.evaluate("document.body.innerText")
            url = page.url
            print(f"\n[{i*2}s] URL: {url[-30:]}")
            msg_idx = body.find("Count from 1 to 3")
            print(f"  body.indexOf(msg) = {msg_idx}")
            print(f"  scroll text ({len(sc)} chars):")
            for line in sc.split("\n")[-10:]:
                print(f"    [{line[:80]}]")
            if "Count" not in body:
                print("  WARNING: message not in body!")
            if sc and len(sc) > 50:
                print("\n  === DETECTED FULL RESPONSE ===")
                for line in sc.split("\n"):
                    if line.strip() and "Count from" not in line and "Thought" not in line:
                        print(f"  >> {line[:120]}")
                break

        await browser.close()

asyncio.run(run())
