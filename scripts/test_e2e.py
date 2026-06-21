"""Full end-to-end test: start, select model, send, retry on capacity."""
import asyncio, sys
sys.path.insert(0, ".")
from zai_chat import ZAIChat, MODEL_PRIORITY

TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3MTAxMDVmLTA4ZDUtNGMzZi1iNzA0LTdjZjUwZWM0NmVkNCIsImVtYWlsIjoiYXJqdW4ueW9uemFuQGdtYWlsLmNvbSJ9.DaYGdldHCFsPbofOx11tHr-vo8nRJ5sOFeEBO3HKOBL8rz4CUQz0qi3Mi84RJ4XV62J5hUieuMr1w-Jcdo1inw"

async def run():
    c = ZAIChat(TOKEN)
    await c.start()
    print()

    msg = "Count from 1 to 5"
    resp = await c.send(msg)

    retries = 0
    while "[at capacity]" in resp and retries < len(MODEL_PRIORITY):
        current_model = c.model
        available_ids = [m["id"] for m in c.available_models]
        current_idx = available_ids.index(current_model) if current_model in available_ids else -1
        next_idx = (current_idx + 1) % len(available_ids)
        next_model = available_ids[next_idx]

        if next_model == current_model:
            print(f"All models at capacity.")
            break

        print(f"  {current_model} at capacity, trying {next_model}...")
        await asyncio.sleep(1)
        switched = await c._change_model(next_model)
        if not switched:
            print(f"  {next_model} not available, skipping...")
            retries += 1
            continue
        resp = await c.send(msg)
        retries += 1

    if "[at capacity]" in resp:
        print(f"Failed: {resp}")
    else:
        print(f"\n=== RESPONSE ===\n{resp[:1000]}")

    await c.close()

asyncio.run(run())
