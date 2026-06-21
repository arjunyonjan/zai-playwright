"""Quick one-shot test with model change."""
import asyncio, json, sys
from playwright.async_api import async_playwright

TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3MTAxMDVmLTA4ZDUtNGMzZi1iNzA0LTdjZjUwZWM0NmVkNCIsImVtYWlsIjoiYXJqdW4ueW9uemFuQGdtYWlsLmNvbSJ9.DaYGdldHCFsPbofOx11tHr-vo8nRJ5sOFeEBO3HKOBL8rz4CUQz0qi3Mi84RJ4XV62J5hUieuMr1w-Jcdo1inw"

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        await page.goto("https://chat.z.ai", timeout=20000)
        await page.evaluate(f"localStorage.setItem('token', '{TOKEN}')")
        await page.reload(timeout=30000)
        await asyncio.sleep(3)
        print("1. Page loaded")

        # Switch to glm-4.7
        btn = await page.wait_for_selector("button.modelSelectorButton", timeout=5000)
        await btn.click()
        await asyncio.sleep(0.5)
        menu = await page.wait_for_selector("[role='menu']", timeout=3000)
        opt = await menu.query_selector("button:has-text('glm-4.7')")
        if opt:
            await opt.click()
            await asyncio.sleep(0.5)
            model = await page.evaluate("document.querySelector('button.modelSelectorButton')?.textContent?.trim()")
            print(f"2. Model: {model}")
        else:
            print("2. Model switch failed")
            return

        # Send message
        textarea = await page.wait_for_selector("#chat-input", timeout=5000)
        await textarea.click()
        await page.keyboard.type("Say hello in one word", delay=30)
        await asyncio.sleep(0.3)
        send_btn = await page.query_selector("button[type='submit']:has(svg)")
        if send_btn:
            await send_btn.click()
            print("3. Sent")

        # Wait for response
        for i in range(30):
            await asyncio.sleep(1)
            text = await page.evaluate("document.body.innerText")
            if "hello" in text.lower() or "Hello" in text:
                idx = text.find("Say hello in one word")
                if idx >= 0:
                    after = text[idx + len("Say hello in one word"):].strip()
                    print(f"4. Response: {after[:200]}")
                    break
            # Check for error
            if any(kw in text.lower() for kw in ["capacity", "concurrency"]):
                print(f"4. Model at capacity")
                break
            if i == 15:
                print(f"4. No response yet... text: {text[-200:]}")
        else:
            print("4. Timeout")

        await asyncio.sleep(3)
        await browser.close()

asyncio.run(run())
