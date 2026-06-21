"""Find how responses are rendered in DOM."""
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
        await page.keyboard.type("Say hello", delay=50)
        await asyncio.sleep(0.2)

        send_btn = await page.query_selector("button[type='submit']:has(svg)")
        if send_btn:
            await send_btn.click()
            print("Sent!")

        await asyncio.sleep(15)

        # Dump the full HTML structure to find message containers
        html = await page.evaluate("""
            () => {
                // Find ALL elements with message-like data attributes
                const all = document.querySelectorAll('*');
                const msgEls = [];
                for (const el of all) {
                    for (const attr of el.getAttributeNames()) {
                        if (attr.includes('message') || attr.includes('role') || attr.includes('author')) {
                            msgEls.push({
                                tag: el.tagName,
                                attr: attr + '=' + el.getAttribute(attr),
                                class: (el.className || '').slice(0, 60),
                                text: (el.textContent || '').trim().slice(0, 80),
                            });
                            break;
                        }
                    }
                }
                // Find ALL elements with role attribute
                const roleEls = [];
                for (const el of all) {
                    const role = el.getAttribute('role');
                    if (role) roleEls.push({tag: el.tagName, role, text: (el.textContent || '').trim().slice(0, 60)});
                }
                return {msgEls: msgEls.slice(0, 20), roleEls: roleEls.slice(0, 20), html: document.body.innerHTML.slice(3000, 8000)};
            }
        """)
        
        print("=== Elements with message/role attributes ===")
        print(json.dumps(html['msgEls'], indent=2))
        print("\n=== Role elements ===")
        print(json.dumps(html['roleEls'], indent=2))
        print("\n=== HTML snippet ===")
        print(html['html'][:2000])

        await asyncio.sleep(5)
        await browser.close()

asyncio.run(run())
