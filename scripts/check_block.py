"""Check if token is still valid, and what Z.ai actually rejects."""
import asyncio
from playwright.async_api import async_playwright

TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3MTAxMDVmLTA4ZDUtNGMzZi1iNzA0LTdjZjUwZWM0NmVkNCIsImVtYWlsIjoiYXJqdW4ueW9uemFuQGdtYWlsLmNvbSJ9.DaYGdldHCFsPbofOx11tHr-vo8nRJ5sOFeEBO3HKOBL8rz4CUQz0qi3Mi84RJ4XV62J5hUieuMr1w-Jcdo1inw"

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})

        await page.goto("https://chat.z.ai", timeout=30000)
        await page.evaluate(f"localStorage.setItem('token', '{TOKEN}')")
        await page.reload(timeout=30000)
        await asyncio.sleep(3)

        # Check page loaded properly
        title = await page.title()
        print(f"Title: {title}")

        # Check token in localStorage
        stored = await page.evaluate("localStorage.getItem('token')")
        print(f"Token in localStorage: {'yes' if stored else 'no'} ({len(stored) if stored else 0} chars)")

        # Try /api/models - this is a simple GET
        models_ok = await page.evaluate("""
            async () => {
                try {
                    const r = await fetch('/api/models', {
                        headers: {'Authorization': 'Bearer ' + localStorage.getItem('token')}
                    });
                    const d = await r.json();
                    return {status: r.status, count: (d.data || []).length};
                } catch(e) {
                    return {error: e.message};
                }
            }
        """)
        print(f"Models API: {models_ok}")

        # Try /api/config
        config_ok = await page.evaluate("""
            async () => {
                try {
                    const r = await fetch('/api/config');
                    return {status: r.status};
                } catch(e) {
                    return {error: e.message};
                }
            }
        """)
        print(f"Config API: {config_ok}")

        # Send a chat message via UI, capture response
        resp_text = await page.evaluate("""
            async () => {
                const ta = document.querySelector('#chat-input');
                if (!ta) return 'NO_TEXTAREA';
                ta.value = 'ping';
                ta.dispatchEvent(new Event('input', {bubbles: true}));
                await new Promise(r => setTimeout(r, 300));
                const btn = document.querySelector("button[type='submit']:has(svg)");
                if (!btn) return 'NO_SEND_BTN';
                btn.click();

                // Wait and capture the response
                return new Promise((resolve) => {
                    let cap = '';
                    const orig = window.fetch;
                    window.fetch = (...args) => {
                        const p = orig(...args);
                        if (typeof args[0] === 'string' && args[0].includes('/chat/completions')) {
                            p.then(r => {
                                const ct = r.headers.get('content-type') || '';
                                if (ct.includes('event-stream')) {
                                    r.clone().text().then(t => { cap = t; }).catch(() => {});
                                }
                            }).catch(() => {});
                        }
                        return p;
                    };
                    setTimeout(async () => {
                        window.fetch = orig;
                        resolve(cap || 'NO_CAPTURE');
                    }, 15000);
                });
            }
        """)

        if resp_text:
            print(f"\nChat API response (first 500): {resp_text[:500]}")
            if "MODEL_CONCURRENCY_LIMIT" in resp_text:
                print("\n=> Servers are just busy (concurrency limit)")
            elif "FRONTEND_CAPTCHA_REQUIRED" in resp_text:
                print("\n=> Captcha issue - may need fresh page/token")
            elif "delta_content" in resp_text:
                print("\n=> IT WORKED! Response received!")
            elif "401" in resp_text or "unauthorized" in resp_text.lower():
                print("\n=> TOKEN EXPIRED!")
            else:
                print("\n=> Unknown response pattern")
        else:
            print("No response captured")

        await browser.close()

asyncio.run(run())
