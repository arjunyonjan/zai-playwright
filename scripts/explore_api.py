"""Capture all API calls - minimal approach."""
import asyncio, json, sys
from playwright.async_api import async_playwright

TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3MTAxMDVmLTA4ZDUtNGMzZi1iNzA0LTdjZjUwZWM0NmVkNCIsImVtYWlsIjoiYXJqdW4ueW9uemFuQGdtYWlsLmNvbSJ9.DaYGdldHCFsPbofOx11tHr-vo8nRJ5sOFeEBO3HKOBL8rz4CUQz0qi3Mi84RJ4XV62J5hUieuMr1w-Jcdo1inw"
captured = []

async def main():
    global captured
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        async def log_response(resp):
            url = str(resp.url)
            if "/api/" not in url:
                return
            try:
                body = await resp.text()
            except:
                body = ""
            entry = {
                "url": url, "method": resp.request.method, "status": resp.status,
                "req_body": resp.request.post_data or "",
                "res_body": body[:3000],
            }
            captured.append(entry)
            print(f"{resp.request.method} {url} [{resp.status}] {'body: ' + resp.request.post_data[:150] if resp.request.post_data else ''}")

        page.on("response", log_response)
        
        try:
            await page.goto("https://chat.z.ai/", timeout=20000)
        except:
            print("Navigation timeout (expected), continuing...")
        
        await page.evaluate(f"localStorage.setItem('token', '{TOKEN}')")
        print("Token set, reloading...")
        
        await page.reload(timeout=30000)
        await asyncio.sleep(5)
        
        # Try to find models available
        print("\n--- Trying to chat ---")
        result = await page.evaluate("""
            async () => {
                const token = localStorage.getItem('token');
                const endpoints = [];
                // Try various endpoints
                for (const ep of ['/api/v1/models', '/api/models', '/api/v1/chat/completions', '/api/chat/completions', '/v1/chat/completions']) {
                    try {
                        const r = await fetch(ep, {
                            headers: {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
                        });
                        endpoints.push({ep, status: r.status, body: (await r.text()).slice(0, 200)});
                    } catch(e) {
                        endpoints.push({ep, error: e.message});
                    }
                }
                return endpoints;
            }
        """)
        for ep in result:
            print(f"  {ep.get('ep')}: [{ep.get('status', 'ERR')}] {ep.get('body', ep.get('error', ''))}")
        
        input("\nPress Enter to save and exit...")
        
        with open("captured_api.json", "w", encoding="utf-8") as f:
            json.dump(captured, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(captured)} entries")
        await browser.close()

asyncio.run(main())
