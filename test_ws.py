import asyncio, json
import websockets

async def test():
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as ws:
        with open("shell.json") as f:
            wf = json.load(f)
        await ws.send(json.dumps({"type":"START","workflow":wf}))
        print("Sent start, awaiting events…")

        for _ in range(2):
        # while True:
            msg = await ws.recv()
            print("←", msg)

        await ws.send(json.dumps({"type":"PAUSE"}))
        # print("Sent pause")

        await ws.send(json.dumps({"type":"RESUME"}))
        # print("Sent resume")

        # print("←", await ws.recv())
        while True:
            msg = await ws.recv()
            print("←", msg)
            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                continue
            if data.get("type") == "workflow_update" and data.get("status") == "COMPLETED":
                print("Workflow completed—closing connection.")
                break
        await ws.close()

if __name__ == "__main__":
    asyncio.run(test())
