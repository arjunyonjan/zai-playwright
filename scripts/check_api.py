"""Check captured API response and body text."""
import asyncio
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

        await page.evaluate("""
            () => {
                window.__apiResp = null;
                const orig = fetch;
                fetch = (...args) => {
                    const p = orig(...args);
                    if (typeof args[0] === 'string' && args[0].includes('/chat/completions')) {
                        p.then(r => {
                            const clone = r.clone();
                            clone.text().then(t => { window.__apiResp = t; }).catch(() => {});
                        }).catch(() => {});
                    }
                    return p;
                };
            }
        """)

        ta = await page.wait_for_selector("#chat-input", timeout=5000)
        await ta.click()
        await page.keyboard.type("Say hi", delay=30)
        btn = await page.query_selector("button[type='submit']:has(svg)")
        if btn:
            await btn.click()

        await asyncio.sleep(10)
        cap = await page.evaluate("window.__apiResp")
        text = await page.evaluate("document.body.innerText")
        print("=== API RESPONSE ===")
        print(cap[:1500] if cap else "None")
        print("\n=== BODY TEXT (last 500) ===")
        print(text[-500:])
        await browser.close()

asyncio.run(run())
