"""GitHub Trending — scrape today's repos with language + stars."""
import asyncio
from playwright.async_api import async_playwright

def safe(s):
    return s.encode('ascii', 'replace').decode() if s else ''

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://github.com/trending", timeout=15000)
        await page.wait_for_timeout(2000)

        repos = await page.evaluate("""
            () => Array.from(document.querySelectorAll('article.Box-row')).slice(0, 15).map(article => ({
                name: article.querySelector('h2 a')?.textContent?.trim().replace(/\\s+/g, ' ') || '',
                description: article.querySelector('p')?.textContent?.trim() || '',
                language: article.querySelector('[itemprop="programmingLanguage"]')?.textContent?.trim() || '',
                stars: article.querySelector('[href$="/stargazers"]')?.textContent?.trim() || '',
                today_stars: article.querySelector('span.d-inline-block.float-sm-right')?.textContent?.trim()?.replace('stars today','')?.trim() || '',
            }))
        """)

        print(f"\n{'='*60}")
        print(f"  GITHUB TRENDING — TODAY")
        print(f"{'='*60}\n")

        for i, r in enumerate(repos, 1):
            print(f"{i:2d}. {safe(r['name'])}")
            if r['description']:
                print(f"     {safe(r['description'][:100])}")
            line = f"     stars: {safe(r['stars'])}"
            if r['today_stars']:
                line += f"  +{safe(r['today_stars'])} today"
            if r['language']:
                line += f"  lang: {safe(r['language'])}"
            print(line)
            print()

        await browser.close()

asyncio.run(run())
