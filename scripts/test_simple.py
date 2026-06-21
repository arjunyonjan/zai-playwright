"""Simple DOM dump after send — no fancy selectors."""
import asyncio
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
        print("Loaded")

        textarea = await page.wait_for_selector("#chat-input", timeout=5000)
        await textarea.click()
        await page.keyboard.type("Say hello", delay=50)
        send_btn = await page.query_selector("button[type='submit']:has(svg)")
        if send_btn:
            await send_btn.click()
            print("Sent")

        await asyncio.sleep(20)

        all_text = await page.evaluate("document.body.innerText")
        print(f"\n=== ALL BODY TEXT ===\n{all_text[:3000]}")

        # Also dump all data-* attributes
        attrs = await page.evaluate("""
            () => {
                const all = document.querySelectorAll('[data-message-author-role], [data-role], [class*=\"assistant\"], [class*=\"Assistant\"]');
                return Array.from(all).map(el => ({
                    tag: el.tagName,
                    attrs: Array.from(el.attributes).map(a => a.name+'='+a.value).join(' '),
                    text: (el.textContent||'').trim().slice(0, 200),
                    html: el.innerHTML.slice(0, 300),
                }));
            }
        """)
        if attrs:
            print(f"\n=== SPECIAL ELEMENTS ({len(attrs)}) ===")
            for a in attrs[:10]:
                print(json.dumps(a, indent=2)[:300])

        await asyncio.sleep(3)
        await browser.close()

import json
asyncio.run(run())
