"""Z.ai chat client — uses Playwright to handle captcha, sends messages via
the page's built-in functions, and captures streaming replies."""
import asyncio
import json
import re
from playwright.async_api import async_playwright

TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3MTAxMDVmLTA4ZDUtNGMzZi1iNzA0LTdjZjUwZWM0NmVkNCIsImVtYWlsIjoiYXJqdW4ueW9uemFuQGdtYWlsLmNvbSJ9.DaYGdldHCFsPbofOx11tHr-vo8nRJ5sOFeEBO3HKOBL8rz4CUQz0qi3Mi84RJ4XV62J5hUieuMr1w-Jcdo1inw"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Monitor network responses
        responses = []
        async def on_response(resp):
            url = str(resp.url)
            if "/api/v2/chat/completions" in url or "/api/chat/completions" in url:
                try:
                    body = await resp.text()
                    responses.append({"url": url, "body": body[:500]})
                except:
                    pass
        page.on("response", on_response)
        
        # Load page and set token
        await page.goto("https://chat.z.ai", timeout=20000)
        await page.evaluate(f"localStorage.setItem('token', '{TOKEN}')")
        await page.reload(timeout=30000)
        await asyncio.sleep(5)
        
        print("Page loaded. Looking for chat input...")
        
        # Wait for the chat input to be visible
        try:
            await page.wait_for_selector("textarea, [contenteditable], #prompt-textarea, [data-testid='chat-input']", 
                                         timeout=10000)
        except:
            print("Could not find chat input element")
        
        # Print the page structure to find the right elements
        elements = await page.evaluate("""
            () => {
                const inputs = [];
                document.querySelectorAll('textarea, [contenteditable], input[type="text"], [role="textbox"]').forEach(el => {
                    inputs.push({
                        tag: el.tagName,
                        id: el.id,
                        class: el.className?.substring(0, 100),
                        placeholder: el.placeholder || el.getAttribute('data-placeholder') || '',
                        role: el.getAttribute('role') || '',
                        rect: el.getBoundingClientRect(),
                    });
                });
                return inputs;
            }
        """)
        print(f"Found input elements: {json.dumps(elements, indent=2)[:1000]}")
        
        # Try sending a message via the page's app code
        # Check if there's an existing chat or we need to create one
        result = await page.evaluate("""
            async () => {
                const token = localStorage.getItem('token');
                
                // Get or create a chat
                async function getOrCreateChat() {
                    // Try to get existing chats
                    const chatsRes = await fetch('/api/v1/chats/?page=1&type=default', {
                        headers: {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
                    });
                    const chats = await chatsRes.json();
                    if (chats.length > 0) {
                        return chats[0].id;
                    }
                    
                    // Create new chat
                    const createRes = await fetch('/api/v1/chats/new', {
                        method: 'POST',
                        headers: {
                            'Authorization': 'Bearer ' + token,
                            'Content-Type': 'application/json',
                            'Accept-Language': 'en-US'
                        },
                        body: JSON.stringify({model: 'glm-5.2'})
                    });
                    const chat = await createRes.json();
                    return chat.id;
                }
                
                try {
                    const chatId = await getOrCreateChat();
                    return {chatId};
                } catch(e) {
                    return {error: e.message, stack: e.stack};
                }
            }
        """)
        print(f"Chat setup: {json.dumps(result, indent=2)}")
        
        if "chatId" in result:
            # Navigate to the chat
            await page.goto(f"https://chat.z.ai/c/{result['chatId']}", timeout=20000)
            await asyncio.sleep(3)
            
            # Try to type and send a message
            await page.evaluate("""
                async () => {
                    const token = localStorage.getItem('token');
                    
                    // Send message via API with captcha
                    async function sendMessage() {
                        const ts = Date.now();
                        const reqId = crypto.randomUUID();
                        
                        const body = {
                            stream: false,
                            model: 'glm-5.2',
                            messages: [{role: 'user', content: 'hello'}],
                            signature_prompt: 'hello',
                        };
                        
                        const qs = 'requestId=' + reqId + '&timestamp=' + ts + '&user_id=' + '&signature_timestamp=' + ts;
                        const r = await fetch('/api/v2/chat/completions?' + qs, {
                            method: 'POST',
                            headers: {
                                'Authorization': 'Bearer ' + token,
                                'Content-Type': 'application/json',
                                'X-FE-Version': 'prod-fe-1.1.66',
                                'X-Signature': 'test',
                            },
                            body: JSON.stringify(body)
                        });
                        return {status: r.status, body: await r.text()};
                    }
                    
                    return await sendMessage();
                }
            """)
        
        # Wait a bit to see what happens
        await asyncio.sleep(10)
        
        print("\nCaptured API responses:")
        for r in responses:
            print(f"  {r['url']}")
            print(f"    {r['body'][:200]}")
        
        input("Press Enter to exit...")
        await browser.close()

asyncio.run(main())
