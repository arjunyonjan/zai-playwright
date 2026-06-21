"""Quick page exploration — finds chat input and send button selectors."""
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
        await asyncio.sleep(5)

        info = await page.evaluate("""
            () => ({
                url: location.href,
                textareas: Array.from(document.querySelectorAll('textarea')).map(t => ({
                    id: t.id, name: t.name, class: (t.className || '').slice(0, 80),
                    placeholder: t.placeholder, rows: t.rows, cols: t.cols,
                    rect: (r => r ? `${r.left},${r.top},${r.width}x${r.height}` : null)(t.getBoundingClientRect()),
                    parent: t.parentElement ? (t.parentElement.tagName + '.' + (t.parentElement.className || '').slice(0, 60)) : null
                })),
                contenteditables: Array.from(document.querySelectorAll('[contenteditable]')).map(t => ({
                    tag: t.tagName, id: t.id, class: (t.className || '').slice(0, 80),
                    parent: t.parentElement ? (t.parentElement.tagName + '.' + (t.parentElement.className || '').slice(0, 60)) : null
                })),
                buttons: Array.from(document.querySelectorAll('button')).map(b => ({
                    id: b.id, text: (b.textContent || '').trim().slice(0, 50),
                    class: (b.className || '').slice(0, 80), type: b.type,
                    has_svg: !!b.querySelector('svg'),
                    rect: (r => r ? `${r.left},${r.top},${r.width}x${r.height}` : null)(b.getBoundingClientRect()),
                })),
                inputs: Array.from(document.querySelectorAll('input[type="text"]')).map(i => ({
                    id: i.id, placeholder: i.placeholder, class: (i.className || '').slice(0, 80)
                })),
                body_html: document.body.innerHTML.slice(0, 3000),
            })
        """)

        print(json.dumps(info, indent=2, default=str)[:5000])
        input("\nPress Enter to exit...")
        await browser.close()

asyncio.run(run())
