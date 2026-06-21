"""Map the DOM structure of rendered messages for the chat client."""
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

        # Wait for DOM to update with response
        for i in range(60):
            await asyncio.sleep(1)
            try:
                dom_info = await page.evaluate("""
                    () => {
                        // Find ALL elements with text content
                        const all = document.querySelectorAll('*');
                        const results = [];
                        
                        // Look for the main content area
                        const main = document.querySelector('main') || document.querySelector('div:has(> #chat-input)') || document.body;
                        
                        // Find user and assistant messages markers
                        const markers = ['data-message-author-role', 'data-message-role', 'data-role', 'data-author'];
                        const msgElements = [];
                        for (const el of all) {
                            for (const marker of markers) {
                                const val = el.getAttribute(marker);
                                if (val) {
                                    const rect = el.getBoundingClientRect();
                                    msgElements.push({
                                        tag: el.tagName,
                                        marker: `${marker}=${val}`,
                                        class: (el.className || '').slice(0, 80),
                                        id: el.id,
                                        text: (el.textContent || '').trim().slice(0, 200),
                                        rect: rect.width > 0 ? `${rect.width}x${rect.height}` : 'hidden',
                                    });
                                    break;
                                }
                            }
                        }
                        
                        // Get all text content in main area
                        const mainText = main ? main.innerText || '' : '';
                        
                        // Get user/assistant message divs by looking at parent structure
                        // Usually in chat apps, messages are in a specific container
                        const allDivs = Array.from(document.querySelectorAll('div'));
                        const msgDivs = [];
                        for (const div of allDivs) {
                            const text = (div.textContent || '').trim();
                            if (text && (text.includes('Hello') || text.includes('hello')) && text.length < 100) {
                                msgDivs.push({
                                    class: (div.className || '').slice(0, 100),
                                    text: text,
                                    parentClass: div.parentElement ? (div.parentElement.className || '').slice(0, 80) : '',
                                    depth: (() => { let d=0, p=div; while(p) { d++; p=p.parentElement; if(d>5) break; } return d; })(),
                                });
                            }
                        }
                        
                        return {
                            msgElements, msgDivs,
                            mainTextSnippet: mainText.substring(0, 1000),
                            htmlSnippet: document.body.innerHTML.substring(0, 5000),
                        };
                    }
                """)
                
                if dom_info['msgElements']:
                    print(f"\n=== Elements with message markers ===")
                    print(json.dumps(dom_info['msgElements'], indent=2))
                if dom_info['msgDivs']:
                    print(f"\n=== Divs containing 'Hello' ===")
                    print(json.dumps(dom_info['msgDivs'], indent=2))
                
                if 'Hello' in dom_info.get('mainTextSnippet', '') or 'hello' in dom_info.get('mainTextSnippet', ''):
                    print(f"\n=== Main area text ===\n{dom_info['mainTextSnippet']}")
                    break
                    
                if i == 30:
                    print(f"\n=== HTML snippet at 30s ===\n{dom_info['htmlSnippet'][:2000]}")
                    
            except Exception as e:
                print(f"[{i}] Error: {e}")
                break
        else:
            print("Timeout")

        await asyncio.sleep(5)
        await browser.close()

asyncio.run(run())
