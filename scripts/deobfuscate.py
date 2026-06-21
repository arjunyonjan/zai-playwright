import sys
import re
import base64
import json
import urllib.parse

sys.stdout.reconfigure(encoding='utf-8')

with open("bundle.js", "r", encoding="utf-8") as f:
    js = f.read()

# Extract the string array from lx() function
match = re.search(r'function lx\(\)\s*\{const\s*t=\[(.*?)\];return\s*lx=function\(\)\{return\s*t\},lx\(\)\}', js, re.DOTALL)
if match:
    raw = match.group(1)
    strings = re.findall(r'"((?:[^"\\]|\\.)*)"', raw)
    print(f"Extracted {len(strings)} obfuscated strings")
else:
    print("Could not find string array")
    strings = []

# Custom base64 decoder (matches JS o() function)
CUSTOM_B64 = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+/="

def custom_b64_decode(s):
    m = ""
    v = ""
    x = 0
    k = 0
    w = None
    for C, ch in enumerate(s):
        idx = CUSTOM_B64.find(ch)
        if idx != -1:
            w = idx
            if x % 4:
                k = k * 64 + w
            else:
                k = w
            x += 1
            if x % 4 == 0:
                m += chr(255 & (k >> (-2 * (x % 4 - 1) & 6)))
    # URL decode the result
    return urllib.parse.unquote(m)

# RC4 decryption (matches JS f() function)
def rc4_decrypt(p, key):
    # p is already decoded string from custom_b64_decode
    S = list(range(256))
    v = 0
    for i in range(256):
        v = (v + S[i] + ord(key[i % len(key)])) % 256
        S[i], S[v] = S[v], S[i]
    
    i = 0
    v = 0
    result = []
    for C in range(len(p)):
        i = (i + 1) % 256
        v = (v + S[i]) % 256
        S[i], S[v] = S[v], S[i]
        result.append(ord(p[C]) ^ S[(S[i] + S[v]) % 256])
    
    return bytes(result).decode('utf-8', errors='replace')

# Keys used in Lc calls
keys_to_try = ["K31@", "qbN@", "n9jB", "wM83", "b(%A", "cnLz", "^o$2", "LWzn", "HnEP", "D(b)"]

print("=== Decrypting strings ===")
for i, s in enumerate(strings):
    for key in keys_to_try:
        try:
            decoded_b64 = custom_b64_decode(s)
            decrypted = rc4_decrypt(decoded_b64, key)
            if decrypted and len(decrypted) > 2 and not decrypted.startswith('\ufffd'):
                safe = decrypted.encode('utf-8', errors='replace').decode('utf-8')
                print(f"[{i:3d}] key={key!r}: {safe}")
        except Exception as e:
            pass
