"""Quick test to verify page loads and chat-input exists."""
import asyncio
from playwright.async_api import async_playwright

TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3MTAxMDVmLTA4ZDUtNGMzZi1iNzA0LTdjZjUwZWM0NmVkNCIsImVtYWlsIjoiYXJqdW4ueW9uemFuQGdtYWlsLmNvbSJ9.DaYGdldHCFsPbofOx11tHr-vo8nRJ5sOFeEBO3HKOBL8rz4CUQz0qi3Mi84RJ4XV62J5hUieuMr1w-Jcdo1inw"

async def run():
    print("1. Starting...")
    async with async_playwright() as p:
        print("2. Playwright started")
        browser = await p.chromium.launch(headless=False)
        print("3. Browser launched")
        page = await browser.new_page()
        print("4. Page created")
        await page.goto("https://chat.z.ai", timeout=20000)
        print("5. First goto done")
        await page.evaluate(f"localStorage.setItem('token', '{TOKEN}')")
        print("6. Token set")
        await page.reload(timeout=30000)
        print("7. Reloaded")
        await asyncio.sleep(3)
        print("8. Waited 3s")
        title = await page.evaluate("document.title")
        has_input = await page.evaluate("!!document.querySelector('#chat-input')")
        print(f"9. Title: {title} | Has #chat-input: {has_input}")
        await asyncio.sleep(2)
        await browser.close()
        print("10. Done")

asyncio.run(run())
