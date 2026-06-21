"""Test changing model via dropdown."""
import asyncio, json
from playwright.async_api import async_playwright

TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3MTAxMDVmLTA4ZDUtNGMzZi1iNzA0LTdjZjUwZWM0NmVkNCIsImVtYWlsIjoiYXJqdW4ueW9uemFuQGdtYWlsLmNvbSJ9.DaYGdldHCFsPbofOx11tHr-vo8nRJ5sOFeEBO3HKOBL8rz4CUQz0qi3Mi84RJ4XV62J5hUieuMr1w-Jcdo1inw"

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://chat.z.ai", timeout=20000)
        await page.evaluate(f"localStorage.setItem('token', '{TOKEN}')")
        await page.reload(timeout=30000)
        await asyncio.sleep(3)

        current = await page.evaluate("document.querySelector('button.modelSelectorButton')?.textContent?.trim()")
        print(f"Current model: {current}")

        # Click and change to glm-4.7
        btn = await page.wait_for_selector("button.modelSelectorButton", timeout=5000)
        await btn.click()
        await asyncio.sleep(0.5)

        menu = await page.wait_for_selector("[role='menu']", timeout=3000)
        option = await menu.query_selector("button:has-text('glm-4.7')")
        if option:
            await option.click()
            await asyncio.sleep(1)
            new_current = await page.evaluate("document.querySelector('button.modelSelectorButton')?.textContent?.trim()")
            print(f"New model: {new_current}")
        else:
            print("Could not find glm-4.7 option")
            # Show what's in the menu
            items = await menu.evaluate("""
                el => Array.from(el.querySelectorAll('button')).map(b => ({
                    text: (b.textContent||'').trim().slice(0, 80),
                    id: b.id,
                }))
            """)
            print("Menu items:", json.dumps(items, indent=2))

        await browser.close()

asyncio.run(run())
