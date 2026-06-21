"""Scrape Nepal + China news → summarize via Z.ai. Captcha solved once, cached."""
import asyncio, sys, urllib.parse, os
sys.path.insert(0, ".")
from playwright.async_api import async_playwright
from zai_chat import ZAIChat

TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3MTAxMDVmLTA4ZDUtNGMzZi1iNzA0LTdjZjUwZWM0NmVkNCIsImVtYWlsIjoiYXJqdW4ueW9uemFuQGdtYWlsLmNvbSJ9.DaYGdldHCFsPbofOx11tHr-vo8nRJ5sOFeEBO3HKOBL8rz4CUQz0qi3Mi84RJ4XV62J5hUieuMr1w-Jcdo1inw"

SEARCHES = ["china nepal projects news"]
GET_ARTICLE = """
() => {
    let el = document.querySelector('article') || document.querySelector('main');
    if (el) return el.innerText.slice(0,8000);
    let best=null, bc=0;
    for (const d of document.querySelectorAll('div,section')) {
        if (d.closest('header,nav,footer,aside')) continue;
        let n = d.querySelectorAll('p').length;
        if (n>bc) {bc=n; best=d;}
    }
    return (best||document.body).innerText.slice(0,8000);
}
"""

async def google_search(page, query, max_results=10):
    url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
    await page.goto(url, timeout=15000)
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(2000)

    body = await page.evaluate("document.body.innerText")
    if len(body) < 300 or "verify" in body.lower() or "unusual traffic" in body.lower():
        print("  Captcha — solve in browser window (30s)...")
        await page.wait_for_timeout(30000)

    results = await page.evaluate(f"""
        () => Array.from(document.querySelectorAll('a[href^="http"] h3')).slice(0,{max_results}).map(h3 => {{
            const a = h3.closest('a');
            return a ? {{title: h3.textContent, link: a.href}} : null;
        }}).filter(Boolean)
    """)
    skip = ["facebook","instagram","twitter","youtube","google.com/search"]
    return [r for r in results if not any(d in r['link'] for d in skip)]

async def extract_articles(page, results):
    texts = []
    for i, r in enumerate(results):
        print(f"  [{i+1}/{len(results)}] {r['title'][:55]}...", end="", flush=True)
        try:
            await page.goto(r['link'], timeout=15000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            text = await page.evaluate(GET_ARTICLE)
            if text and len(text) > 300:
                texts.append(f"--- {r['title']} ({r['link']}) ---\n{text.strip()}")
                print(f" {len(text)}c")
            else:
                print(" short")
        except Exception as e:
            print(f" err: {str(e)[:35]}")
    return texts

async def summarize_zai(text):
    z = ZAIChat(TOKEN)
    await z.start()
    prompt = f"""Summarize these Nepal & China news articles in bullet points grouped by theme.
Include source name and date (if found in text) for each point.

{text[:8000]}"""
    resp = await z.send(prompt)
    for _ in range(4):
        if "[at capacity]" not in resp and "[empty" not in resp:
            break
        avail = [m["id"] for m in z.available_models]
        cur = avail.index(z.model) if z.model in avail else -1
        nxt = avail[(cur + 1) % len(avail)]
        if nxt == z.model:
            break
        print(f"  {z.model} busy, trying {nxt}...")
        await asyncio.sleep(1)
        if not await z._change_model(nxt):
            continue
        resp = await z.send(prompt)
    await z.close()
    return resp

async def run():
    async with async_playwright() as p:
        profile_dir = os.path.join(os.path.dirname(__file__), "..", ".browser_profile")
        ctx = await p.chromium.launch_persistent_context(
            profile_dir, headless=False, viewport={"width":1280,"height":800},
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        all_results = []
        for q in SEARCHES:
            print(f"\nSearch: {q}")
            results = await google_search(page, q, 10)
            print(f"  Got {len(results)} results")
            for r in results:
                print(f"    - {r['title'][:70]}")
            all_results.extend(results)

        if not all_results:
            print("\nNo results. Captcha may still be blocking. Run again after solving once.")
            await ctx.close()
            return

        print(f"\nTotal: {len(all_results)} articles")
        texts = await extract_articles(page, all_results)
        await ctx.close()

    if not texts:
        print("No articles extracted."); return

    combined = "\n\n".join(texts)
    print(f"\n{len(combined)} chars. Summarizing via Z.ai...\n")
    summary = await summarize_zai(combined)
    print(f"\n{'='*60}\nSUMMARY\n{'='*60}\n{summary}")

asyncio.run(run())
