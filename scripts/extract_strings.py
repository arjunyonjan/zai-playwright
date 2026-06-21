import asyncio
import json
import re
from playwright.async_api import async_playwright

with open("bundle.js", "r", encoding="utf-8") as f:
    bundle = f.read()

lx_match = re.search(r'function lx\(\)\s*\{const\s*t=\[(.*?)\];return\s*lx=function\(\)\{return\s*t\},lx\(\)\}', bundle, re.DOTALL)
if lx_match:
    strings_array_js = f"const _lx_array = [{lx_match.group(1)}];"
else:
    strings_array_js = "const _lx_array = [];"

JS_CODE = f"""
{strings_array_js}
function o(p) {{
    const h = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+/=";
    let m = "", v = "";
    for (let x = 0, k, w, C = 0; w = p.charAt(C++); 
         ~w && (k = x % 4 ? k * 64 + w : w, x++ % 4) ? 
         m += String.fromCharCode(255 & k >> (-2 * x & 6)) : 0) 
        w = h.indexOf(w);
    for (let x = 0, k = m.length; x < k; x++) 
        v += "%" + ("00" + m.charCodeAt(x).toString(16)).slice(-2);
    return decodeURIComponent(v);
}}

function f(p, h) {{
    let m = [], v = 0, x, k = "";
    p = o(p);
    let w;
    for (w = 0; w < 256; w++) m[w] = w;
    for (w = 0; w < 256; w++) {{
        v = (v + m[w] + h.charCodeAt(w % h.length)) % 256;
        x = m[w]; m[w] = m[v]; m[v] = x;
    }}
    w = 0; v = 0;
    for (let C = 0; C < p.length; C++) {{
        w = (w + 1) % 256;
        v = (v + m[w]) % 256;
        x = m[w]; m[w] = m[v]; m[v] = x;
        k += String.fromCharCode(p.charCodeAt(C) ^ m[(m[w] + m[v]) % 256]);
    }}
    return k;
}}

const keys = ['K31@', 'qbN@', 'n9jB', 'wM83', 'b(%A', 'cnLz', '^o$2', 'LWzn', 'HnEP', 'D(b)', 'RA87', 'OMw0', 'bqLL', 'nXkD'];
const results = [];
for (let i = 0; i < _lx_array.length; i++) {{
    for (const key of keys) {{
        try {{
            const decrypted = f(_lx_array[i], key);
            if (decrypted && decrypted.length > 2) {{
                results.push({{idx: i, key: key, value: decrypted}});
            }}
        }} catch(e) {{}}
    }}
}}
return results;
"""

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("about:blank")
        result = await page.evaluate(f"(function() {{{JS_CODE}}})()")
        
        seen = {}
        for r in result:
            key = (r['idx'], r['value'])
            if key not in seen:
                seen[key] = r
        
        for r in sorted(seen.values(), key=lambda x: (x['idx'], x['key'])):
            safe_value = r['value'].encode('utf-8', errors='replace').decode('utf-8', errors='replace')
            safe_value = ''.join(c if c.isprintable() else f'\\x{ord(c):02x}' for c in safe_value)
            print(f"[{r['idx']:3d}] key={r['key']!r}: {safe_value}")
        
        output = sorted(seen.values(), key=lambda x: x['idx'])
        with open("decrypted_strings.json", "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\nTotal: {len(seen)} decrypted strings")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
