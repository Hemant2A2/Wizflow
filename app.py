from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json

class WizFlowBlueprint(BaseModel):
    blueprint: str

app = FastAPI(
    title="WizFlow API",
    description="API for WizFlow application",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def read_root():
    return {
        "title": app.title,
        "description": app.description,
        "version": app.version,
        "status": "Running",
    }

@app.post("/api/v1/execute")
async def execute_task(payload: WizFlowBlueprint):  
    try:
        blueprint = json.loads(payload.blueprint)
        print(f"Received blueprint: {blueprint}")
        with open(f"{blueprint['workflow_name']}.json", "w") as f:
            json.dump(blueprint, f)

        return {
            "status": "success",
            "message": "Task executed successfully",
            "status_code": 200,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
