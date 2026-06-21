"""Test glm-4.7 — fresh browser instance."""
import asyncio
from playwright.async_api import async_playwright

TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3MTAxMDVmLTA4ZDUtNGMzZi1iNzA0LTdjZjUwZWM0NmVkNCIsImVtYWlsIjoiYXJqdW4ueW9uemFuQGdtYWlsLmNvbSJ9.DaYGdldHCFsPbofOx11tHr-vo8nRJ5sOFeEBO3HKOBL8rz4CUQz0qi3Mi84RJ4XV62J5hUieuMr1w-Jcdo1inw"

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--no-sandbox"])
        ctx = await browser.new_context()
        page = await ctx.new_page()
        
        try:
            await page.goto("https://chat.z.ai", timeout=30000)
            await page.evaluate(f"localStorage.setItem('token', '{TOKEN}')")
            await page.reload(timeout=30000)
            await asyncio.sleep(4)

            # Switch model
            btn = await page.wait_for_selector("button.modelSelectorButton", timeout=5000)
            await btn.click()
            await asyncio.sleep(0.5)
            menu = await page.wait_for_selector("[role='menu']", timeout=3000)
            opt = await menu.query_selector("button:has-text('glm-4.7')")
            if not opt:
                print("glm-4.7 not found")
                # Try all models
                opts = await menu.evaluate("""el => Array.from(el.querySelectorAll('button')).map(b => (b.textContent||'').trim().slice(0,40))""")
                print(f"Available: {opts}")
                await browser.close()
                return
            await opt.click()
            await asyncio.sleep(1)

            model = await page.evaluate("document.querySelector('button.modelSelectorButton')?.textContent?.trim()")
            print(f"Model: {model}")

            # Interceptor
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

            # Send
            ta = await page.wait_for_selector("#chat-input", timeout=5000)
            await ta.click()
            await page.keyboard.type("Say hi", delay=30)
            btn_send = await page.query_selector("button[type='submit']:has(svg)")
            if btn_send:
                await btn_send.click()
                print("Sent")

            await asyncio.sleep(15)

            cap = await page.evaluate("window.__apiResp")
            text = await page.evaluate("document.body.innerText")
            print("\n=== API RESPONSE ===")
            if cap:
                print(cap[:1500])
                if "MODEL_CONCURRENCY_LIMIT" in cap:
                    print("=> MODEL AT CAPACITY")
                elif "delta_content" in cap:
                    print("=> GOT RESPONSE!")
            else:
                print("None")
            print("\n=== BODY TEXT ===")
            print(text[-600:])

        finally:
            await browser.close()

asyncio.run(run())
