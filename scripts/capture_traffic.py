"""Capture Z.ai API traffic — login, send message, save requests/responses."""
import asyncio
import json
import sys
from datetime import datetime
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding='utf-8')

OUTPUT = "captured_traffic.json"
all_entries = []
seen_urls = set()

def is_api_request(url):
    return any(x in url for x in ["/api/", "/chats", "/completions", "/auth", "/sign", "/challenge"])

async def handle_response(response):
    url = response.url
    if not is_api_request(url):
        return
    
    try:
        body = await response.text()
    except:
        body = "<binary>"
    
    headers = dict(response.headers)
    entry = {
        "time": datetime.now().isoformat(),
        "url": url,
        "method": response.request.method,
        "status": response.status,
        "request_headers": dict(response.request.headers),
        "response_headers": headers,
        "request_body": response.request.post_data or "",
        "response_body": body[:10000],
    }
    all_entries.append(entry)

async def handle_request(request):
    url = request.url
    if not is_api_request(url):
        return
    
    if url in seen_urls:
        return
    seen_urls.add(url)
    
    headers = dict(request.headers)
    post_data = request.post_data or ""
    
    print(f"\n>>> {request.method} {url}")
    for k in ["authorization", "content-type", "x-", "signature", "timestamp"]:
        for hk, hv in headers.items():
            if hk.lower().startswith(k):
                print(f"    {hk}: {hv[:200]}")
    if post_data:
        print(f"    body: {post_data[:500]}")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-web-security"]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()
        
        page.on("response", handle_response)
        page.on("request", handle_request)
        
        print("Navigating to chat.z.ai...")
        await page.goto("https://chat.z.ai", wait_until="domcontentloaded", timeout=30000)
        
        print("\n" + "="*60)
        print("Page loaded. Complete login and send a chat message.")
        print("Press Ctrl+C in this terminal when done capturing.")
        print("="*60 + "\n")
        
        # Wait until user presses Ctrl+C
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            with open(OUTPUT, "w", encoding="utf-8") as f:
                json.dump(all_entries, f, indent=2, ensure_ascii=False)
            print(f"\nSaved {len(all_entries)} API entries to {OUTPUT}")
            await browser.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCapture stopped by user.")
