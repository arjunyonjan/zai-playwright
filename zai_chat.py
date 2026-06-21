"""Z.ai chat — model selection, auto-retry, CDP-level response capture."""
import asyncio
import json
from playwright.async_api import async_playwright

TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3MTAxMDVmLTA4ZDUtNGMzZi1iNzA0LTdjZjUwZWM0NmVkNCIsImVtYWlsIjoiYXJqdW4ueW9uemFuQGdtYWlsLmNvbSJ9.DaYGdldHCFsPbofOx11tHr-vo8nRJ5sOFeEBO3HKOBL8rz4CUQz0qi3Mi84RJ4XV62J5hUieuMr1w-Jcdo1inw"

UI_NOISE = {"Chat", "Agent", "New Chat", "AI PPT", "New product", "OCR.z",
            "Image.z", "Audio.z", "AutoClaw", "Loading", "Arjun", "GLM-",
            "Previous ", "Click to enter", "Deep Think", "Max", "Share",
            "Thought Process", "Search"}


class ZAIChat:
    def __init__(self, token: str):
        self.token = token
        self.page = None
        self._pw_ctx = None
        self._browser = None
        self.model = "glm-4.7"
        self.model_name = ""
        self.available_models = []
        self._resp_future = None

    async def start(self):
        self._pw_ctx = async_playwright()
        self._pw = await self._pw_ctx.__aenter__()
        self._browser = await self._pw.chromium.launch(headless=False)
        self.page = await self._browser.new_page(viewport={"width": 1280, "height": 800})
        self.page.on("response", self._on_response)

        await self.page.goto("https://chat.z.ai", timeout=20000)
        await self.page.evaluate(f"localStorage.setItem('token', '{self.token}')")
        await self.page.reload(timeout=30000)
        await asyncio.sleep(3)

        self.available_models = await self.page.evaluate("""
            async () => {
                const token = localStorage.getItem('token');
                const r = await fetch('/api/models', {
                    headers: {'Authorization': 'Bearer ' + token}
                });
                const data = await r.json();
                return (data.data || []).map(m => ({id: m.id, name: m.name || m.id}));
            }
        """)

        available_ids = {m["id"] for m in self.available_models}
        for mid in ["glm-4.7", "GLM-5-Turbo", "glm-5.2", "GLM-5.1", "GLM-5V-Turbo"]:
            if mid in available_ids:
                self.model = mid
                break
        self.model_name = next(
            (m["name"] for m in self.available_models if m["id"] == self.model),
            self.model
        )
        print(f"Model: {self.model} ({self.model_name})")

    def _on_response(self, response):
        if "/chat/completions" in response.url and self._resp_future and not self._resp_future.done():
            self._resp_future.set_result(response)

    async def _change_model(self, model_id: str) -> bool:
        if model_id not in {m["id"] for m in self.available_models}:
            return False
        self.model = model_id
        self.model_name = next(
            (m["name"] for m in self.available_models if m["id"] == model_id), model_id
        )
        try:
            selector = await self.page.query_selector("button.modelSelectorButton")
            if not selector:
                return False
            await selector.click()
            await asyncio.sleep(0.5)
            menu = await self.page.wait_for_selector("[role='menu']", timeout=3000)
            if not menu:
                return False
            option = await menu.query_selector(f"button:has-text('{model_id}')")
            if option:
                await option.click()
                await asyncio.sleep(0.5)
                return True
        except Exception:
            pass
        return False

    async def send(self, message: str) -> str:
        self._resp_future = asyncio.get_running_loop().create_future()

        textarea = await self.page.wait_for_selector("#chat-input", timeout=5000)
        await textarea.click()
        await textarea.fill(message)
        await asyncio.sleep(0.3)
        send_btn = await self.page.query_selector("button[type='submit']:has(svg)")
        if send_btn and not await send_btn.is_disabled():
            await send_btn.click()
        else:
            await self.page.keyboard.press("Enter")

        try:
            response = await asyncio.wait_for(self._resp_future, timeout=60)
        except asyncio.TimeoutError:
            self._resp_future = None
            return "[timeout]"
        self._resp_future = None

        status = response.status
        if status != 200:
            return f"[HTTP {status}]"

        try:
            body = await asyncio.wait_for(response.text(), timeout=120)
        except asyncio.TimeoutError:
            return "[stream timeout]"

        if "MODEL_CONCURRENCY_LIMIT" in body:
            return f"[{self.model} at capacity]"

        answer = []
        for line in body.split("\n"):
            if line.startswith("data: ") and line != "data: [DONE]":
                try:
                    ev = json.loads(line[6:])
                    if ev.get("type") == "chat:completion":
                        answer.append(ev["data"].get("delta_content", ""))
                except Exception:
                    pass

        result = "".join(answer).strip()
        return result or "[empty response]"

    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._pw_ctx:
            await self._pw_ctx.__aexit__(None, None, None)


async def main():
    client = ZAIChat(TOKEN)
    await client.start()

    try:
        while True:
            msg = await asyncio.get_running_loop().run_in_executor(
                None, lambda: input("You: ")
            )
            if msg.lower() in ("/q", "/quit", "/exit"):
                break

            msg_lower = msg.lower()
            if msg_lower == "/models":
                print("Available models:")
                for m in client.available_models:
                    marker = " <--" if m["id"] == client.model else ""
                    print(f"  {m['id']:35s} {marker}")
                continue
            if msg_lower.startswith("/model "):
                mid = msg[7:].strip()
                if await client._change_model(mid):
                    print(f"Switched to {client.model}")
                else:
                    print(f"Model '{mid}' not found.")
                continue
            if msg.startswith("/"):
                print("Commands: /q, /models, /model <name>")
                continue

            resp = await client.send(msg)
            retries = 0
            while ("[at capacity]" in resp or resp == "[empty response]") and retries < 4:
                avail = [m["id"] for m in client.available_models]
                cur = avail.index(client.model) if client.model in avail else -1
                nxt = avail[(cur + 1) % len(avail)]
                if nxt == client.model:
                    break
                print(f"  {client.model} busy, trying {nxt}...")
                await asyncio.sleep(1)
                if not await client._change_model(nxt):
                    retries += 1
                    continue
                resp = await client.send(msg)
                retries += 1

            print(f"Z: {resp}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
