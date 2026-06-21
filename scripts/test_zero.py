"""Test with zero (Z1-32B) model."""
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

        # Switch to zero (Z1-32B)
        btn = await page.wait_for_selector("button.modelSelectorButton", timeout=5000)
        await btn.click()
        await asyncio.sleep(0.5)
        menu = await page.wait_for_selector("[role='menu']", timeout=3000)
        opt = await menu.query_selector("button:has-text('zero')")
        if not opt:
            opt = await menu.query_selector("button:has-text('Z1')")
        if opt:
            await opt.click()
            await asyncio.sleep(1)
            model = await page.evaluate("document.querySelector('button.modelSelectorButton')?.textContent?.trim()")
            print(f"Model: {model}")
        else:
            items = await menu.evaluate("el => Array.from(el.querySelectorAll('button')).map(b => (b.textContent||'').trim().slice(0,40))")
            print(f"Items: {items}")
            await browser.close()
            return

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

        ta = await page.wait_for_selector("#chat-input", timeout=5000)
        await ta.click()
        await page.keyboard.type("Count from 1 to 3", delay=30)
        btn2 = await page.query_selector("button[type='submit']:has(svg)")
        if btn2:
            await btn2.click()
            print("Sent")

        await asyncio.sleep(15)

        cap = await page.evaluate("window.__apiResp")
        text = await page.evaluate("document.body.innerText")
        sc_text = await page.evaluate("document.querySelector('.overflow-y-scroll.flex-col')?.innerText || ''")

        print("\n=== API ===")
        if cap:
            if "MODEL_CONCURRENCY_LIMIT" in cap:
                print("AT CAPACITY")
            elif "delta_content" in cap:
                print("GOT RESPONSE!")
            print(cap[:500])
        else:
            print("None")

        print("\n=== SCROLL CONTAINER ===")
        print(sc_text[-400:])

        await browser.close()

asyncio.run(run())
