"""Debug: check all text sources after send."""
import asyncio, json
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

        # Switch to glm-4.7
        btn = await page.wait_for_selector("button.modelSelectorButton", timeout=5000)
        await btn.click()
        await asyncio.sleep(0.5)
        menu = await page.wait_for_selector("[role='menu']", timeout=3000)
        opt = await menu.query_selector("button:has-text('glm-4.7')")
        if opt:
            await opt.click()
            await asyncio.sleep(1)

        # Send
        ta = await page.wait_for_selector("#chat-input", timeout=5000)
        await ta.click()
        await page.keyboard.type("Count from 1 to 5", delay=30)
        btn2 = await page.query_selector("button[type='submit']:has(svg)")
        if btn2:
            await btn2.click()
            print("Sent")

        await asyncio.sleep(15)

        # Collect all text sources
        result = await page.evaluate("""
            () => {
                const r = {};
                r.apiResp = window.__apiResp || null;
                r.bodyText = document.body.innerText;
                r.url = location.href;

                const scroll = document.querySelector('.overflow-y-scroll.flex-col');
                r.scrollText = scroll ? scroll.innerText : 'NO_SCROLL';

                const scroll2 = document.querySelector('[class*=\"overflow-y-scroll\"][class*=\"flex-col\"]');
                r.scrollText2 = scroll2 ? scroll2.innerText : 'NO_SCROLL2';

                const main = document.querySelector('main');
                r.mainText = main ? main.innerText : 'NO_MAIN';

                const chatContainer = document.getElementById('chat-container');
                r.chatText = chatContainer ? chatContainer.innerText : 'NO_CHAT';

                return r;
            }
        """)

        print(f"\nURL: {result['url'][-40:]}")
        print(f"\nAPI Response: {(result['apiResp'] or 'None')[:500]}")
        print(f"\nScroll text: {(result['scrollText'] or '')[-400:]}")
        print(f"\nBody text (last 500): {(result['bodyText'] or '')[-500:]}")
        print(f"\nMain text: {(result['mainText'] or '')[-400:]}")
        print(f"\nChat text: {(result['chatText'] or '')[-400:]}")
        print(f"\nScroll2 text: {(result['scrollText2'] or '')[-400:]}")

        await browser.close()

asyncio.run(run())
