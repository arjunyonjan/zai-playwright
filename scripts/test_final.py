"""Final verification — print full response text from DOM."""
import asyncio, json
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

        textarea = await page.wait_for_selector("#chat-input", timeout=5000)
        await textarea.click()
        await page.keyboard.type("Count from 1 to 5", delay=50)
        await asyncio.sleep(0.2)
        send_btn = await page.query_selector("button[type='submit']:has(svg)")
        if send_btn: await send_btn.click()

        # Wait for main content to have both user msg and response
        prev_text = ""
        for i in range(60):
            await asyncio.sleep(1)
            try:
                text = await page.evaluate("""
                    () => {
                        const main = document.querySelector('main') || document.querySelector('[class*=\"overflow-y-scroll\"]') || document.body;
                        const t = main.innerText || '';
                        // Find the user message and what follows
                        const idx = t.lastIndexOf('Count from 1 to 5');
                        if (idx >= 0) {
                            const after = t.substring(idx + 'Count from 1 to 5'.length).trim();
                            if (after && after.length > 5) return {found: true, text: t, after: after.substring(0, 1000)};
                        }
                        return {found: false, text: t.substring(Math.max(0, t.length-300))};
                    }
                """)
                if text.get('found'):
                    print(f"\n=== FULL CHAT ===\n{text['text']}")
                    print(f"\n=== RESPONSE TEXT ===\n{text['after']}")
                    break
            except:
                pass
        else:
            print("Timeout")

        await asyncio.sleep(3)
        await browser.close()

asyncio.run(run())
