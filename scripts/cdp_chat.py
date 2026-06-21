"""Z.ai chat — uses CDP/Playwright to call the page's OWN JS functions (dre/fre/xfe)."""
import asyncio
import json
from playwright.async_api import async_playwright

TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3MTAxMDVmLTA4ZDUtNGMzZi1iNzA0LTdjZjUwZWM0NmVkNCIsImVtYWlsIjoiYXJqdW4ueW9uemFuQGdtYWlsLmNvbSJ9.DaYGdldHCFsPbofOx11tHr-vo8nRJ5sOFeEBO3HKOBL8rz4CUQz0qi3Mi84RJ4XV62J5hUieuMr1w-Jcdo1inw"

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        # Capture streaming SSE data
        stream_chunks = []
        async def on_response(resp):
            url = str(resp.url)
            if "/chat/completions" in url:
                try:
                    text = await resp.text()
                    stream_chunks.append({"url": url, "status": resp.status, "body": text[:2000]})
                except:
                    pass
        page.on("response", on_response)

        await page.goto("https://chat.z.ai", timeout=20000)
        await page.evaluate(f"localStorage.setItem('token', '{TOKEN}')")
        await page.reload(timeout=30000)
        await asyncio.sleep(4)

        print("=" * 60)
        print("Page loaded. Call the browser's own fre()/dre()/xfe() functions.")
        print("=" * 60)

        # Call the page's own functions to send a message
        result = await page.evaluate("""
            async () => {
                const token = localStorage.getItem('token');

                // 1. Get dre() output
                const { sortedPayload, urlParams, timestamp } = dre();
                
                // 2. Get fre() signature
                const promptText = 'hello';
                const { signature, timestamp: sigTs } = fre(sortedPayload, promptText, timestamp);
                
                // 3. Build X-Signature header = urlParams + &signature_timestamp=
                const xSignature = urlParams + '&signature_timestamp=' + sigTs;
                
                // 4. Build body
                const body = {
                    stream: false,
                    model: 'glm-5.2',
                    messages: [{ role: 'user', content: promptText }],
                    signature_prompt: promptText,
                };

                // Check features
                const features = {};
                let captchaParam = '';
                
                // 5. Get captcha if needed
                if (window.lN) {
                    try {
                        captchaParam = await lN();
                    } catch(e) {
                        console.warn('Captcha failed', e);
                    }
                }

                // 6. Call xfe directly
                const response = await xfe(
                    token,
                    captchaParam ? { ...body, captcha_verify_param: captchaParam } : body,
                    '/api/v2',
                    new AbortController().signal,
                    signature,
                    xSignature,
                    captchaParam
                );

                const text = await response.text();
                return {
                    signature,
                    urlParams,
                    timestamp: sigTs,
                    xSignature,
                    hasCaptcha: !!captchaParam,
                    status: response.status,
                    body: text.substring(0, 1000),
                };
            }
        """)

        print(f"\nResult:\n{json.dumps(result, indent=2)}")

        await asyncio.sleep(5)
        await browser.close()

asyncio.run(run())
