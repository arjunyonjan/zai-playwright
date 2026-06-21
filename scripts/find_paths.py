import re
with open('bundle.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Search for chat-related fetch with template strings (backtick)
for m in re.finditer(r'`\$\{.*?\}/chat[^`]*`', content):
    print(m.group(0)[:200])
    # Show some surrounding context
    start = max(0, m.start() - 100)
    snippet = content[start:m.end()+50]
    safe = ''.join(c if 32 <= ord(c) < 127 else ' ' for c in snippet)
    print(f'  ...{safe}...')
    print()
