"""Z.ai chat — robust response reading from scroll container."""
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
        if send_btn:
            await send_btn.click()
            print("Sent!")

        # Wait for response in the scroll container (found from earlier DOM analysis)
        for i in range(60):
            await asyncio.sleep(1)
            try:
                result = await page.evaluate("""
                    () => {
                        // Find the message scroll container
                        const scrollContainer = document.querySelector('.overflow-y-scroll.flex-col');
                        if (!scrollContainer) return {state: 'no_container'};
                        
                        const text = scrollContainer.innerText || '';
                        
                        // Find all direct message-like children
                        const messages = scrollContainer.querySelectorAll(':scope > div > div');
                        const msgs = Array.from(messages).map(el => ({
                            class: (el.className || '').slice(0, 60),
                            text: (el.textContent || '').trim().slice(0, 200),
                        })).filter(m => m.text.length > 3);
                        
                        return {
                            state: msgs.length > 0 ? 'has_messages' : 'empty',
                            messages: msgs,
                            containerText: text.slice(0, 500),
                            containerClass: (scrollContainer.className || '').slice(0, 100),
                        };
                    }
                """)
                
                if i == 0 or result.get('state') == 'has_messages':
                    print(f"[{i}] {json.dumps(result, indent=2)[:500]}")
                    
                if result.get('state') == 'has_messages':
                    msgs = result.get('messages', [])
                    # Last message that doesn't look like UI text is the response
                    for m in reversed(msgs):
                        txt = m['text']
                        if not any(kw in txt for kw in ['Chat', 'Agent', 'New Chat', 'AI PPT', 'Loading', 'New product']):
                            if len(txt) > 3 and txt != 'Count from 1 to 5':
                                print(f"\n=== RESPONSE FOUND ===\n{txt}")
                                break
            except Exception as e:
                print(f"[{i}] Error: {e}")

        await asyncio.sleep(5)
        await browser.close()

asyncio.run(run())
