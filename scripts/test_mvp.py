"""One-shot test using ZAIChat class."""
import asyncio
from zai_chat import ZAIChat

TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3MTAxMDVmLTA4ZDUtNGMzZi1iNzA0LTdjZjUwZWM0NmVkNCIsImVtYWlsIjoiYXJqdW4ueW9uemFuQGdtYWlsLmNvbSJ9.DaYGdldHCFsPbofOx11tHr-vo8nRJ5sOFeEBO3HKOBL8rz4CUQz0qi3Mi84RJ4XV62J5hUieuMr1w-Jcdo1inw"

async def run():
    client = ZAIChat(TOKEN)
    await client.start()
    msg = "Count from 1 to 3"
    print(f"You: {msg}")
    resp = await client.send(msg)
    print(f"Z: {resp[:500]}")
    await client.close()

asyncio.run(run())
