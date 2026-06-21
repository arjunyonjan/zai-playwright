"""Test model selector dropdown."""
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

        # Click model selector
        btn = await page.wait_for_selector("#model-selector-glm-5_2-button", timeout=5000)
        await btn.click()
        await asyncio.sleep(1)

        # Find dropdown items
        info = await page.evaluate("""
            () => {
                // Find all newly visible elements
                const all = document.querySelectorAll('*');
                const dropdownItems = [];
                for (const el of all) {
                    const text = (el.textContent||'').trim();
                    if (text && (text.includes('GLM') || text.includes('glm') || text.includes('zero'))) {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 50 && rect.height > 10) {
                            dropdownItems.push({
                                tag: el.tagName,
                                text: text.slice(0, 40),
                                id: el.id,
                                class: (el.className||'').slice(0, 60),
                                role: el.getAttribute('role') || '',
                                rect: `${rect.width}x${rect.height}`,
                            });
                        }
                    }
                }
                return dropdownItems.slice(0, 20);
            }
        """)
        print("Dropdown items:", json.dumps(info, indent=2))

        await browser.close()

asyncio.run(run())
