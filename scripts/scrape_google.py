"""Stealth Google scraper — avoids captcha without Chrome profile."""
import asyncio, urllib.parse
from playwright.async_api import async_playwright

QUERY = "nepal infrastructure news"
DATE_FILTER = "&tbs=qdr:w"

STEALTH_JS = """
// Hide automation from Google
Object.defineProperty(navigator, 'webdriver', {get: () => false});
Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});

// Override chrome runtime
window.chrome = {runtime: {}};
"""

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        ctx = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        )
        await ctx.add_init_script(STEALTH_JS)
        page = await ctx.new_page()

        search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(QUERY)}{DATE_FILTER}"
        print(f"Searching: {QUERY} (past week)")
        await page.goto(search_url, timeout=20000)
        await page.wait_for_timeout(3000)

        # Check if captcha showed up
        body = await page.evaluate("document.body.innerText")
        if "unusual traffic" in body.lower():
            print("Captcha triggered. Waiting for manual solve...")
            # User has 30s to solve the captcha in the browser window
            try:
                await page.wait_for_function(
                    "() => !document.body.innerText.toLowerCase().includes('unusual traffic')",
                    timeout=30000
                )
                print("Captcha solved!")
                await page.wait_for_timeout(2000)
            except:
                print("Captcha not solved. Results may be empty.")

        results = await page.evaluate("""
            () => {
                const blocks = document.querySelectorAll('div[data-sokoban-container], div.g, div[data-hveid]');
                const out = [];
                for (const block of Array.from(blocks).slice(0, 10)) {
                    const a = block.querySelector('a[href^="http"]');
                    const h3 = block.querySelector('h3');
                    // Snippet: the text block after the title
                    const snippetEl = block.querySelector('div[data-sncf], span.aCOpRe, div.VwiC3b');
                    const snippet = snippetEl ? snippetEl.textContent.trim() : '';
                    if (a && h3) {
                        out.push({title: h3.textContent, link: a.href, snippet});
                    }
                }
                // Fallback: h3 in links
                if (!out.length) {
                    const h3s = document.querySelectorAll('a[href^="http"] h3');
                    for (const h3 of Array.from(h3s).slice(0, 10)) {
                        const a = h3.closest('a');
                        if (!a) continue;
                        const parent = a.closest('div');
                        const textAfter = parent ? parent.textContent.replace(h3.textContent, '').trim().slice(0, 200) : '';
                        out.push({title: h3.textContent, link: a.href, snippet: textAfter});
                    }
                }
                return out.filter(r => r.link);
            }
        """)

        print(f"\n=== {QUERY} ===\n")
        if results:
            for i, r in enumerate(results, 1):
                print(f"{i}. {r['title']}\n   {r['link']}\n")
        else:
            print("No results — page text:")
            print(await page.evaluate("document.body.innerText.slice(0, 1500)"))

        await browser.close()

asyncio.run(run())
