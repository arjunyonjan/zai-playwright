"""Fetch available models from Z.ai API."""
import json, httpx

TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3MTAxMDVmLTA4ZDUtNGMzZi1iNzA0LTdjZjUwZWM0NmVkNCIsImVtYWlsIjoiYXJqdW4ueW9uemFuQGdtYWlsLmNvbSJ9.DaYGdldHCFsPbofOx11tHr-vo8nRJ5sOFeEBO3HKOBL8rz4CUQz0qi3Mi84RJ4XV62J5hUieuMr1w-Jcdo1inw"

r = httpx.get("https://chat.z.ai/api/models", headers={"Authorization": f"Bearer {TOKEN}"})
data = r.json()
models = data.get("data", [])
print(f"Total models: {len(models)}")
for m in models:
    info = m.get("info", {})
    meta = info.get("meta", {})
    caps = meta.get("capabilities", {})
    tags = list(caps.keys()) if caps else []
    print(f"  {m['id']:35s} | {m.get('name',''):20s} | tags: {tags}")
