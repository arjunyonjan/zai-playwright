import re
with open('bundle.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Extract the xfe function (chat completion with PoW)
idx = content.find('xfe=async(t="",e,r=`${xn}/api`')
if idx == -1:
    idx = content.find('chat/completions')

# Read a large chunk around this area
start = max(0, idx - 200)
end = min(len(content), idx + 3000)
section = content[start:end]

# Decode and print safely
lines = []
current = ''
for c in section:
    if 32 <= ord(c) < 127:
        current += c
    else:
        if current:
            lines.append(current)
        current = ''
if current:
    lines.append(current)

for line in lines:
    print(line)
