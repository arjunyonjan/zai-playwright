"""CDP chat: inject fetch from page context, parse SSE directly."""
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

        print("Calling API from page context...")
        text = await page.evaluate("""
            async () => {
                const resp = await window.fetch('/api/v2/chat/completions', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'x-fe-version': 'prod-fe-1.1.66'
                    },
                    body: JSON.stringify({
                        model: 'glm-4.7',
                        messages: [{role: 'user', content: 'Say hi in 5 words'}],
                        stream: true,
                        features: {
                            image_generation: false,
                            web_search: false,
                            auto_web_search: false,
                            preview_mode: true,
                            flags: [],
                            vlm_tools_enable: false,
                            vlm_web_search_enable: false,
                            vlm_website_mode: false,
                            enable_thinking: false,
                        },
                    })
                });

                if (!resp.ok) {
                    return 'HTTP ' + resp.status + ': ' + await resp.text();
                }

                const reader = resp.body.getReader();
                const decoder = new TextDecoder();
                let answer = '';
                let buffer = '';

                const events = [];

                while (true) {
                    const {done, value} = await reader.read();
                    if (done) break;
                    buffer += decoder.decode(value, {stream: true});

                    const lines = buffer.split('\\n');
                    buffer = lines.pop() || '';

                    for (const line of lines) {
                        if (!line.startsWith('data: ')) continue;
                        events.push(line.slice(6));
                        try {
                            const ev = JSON.parse(line.slice(6));
                            if (ev.type === 'chat:completion') {
                                answer += ev.data.delta_content || '';
                                if (ev.data.phase === 'done') return 'DONE:' + JSON.stringify(events);
                            }
                        } catch(e) {}
                    }
                }
                return 'END:' + JSON.stringify(events) + '|ANSWER:' + answer;
            }
        """)

        print(f"\n=== RESULT ===\n{text[:1000]}")
        await browser.close()

asyncio.run(run())
