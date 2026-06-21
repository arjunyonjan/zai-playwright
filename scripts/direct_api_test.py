"""Test direct API calls with JWT token to understand Z.ai's chat API."""
import httpx
import json

TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3MTAxMDVmLTA4ZDUtNGMzZi1iNzA0LTdjZjUwZWM0NmVkNCIsImVtYWlsIjoiYXJqdW4ueW9uemFuQGdtYWlsLmNvbSJ9.DaYGdldHCFsPbofOx11tHr-vo8nRJ5sOFeEBO3HKOBL8rz4CUQz0qi3Mi84RJ4XV62J5hUieuMr1w-Jcdo1inw"
BASE = "https://chat.z.ai"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# Step 1: Try getting available models
print("=== GET /api/v1/models ===")
r = httpx.get(f"{BASE}/api/v1/models", headers=headers, timeout=10)
print(f"Status: {r.status_code}")
print(json.dumps(r.json(), indent=2)[:1000])

# Step 2: Try a simple chat completion
print("\n=== POST /api/v1/chat/completions ===")
body = {
    "model": "glm-5-0529",  # guess
    "messages": [{"role": "user", "content": "say hello"}],
    "stream": False,
}
r = httpx.post(f"{BASE}/api/v1/chat/completions", headers=headers, json=body, timeout=15)
print(f"Status: {r.status_code}")
try:
    print(r.text[:1000])
except:
    print(r.text[:200])
