"""Z.ai chat via CDP — intercepts bundle to expose dre/fre/xfe on window."""
import asyncio
import json
import re
from playwright.async_api import async_playwright

TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3MTAxMDVmLTA4ZDUtNGMzZi1iNzA0LTdjZjUwZWM0NmVkNCIsImVtYWlsIjoiYXJqdW4ueW9uemFuQGdtYWlsLmNvbSJ9.DaYGdldHCFsPbofOx11tHr-vo8nRJ5sOFeEBO3HKOBL8rz4CUQz0qi3Mi84RJ4XV62J5hUieuMr1w-Jcdo1inw"

PATCH = r"""
// Expose internal functions for CDP automation
if (!window.__patched && typeof dre === 'function') {
    window.__patched = true;
    window.__dre = dre;
    window.__fre = fre;
    window.__xfe = xfe;
    window.__lN = typeof lN !== 'undefined' ? lN : null;
}
"""

# Minified patch
MINI_PATCH = "window.__patched||(window.__patched=!0,window.__dre=dre,window.__fre=fre,window.__xfe=xfe,window.__lN=typeof lN!=='undefined'?lN:null);"

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        # Intercept the bundle JS and inject window exposure
        async def route_handler(route):
            url = str(route.request.url)
            if url.endswith(".js") and "assets/index-" in url and route.request.resource_type == "script":
                resp = await route.fetch()
                body = await resp.text()
                # Inject our patch at the end of the bundle
                patched = body + "\n" + MINI_PATCH
                await route.fulfill(
                    body=patched,
                    content_type="application/javascript",
                    headers=resp.headers,
                )
                print(f"  Patched bundle: {url.split('/')[-1][:60]}")
            else:
                await route.continue_()
        
        await page.route("**/*", route_handler)

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

        print("=" * 50)
        print("Page loaded. Testing if functions are exposed...")
        print("=" * 50)

        # Check if exposure worked
        exposed = await page.evaluate("typeof window.__dre === 'function'")
        print(f"  __dre exposed: {exposed}")
        
        if not exposed:
            # Try harder - scan the window for the functions
            print("  Attempting to find functions via eval...")
            found = await page.evaluate("""
                () => {
                    const results = {};
                    // Common patterns in Vite bundles
                    const keys = Object.getOwnPropertyNames(window);
                    // Search for functions that return objects with sortedPayload
                    for (const key of keys) {
                        try {
                            const val = window[key];
                            if (typeof val === 'function' && val.toString().includes('sortedPayload')) {
                                results[key] = 'found sortedPayload';
                            }
                        } catch(e) {}
                    }
                    // Check global scope
                    try {
                        if (typeof dre === 'function') results.global_dre = 'found';
                        if (typeof fre === 'function') results.global_fre = 'found';
                        if (typeof xfe === 'function') results.global_xfe = 'found';
                    } catch(e) {}
                    return results;
                }
            """)
            print(f"  Scan result: {json.dumps(found)}")
        else:
            # Test call
            result = await page.evaluate("""
                async () => {
                    const token = localStorage.getItem('token');
                    const { sortedPayload, urlParams, timestamp } = window.__dre();
                    const promptText = 'hello';
                    const { signature, timestamp: sigTs } = window.__fre(sortedPayload, promptText, timestamp);
                    const xSignature = urlParams + '&signature_timestamp=' + sigTs;
                    const body = {
                        stream: false,
                        model: 'glm-5.2',
                        messages: [{ role: 'user', content: promptText }],
                        signature_prompt: promptText,
                    };
                    let captchaParam = '';
                    if (window.__lN) {
                        try { captchaParam = await window.__lN(); } catch(e) {}
                    }
                    const response = await window.__xfe(
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
                        hasCaptcha: !!captchaParam,
                        status: response.status,
                        body: text.substring(0, 2000),
                        xSignature,
                    };
                }
            """)
            print(f"\nResult:\n{json.dumps(result, indent=2)}")

        await asyncio.sleep(5)
        await browser.close()

asyncio.run(run())
