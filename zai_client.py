"""Z.ai chat client — handles HMAC signing and streaming chat."""
import hashlib
import hmac
import json
import base64
import time
import uuid
import httpx

BASE = "https://chat.z.ai"
HMAC_SECRET = "key-@@@@)))()((9))-xxxx&&&%%%%%"

def compute_signature(sorted_payload: str, prompt_text: str, timestamp: int) -> str:
    """Compute HMAC-SHA256 signature (matches fre() in the JS bundle)."""
    prompt_bytes = prompt_text.encode("utf-8")
    chunk_size = 32768
    chunks = []
    for i in range(0, len(prompt_bytes), chunk_size):
        chunks.append(prompt_bytes[i:i+chunk_size])
    # Convert bytes to string via latin-1 (treat bytes as chars), then base64
    base64_str = base64.b64encode(b"".join(chunks)).decode()
    
    payload_to_sign = f"{sorted_payload}|{base64_str}|{timestamp}"
    
    time_window = timestamp // (5 * 60 * 1000)
    session_key = hmac.new(
        HMAC_SECRET.encode(),
        str(time_window).encode(),
        hashlib.sha256
    ).hexdigest()
    
    signature = hmac.new(
        session_key.encode(),
        payload_to_sign.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return signature

class ZAIClient:
    def __init__(self, token: str):
        self.token = token
        self.client = httpx.Client(follow_redirects=True, base_url=BASE)
    
    def get_models(self) -> list:
        r = self.client.get("/api/models", headers=self._headers())
        r.raise_for_status()
        return r.json()["data"]
    
    def _headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
    
    def _build_url_params(self, user_id: str = "") -> tuple[str, str, str]:
        """Build sorted payload, URL params, and timestamp (matches dre())."""
        ts = int(time.time() * 1000)
        request_id = str(uuid.uuid4())
        
        payload = [
            ("requestId", request_id),
            ("timestamp", str(ts)),
            ("user_id", user_id),
        ]
        sorted_payload = ",".join(f"{k}={v}" for k, v in sorted(payload))
        url_params = "&".join(f"{k}={v}" for k, v in sorted(payload))
        
        return sorted_payload, url_params, str(ts)
    
    def chat_completion(self, model: str, messages: list, stream: bool = False):
        prompt_text = messages[-1]["content"] if messages else ""
        
        sorted_payload, url_params, ts = self._build_url_params()
        signature = compute_signature(sorted_payload, prompt_text, int(ts))
        
        body = {
            "stream": stream,
            "model": model,
            "messages": messages,
            "signature_prompt": prompt_text,
        }
        
        qs = f"{url_params}&signature_timestamp={ts}"
        # Try v2 endpoint first (used by newer completion_version)
        url = f"/api/v2/chat/completions?{qs}"
        
        headers = self._headers()
        headers["X-FE-Version"] = "prod-fe-1.1.66"
        headers["X-Signature"] = signature
        
        if stream:
            return self._stream(url, headers, body)
        else:
            r = self.client.post(url, headers=headers, json=body, timeout=30)
            r.raise_for_status()
            return r.json()
    
    def _stream(self, url, headers, body):
        with self.client.stream("POST", url, headers=headers, json=body, timeout=60) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    yield json.loads(data)


if __name__ == "__main__":
    TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3MTAxMDVmLTA4ZDUtNGMzZi1iNzA0LTdjZjUwZWM0NmVkNCIsImVtYWlsIjoiYXJqdW4ueW9uemFuQGdtYWlsLmNvbSJ9.DaYGdldHCFsPbofOx11tHr-vo8nRJ5sOFeEBO3HKOBL8rz4CUQz0qi3Mi84RJ4XV62J5hUieuMr1w-Jcdo1inw"
    client = ZAIClient(TOKEN)
    
    models = client.get_models()
    print(f"Available models: {[m['id'] for m in models]}")
    
    if models:
        model_id = models[0]["id"]
        print(f"\nSending message to {model_id}...")
        r = client.chat_completion(model_id, [
            {"role": "user", "content": "Say hello in one word"}
        ], stream=False)
        print(f"Response: {json.dumps(r, indent=2)[:500]}")
