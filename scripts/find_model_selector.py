"""Find model selector UI element."""
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

        info = await page.evaluate("""
            () => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const modelBtns = buttons.filter(b =>
                    (b.textContent||'').includes('GLM') ||
                    (b.textContent||'').includes('glm')
                );
                return modelBtns.map(b => ({
                    text: (b.textContent||'').trim().slice(0, 40),
                    id: b.id,
                    class: (b.className||'').slice(0, 80),
                    rect: (r => r ? r.width+'x'+r.height : '?')(b.getBoundingClientRect()),
                }));
            }
        """)
        print("Model buttons:", json.dumps(info, indent=2))

        await browser.close()

asyncio.run(run())
