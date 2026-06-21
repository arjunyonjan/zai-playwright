"""Stock prices — headless, 1 min timeout, auto-stop."""
import asyncio, re
from playwright.async_api import async_playwright

SYMBOLS = [("AAPL","NASDAQ"),("GOOGL","NASDAQ"),("MSFT","NASDAQ"),("TSLA","NASDAQ"),("AMZN","NASDAQ")]

async def get_price(page, sym, ex):
    try:
        await page.goto(f"https://www.google.com/finance/quote/{sym}:{ex}", timeout=10000, wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)
        text = await page.evaluate("document.body.innerText")
        idx = text.find(f"{sym}:{ex}")
        if idx < 0: idx = text.find(sym)
        if idx < 0: return f"{sym:6s} ?"
        chunk = text[idx:idx+200]
        p = re.findall(r"\$[\d,]+\.\d{2}", chunk)
        c = re.findall(r"[+-][\d.]+%", chunk)
        return f"{sym:6s} {p[0] if p else '?'}  {c[0] if c else ''}"
    except:
        return f"{sym:6s} timeout"

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("\nStock prices:\n")
        for sym, ex in SYMBOLS:
            line = (await get_price(page, sym, ex)).encode("ascii","replace").decode()
            print(f"  {line}")
        print()
        await browser.close()

try:
    asyncio.run(asyncio.wait_for(run(), timeout=55))
except asyncio.TimeoutError:
    print("  [stopped after 55s]")
