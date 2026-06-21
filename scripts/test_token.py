"""Set JWT token in Playwright and test if it's still valid."""
import asyncio
import json
from playwright.async_api import async_playwright

TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3MTAxMDVmLTA4ZDUtNGMzZi1iNzA0LTdjZjUwZWM0NmVkNCIsImVtYWlsIjoiYXJqdW4ueW9uemFuQGdtYWlsLmNvbSJ9.DaYGdldHCFsPbofOx11tHr-vo8nRJ5sOFeEBO3HKOBL8rz4CUQz0qi3Mi84RJ4XV62J5hUieuMr1w-Jcdo1inw"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Navigate to the site first
        await page.goto("https://chat.z.ai/", timeout=30000)
        
        # Set the token
        await page.evaluate(f"localStorage.setItem('token', '{TOKEN}')")
        
        # Reload to use the token
        await page.goto("https://chat.z.ai/", wait_until="domcontentloaded", timeout=30000)
        
        # Check if we're authenticated
        token_check = await page.evaluate("localStorage.getItem('token')")
        print(f"Token in localStorage: {token_check[:20]}...")
        
        # Try to fetch models via the page context
        models = await page.evaluate("""
            async () => {
                try {
                    const r = await fetch('/api/v1/models/', {
                        headers: {
                            'Authorization': `Bearer ${localStorage.getItem('token')}`,
                            'Content-Type': 'application/json'
                        }
                    });
                    return { status: r.status, body: await r.text() };
                } catch (e) {
                    return { error: e.message };
                }
            }
        """)
        print(f"Models API: {json.dumps(models, indent=2)[:500]}")
        
        # Try chat completions
        chat_test = await page.evaluate("""
            async () => {
                try {
                    const r = await fetch('/api/v1/chat/completions', {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${localStorage.getItem('token')}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            model: 'glm-5-0529',
                            messages: [{role: 'user', content: 'hi'}],
                            stream: false
                        })
                    });
                    return { status: r.status, body: await r.text() };
                } catch (e) {
                    return { error: e.message };
                }
            }
        """)
        print(f"Chat test: {json.dumps(chat_test, indent=2)[:1000]}")
        
        # Wait to see the page
        print("\nPage is open. Close the browser window when done.")
        await asyncio.sleep(30)
        await browser.close()

asyncio.run(main())
