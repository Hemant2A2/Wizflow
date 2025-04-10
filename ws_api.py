import aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
from threading import Thread
from engine import WorkflowEngine

app = FastAPI(
    title="WizFlow Ws API",
    description="WS_API for WizFlow application",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_pubsub = None
engines = {} 

@app.on_event("startup")
async def startup_event():
    global redis_pubsub
    redis_pubsub = await aioredis.create_redis_pool("redis://localhost")

@app.websocket("/ws")
async def workflow_ws(websocket: WebSocket):
    await websocket.accept()
    wf_id = None
    channel = None

    try:
        while True:
            done, pending = await asyncio.wait(
                [
                    asyncio.create_task(websocket.receive_text()),
                    asyncio.create_task((channel.get() if channel else asyncio.Future()))
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in done:
                if task in pending:
                    continue
                res = task.result()

                if isinstance(res, str):
                    msg = json.loads(res)
                    typ = msg.get("type")

                    # start workflow
                    if typ == "start":
                        wf_json = msg["workflow"]
                        engine = WorkflowEngine(wf_json)
                        wf_id = engine.wf_key
                        engines[wf_id] = engine
                        ps = await redis_pubsub.subscribe(f"wf:{wf_id}:events")
                        channel = ps[0]
                        Thread(target=engine.run_parallel, daemon=True).start()
                        await websocket.send_json({
                            "type": "workflow_started",
                            "workflow_id": wf_id
                        })

                    # pause / resume / restart
                    elif typ in ("pause", "resume", "restart"):
                        if not wf_id or wf_id not in engines:
                            await websocket.send_json({"type":"error","message":"No active workflow"})
                            continue
                        engine = engines[wf_id]
                        if typ == "pause":
                            engine.pause()
                        elif typ == "resume":
                            engine.resume()
                        else:
                            from_task = msg.get("from_task")
                            engine.restart(from_task)
                            Thread(target=engine.run_parallel, daemon=True).start()
                        await websocket.send_json({
                            "type": f"{typ}_ack",
                            "workflow_id": wf_id
                        })
                else:
                    msg_bytes = res
                    if msg_bytes:
                        await websocket.send_text(msg_bytes.decode())

            for p in pending:
                p.cancel()

    except WebSocketDisconnect:
        if channel and wf_id:
            await redis_pubsub.unsubscribe(f"wf:{wf_id}:events")