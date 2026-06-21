import json

with open("decrypted_strings.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# For each index, find the valid reading (ASCII printable)
valid = {}
for r in data:
    idx, key, value = r['idx'], r['key'], r['value']
    # Check if string is mostly printable ASCII
    printable_count = sum(1 for c in value if 32 <= ord(c) < 127 or c in '\n\r\t')
    if printable_count >= len(value) * 0.8 and len(value) >= 2:
        if idx not in valid or len(value) > len(valid[idx]['value']):
            valid[idx] = r

print(f"=== {len(valid)} valid decrypted strings ===\n")
for k in sorted(valid.keys()):
    v = valid[k]
    print(f"[{k:3d}] key={v['key']!r}: {v['value']}")

# Also save mapping
with open("string_map.json", "w", encoding="utf-8") as f:
    json.dump({str(k): {"key": valid[k]["key"], "value": valid[k]["value"]} for k in sorted(valid.keys())}, 
              f, indent=2, ensure_ascii=False)
