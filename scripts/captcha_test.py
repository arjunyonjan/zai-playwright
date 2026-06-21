"""Z.ai client using Playwright for captcha handling + direct HTTP for API."""
import asyncio
import json
import time
import uuid
import hashlib
import hmac
import base64
import httpx
from playwright.async_api import async_playwright

HMAC_SECRET = "key-@@@@)))()((9))-xxxx&&&%%%%%"

def compute_signature(sorted_payload: str, prompt_text: str, timestamp: int) -> str:
    prompt_bytes = prompt_text.encode("utf-8")
    chunk_size = 32768
    chunks = []
    for i in range(0, len(prompt_bytes), chunk_size):
        chunks.append(prompt_bytes[i:i+chunk_size])
    b64 = base64.b64encode(b"".join(chunks)).decode()
    to_sign = f"{sorted_payload}|{b64}|{timestamp}"
    time_window = timestamp // (5 * 60 * 1000)
    session_key = hmac.new(HMAC_SECRET.encode(), str(time_window).encode(), hashlib.sha256).hexdigest()
    return hmac.new(session_key.encode(), to_sign.encode(), hashlib.sha256).hexdigest()

async def main():
    TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3MTAxMDVmLTA4ZDUtNGMzZi1iNzA0LTdjZjUwZWM0NmVkNCIsImVtYWlsIjoiYXJqdW4ueW9uemFuQGdtYWlsLmNvbSJ9.DaYGdldHCFsPbofOx11tHr-vo8nRJ5sOFeEBO3HKOBL8rz4CUQz0qi3Mi84RJ4XV62J5hUieuMr1w-Jcdo1inw"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Listen for captcha event
        captcha_result = None
        
        def handle_console(msg):
            nonlocal captcha_result
            text = msg.text
            if "captcha_verify_success" in text:
                print("Captcha solved!")
        
        page.on("console", handle_console)
        
        await page.goto("https://chat.z.ai/", timeout=20000)
        await page.evaluate(f"localStorage.setItem('token', '{TOKEN}')")
        await page.reload(timeout=30000)
        await asyncio.sleep(3)
        
        # Check if captcha is present
        has_captcha = await page.evaluate("""
            () => {
                return document.querySelector('.ali-captcha') !== null ||
                       document.querySelector('[class*="captcha"]') !== null ||
                       typeof initAliyunCaptcha !== 'undefined';
            }
        """)
        print(f"Captcha element found: {has_captcha}")
        
        # Get captcha scene config
        scene_cfg = await page.evaluate("""
            () => {
                // Try to find Sh (scene config) variable
                try {
                    return window.Sh || null;
                } catch(e) { return null; }
            }
        """)
        print(f"Sh (scene cfg): {scene_cfg}")
        
        # Try to trigger captcha initialization programmatically  
        # and get the captcha token
        result = await page.evaluate("""
            async () => {
                const token = localStorage.getItem('token');
                
                // Build the request with captcha bypass attempt
                const ts = Date.now();
                const reqId = crypto.randomUUID();
                const payload = 'requestId=' + reqId + '&timestamp=' + ts + '&user_id=';
                const body = {
                    stream: false,
                    model: 'glm-5.2',
                    messages: [{role: 'user', content: 'hi'}],
                    signature_prompt: 'hi',
                };
                
                // Try without captcha first
                const qs = payload + '&signature_timestamp=' + ts;
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
                const text = await r.text();
                return {status: r.status, body: text.substring(0, 500)};
            }
        """)
        print(f"Page-based request: {json.dumps(result, indent=2)[:500]}")
        
        input("Press Enter to exit...")
        await browser.close()

asyncio.run(main())
