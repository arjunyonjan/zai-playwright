"""FastAPI server — call Playwright stock checker from anywhere."""
import asyncio, re
from fastapi import FastAPI, Query
from playwright.async_api import async_playwright

app = FastAPI(title="Stock Price API", version="1.0")
_browser = None
_pw = None

async def get_browser():
    global _browser, _pw
    if not _browser:
        _pw = await async_playwright().start()
        _browser = await _pw.chromium.launch(headless=True)
    return _browser

async def get_price(page, symbol, exchange):
    try:
        await page.goto(f"https://www.google.com/finance/quote/{symbol}:{exchange}", timeout=10000, wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)
        text = await page.evaluate("document.body.innerText")
        idx = text.find(f"{symbol}:{exchange}")
        if idx < 0: idx = text.find(symbol)
        if idx < 0: return {"symbol": symbol, "price": None, "change": None}
        chunk = text[idx:idx+200]
        p = re.findall(r"\$[\d,]+\.\d{2}", chunk)
        c = re.findall(r"[+-][\d.]+%", chunk)
        return {"symbol": symbol, "price": p[0] if p else None, "change": c[0] if c else None}
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}

@app.get("/stock/{symbol}")
async def stock(symbol: str, exchange: str = Query("NASDAQ")):
    browser = await get_browser()
    page = await browser.new_page()
    try:
        result = await get_price(page, symbol.upper(), exchange.upper())
    finally:
        await page.close()
    return result

@app.get("/stocks")
async def stocks(symbols: str = Query("AAPL,GOOGL,MSFT,TSLA,AMZN"), exchange: str = Query("NASDAQ")):
    browser = await get_browser()
    page = await browser.new_page()
    results = []
    try:
        for s in symbols.split(","):
            r = await get_price(page, s.strip().upper(), exchange.upper())
            results.append(r)
    finally:
        await page.close()
    return {"results": results}

@app.on_event("shutdown")
async def shutdown():
    global _browser, _pw
    if _browser:
        await _browser.close()
    if _pw:
        await _pw.stop()

# Run: uvicorn stock_api:app --host 0.0.0.0 --port 8000
