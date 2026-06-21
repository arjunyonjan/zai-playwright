"""Check main element innerText for response."""
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

        # Change to glm-4.7
        btn = await page.wait_for_selector("button.modelSelectorButton", timeout=5000)
        await btn.click(); await asyncio.sleep(0.5)
        menu = await page.wait_for_selector("[role='menu']", timeout=3000)
        opt = await menu.query_selector("button:has-text('glm-4.7')")
        if opt: await opt.click(); await asyncio.sleep(1)

        # Send
        ta = await page.wait_for_selector("#chat-input", timeout=5000)
        await ta.click(); await page.keyboard.type("Say hi", delay=30)
        btn = await page.query_selector("button[type='submit']:has(svg)")
        if btn: await btn.click(); print("Sent")

        await asyncio.sleep(15)

        # Check ALL possible text sources
        result = await page.evaluate("""
            () => {
                const sources = {
                    bodyInnerText: document.body.innerText,
                    bodyTextContent: document.body.textContent,
                    main: null,
                    scrollContainer: null,
                    chatContainer: null,
                    allDivs: []
                };
                const main = document.querySelector('main');
                if (main) sources.main = main.innerText;

                const scroll = document.querySelector('.overflow-y-scroll.flex-col');
                if (scroll) sources.scrollContainer = scroll.innerText;

                const chat = document.getElementById('chat-container');
                if (chat) sources.chatContainer = chat.innerText;

                // Collect unique multi-word texts > 5 chars
                const all = document.querySelectorAll('div');
                const texts = new Set();
                for (const el of all) {
                    const t = (el.textContent||'').trim();
                    if (t.length > 5 && t.length < 200) texts.add(t);
                }
                sources.allDivs = Array.from(texts).slice(0, 50);
                return sources;
            }
        """)

        for key, val in result.items():
            if isinstance(val, str):
                if "Hi there" in val or "hello" in val.lower():
                    print(f"\n>>> FOUND in '{key}':")
                    print(val[-500:])
            elif isinstance(val, list):
                for item in val:
                    if "Hi there" in item or "hello" in item.lower():
                        print(f">>> FOUND in div: {item}")

        print("\n=== ALL DIV TEXTS ===")
        for t in result.get('allDivs', []):
            print(f"  {t[:80]}")

        await browser.close()

asyncio.run(run())
