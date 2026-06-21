"""No interceptor — just send and check DOM thoroughly after response."""
import asyncio, json
from playwright.async_api import async_playwright

TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3MTAxMDVmLTA4ZDUtNGMzZi1iNzA0LTdjZjUwZWM0NmVkNCIsImVtYWlsIjoiYXJqdW4ueW9uemFuQGdtYWlsLmNvbSJ9.DaYGdldHCFsPbofOx11tHr-vo8nRJ5sOFeEBO3HKOBL8rz4CUQz0qi3Mi84RJ4XV62J5hUieuMr1w-Jcdo1inw"

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        # Track if API call was made
        api_called = asyncio.Event()
        api_status = {}
        async def on_response(resp):
            if "/chat/completions" in resp.url and "/api/v1/chats" not in resp.url:
                api_status["status"] = resp.status
                api_status["url"] = resp.url
                # Read first chunk to detect errors
                api_called.set()
        page.on("response", on_response)

        await page.goto("https://chat.z.ai", timeout=20000)
        await page.evaluate(f"localStorage.setItem('token', '{TOKEN}')")
        await page.reload(timeout=30000)
        await asyncio.sleep(3)

        textarea = await page.wait_for_selector("#chat-input", timeout=5000)
        await textarea.click()
        await page.keyboard.type("Say hello in one word", delay=50)
        await asyncio.sleep(0.2)

        send_btn = await page.query_selector("button[type='submit']:has(svg)")
        if send_btn:
            await send_btn.click()
            print("Sent!")

        # Wait for API call
        await asyncio.wait_for(api_called.wait(), timeout=30)
        print(f"API called -> {api_status.get('status')}")

        # Wait for DOM to update
        for i in range(60):
            await asyncio.sleep(1)
            try:
                state = await page.evaluate("""
                    () => {
                        // Get ALL text in the main content area (not sidebar)
                        const main = document.querySelector('main') || document.querySelector('[class*="main"]') || document.body;
                        const text = main.innerText || '';
                        
                        // Find any elements that contain the response
                        const allEls = document.querySelectorAll('*');
                        let responseArea = '';
                        for (const el of allEls) {
                            const t = (el.textContent || '').trim();
                            // Skip tiny elements and common UI text
                            if (t.includes('Hello') || t.includes('hello') || t.includes('one word') && t.length < 200) {
                                responseArea = t;
                                break;
                            }
                        }
                        
                        // Check for error UI
                        const errorUi = document.querySelector('[role="alert"], [class*="error"], [class*="Error"]');
                        const errorText = errorUi ? (errorUi.textContent || '').trim().slice(0, 200) : '';
                        
                        // Get URL
                        return {
                            url: location.href,
                            hasHello: text.includes('Hello') || text.includes('hello'),
                            responseFound: responseArea,
                            errorText,
                            mainTextSnippet: text.substring(0, 1000),
                        };
                    }
                """)
                
                if state['hasHello']:
                    print(f"[{i}] Found response!")
                    print(f"  Response: {state['responseFound']}")
                    break
                if state['errorText']:
                    print(f"[{i}] Error in UI: {state['errorText']}")
                    break
                    
                # Print snippet every 10 seconds
                if i % 10 == 0:
                    print(f"[{i}] {state['mainTextSnippet'][:150].replace(chr(10), ' ')}")
            except Exception as e:
                print(f"[{i}] Error: {e}")
                break
        else:
            print("Timeout")

        # Final HTML dump
        final = await page.evaluate("document.body.innerHTML.substring(0, 5000)")
        print(f"\n=== FINAL HTML (first 5000) ===\n{final[:2000]}")

        await asyncio.sleep(5)
        await browser.close()

asyncio.run(run())
