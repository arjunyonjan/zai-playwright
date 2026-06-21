"""Find CAPTCHA and HMAC in page globals."""
import asyncio
from playwright.async_api import async_playwright

TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3MTAxMDVmLTA4ZDUtNGMzZi1iNzA0LTdjZjUwZWM0NmVkNCIsImVtYWlsIjoiYXJqdW4ueW9uemFuQGdtYWlsLmNvbSJ9.DaYGdldHCFsPbofOx11tHr-vo8nRJ5sOFeEBO3HKOBL8rz4CUQz0qi3Mi84RJ4XV62J5hUieuMr1w-Jcdo1inw"

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://chat.z.ai", timeout=30000)
        await page.evaluate(f"localStorage.setItem('token', '{TOKEN}')")
        await page.reload(timeout=30000)
        await asyncio.sleep(5)

        # Check if fetch is wrapped
        is_wrapped = await page.evaluate("""
            () => {
                const fetchStr = window.fetch.toString();
                return {isNative: fetchStr.includes('[native code]'), snippet: fetchStr.slice(0, 200)};
            }
        """)
        print(f"fetch native: {is_wrapped['isNative']}")
        if not is_wrapped['isNative']:
            print(f"fetch wrapper: {is_wrapped['snippet']}")

        # Check for known HMAC functions
        has_dre = await page.evaluate("typeof window.dre")
        print(f"typeof dre: {has_dre}")

        # Check globals for captcha / token related keys
        captcha_keys = await page.evaluate("""
            () => {
                const keys = Object.keys(window).filter(k => 
                    k.toLowerCase().includes('captcha') || 
                    k.toLowerCase().includes('verify') ||
                    k.toLowerCase().includes('aliyun')
                );
                return keys.slice(0, 20);
            }
        """)
        print(f"captcha globals: {captcha_keys}")

        # Check for _captcha, captcha_verify etc
        checks = await page.evaluate("""
            () => {
                const r = {};
                for (const key of ['_captcha', 'captcha', 'captchaToken', 'aliyunCaptcha',
                    'verifyToken', 'captchaVerifyParam', '__captcha']) {
                    r[key] = window[key] !== undefined ? String(window[key]).slice(0, 80) : 'UNDEFINED';
                }
                return r;
            }
        """)
        for k, v in checks.items():
            print(f"  {k}: {v}")

        # Use our own fetch interceptor (TEMPORARY - one request only)
        # to capture what the page actually sends
        api_data = await page.evaluate("""
            async () => {
                const orig = window.fetch;
                window.__lastChatReq = null;
                window.fetch = (...args) => {
                    window.__lastChatReq = args;
                    return orig(...args);
                };

                // Trigger a real send by clicking
                const ta = document.querySelector('#chat-input');
                if (ta) {
                    const nativeSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLTextAreaElement.prototype, 'value'
                    ).set;
                    nativeSetter.call(ta, 'hello');
                    ta.dispatchEvent(new Event('input', {bubbles: true}));
                    await new Promise(r => setTimeout(r, 200));
                    const btn = document.querySelector("button[type='submit']:has(svg)");
                    if (btn) btn.click();
                    await new Promise(r => setTimeout(r, 2000));
                }
                window.fetch = orig;
                return window.__lastChatReq ? {
                    url: window.__lastChatReq[0],
                    headers: Object.fromEntries(
                        (window.__lastChatReq[1]?.headers || new Headers()).entries ?
                            (window.__lastChatReq[1].headers).entries() : []
                    ),
                    body: window.__lastChatReq[1]?.body || null
                } : null;
            }
        """)

        if api_data:
            print(f"\n=== CAPTURED REQUEST ===")
            print(f"URL: {api_data['url']}")
            print(f"Headers: {json.dumps(api_data['headers'], indent=2)}")
            print(f"Body: {api_data['body']}")
        else:
            print("No request captured")

        await browser.close()

asyncio.run(run())
