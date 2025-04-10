import json
import asyncio
import logging
from threading import Thread
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from engine import WorkflowEngine
from logging_config import setup_logging

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

redis_client: Redis
engines: dict[str, WorkflowEngine] = {}

@app.on_event("startup")
async def startup_event():
    global redis_client
    log_file = "logs/workflow.log"
    if os.path.exists(log_file):
        open(log_file, "w").close()
    setup_logging(log_file="logs/workflow.log")
    logging.getLogger("uvicorn").info("Logging initialized, writing to logs/workflow.log")
    redis_client = Redis(host="localhost", port=6379, db=0, decode_responses=True)

@app.websocket("/ws")
async def workflow_ws(websocket: WebSocket):
    await websocket.accept()
    wf_id = None
    pubsub = None

    try:
        while True:
            ws_task = asyncio.create_task(websocket.receive_text())
            ps_task = None
            if pubsub:
                ps_task = asyncio.create_task(pubsub.get_message(ignore_subscribe_messages=True))

            done, pending = await asyncio.wait(
                [t for t in (ws_task, ps_task) if t],
                return_when=asyncio.FIRST_COMPLETED,
            )

            if ws_task in done:
                text = ws_task.result()
                msg = json.loads(text)
                typ = msg.get("type")

                # start workflow
                if typ == "START":
                    # logging.getLogger("uvicorn").info(msg)
                    wf_data = msg["workflow"]
                    wf_json = wf_data
                    if isinstance(wf_data, str):
                        wf_json = json.loads(wf_data)
                    engine = WorkflowEngine(wf_json)
                    engine.export_dag()
                    wf_id = engine.wf_key
                    engines[wf_id] = engine

                    pubsub = redis_client.pubsub()
                    await pubsub.subscribe(f"wf:{wf_id}:events")

                    max_workers = engine.estimate_max_workers()
                    Thread(
                        target=lambda: engine.run_parallel(max_workers=max_workers),
                        daemon=True
                    ).start()

                    await websocket.send_json({
                        "type": "workflow_started",
                        "workflow_id": wf_id
                    })

                # pause/resume/restart
                elif typ in ("PAUSE", "RESUME", "RESTART"):
                    if not wf_id or wf_id not in engines:
                        await websocket.send_json({
                            "type": "error",
                            "message": "No active workflow"
                        })
                    else:
                        engine = engines[wf_id]
                        if typ == "PAUSE":
                            engine.pause()
                        elif typ == "RESUME":
                            engine.resume()
                        elif typ == "RESTART":
                            from_task = msg.get("from_task")
                            engine.restart(from_task)
                            max_workers = engine.estimate_max_workers()
                            Thread(
                                target=lambda: engine.run_parallel(max_workers=max_workers),
                                daemon=True
                            ).start()

                        await websocket.send_json({
                            "type": f"{typ}_ack",
                            "workflow_id": wf_id
                        })
                if ps_task:
                    ps_task.cancel()

            elif ps_task in done:
                event = ps_task.result()
                # {"type":"message","pattern":None,"channel":"...","data":"..."}
                if event and event.get("data"):
                    payload = event["data"]
                    await websocket.send_text(payload)
                    try:
                        data = json.loads(payload)
                    except json.JSONDecodeError:
                        data = {}
                    if data.get("type") == "workflow_update" and data.get("status") == "COMPLETED":
                        engine = engines.get(wf_id)
                        if engine:
                            leaf_tasks = [tid for tid, children in engine.dag.items() if not children]
                            final_outputs = {
                                tid: engine.results.get(tid)
                                for tid in leaf_tasks
                            }
                            await websocket.send_json({
                                "type": "workflow_output",
                                "outputs": final_outputs
                            })
                ws_task.cancel()

            for task in pending:
                task.cancel()

    except WebSocketDisconnect:
        if pubsub and wf_id:
            await pubsub.unsubscribe(f"wf:{wf_id}:events")
