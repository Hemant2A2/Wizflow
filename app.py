from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
# from engine import WorkFlow, WorkFlowEngine
import os
import json

class WizFlowBlueprint(BaseModel):
    blueprint: str

class CreateDirectory(BaseModel):
    workflowID: str
    userID: str


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

@app.post("/api/v1/directory")
async def create_directory(directory: CreateDirectory):
    base_dir = "uploads"
    user_dir = os.path.join(base_dir, directory.userID)
    workflow_dir = os.path.join(user_dir, directory.workflowID)
    
    os.makedirs(workflow_dir, exist_ok=True)

    return JSONResponse({
        "message": "Directory created successfully",
        "status_code": 200
    })

@app.post("/api/v1/upload")
async def upload_file(
    file: UploadFile = File(...),
    workflowID: str = Form(...),
    userID: str = Form(...)
):
    contents = await file.read()

    base_dir = "uploads"
    user_dir = os.path.join(base_dir, userID)
    workflow_dir = os.path.join(user_dir, workflowID)
    
    os.makedirs(workflow_dir, exist_ok=True)
    
    file_path = os.path.join(workflow_dir, file.filename)

    with open(file_path, "wb") as f:
        f.write(contents)

    return JSONResponse({
        "filename": file.filename,
        "saved_path": file_path,
        "content_type": file.content_type,
        "message": "File uploaded successfully",
        "status_code": 200
    })