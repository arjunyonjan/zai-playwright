import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

OUTPUT_DIR = Path(__file__).parent.parent / "bundles"

async def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        async def handle_response(response):
            if response.url.endswith(".js") and response.ok:
                body = await response.text()
                name = response.url.split("/")[-1]
                path = OUTPUT_DIR / name
                path.write_text(body, encoding="utf-8")
                print(f"[+] {name} ({len(body)} bytes)")

        page.on("response", handle_response)
        await page.goto("https://chat.z.ai", wait_until="networkidle")
        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
