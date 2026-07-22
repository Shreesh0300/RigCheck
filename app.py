from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional
import os

from model.rigcheck_engine import recommend_game

# app.py should only deal with HTTP, validation, and routing. All AI/NLP logic lives in rigcheck_engine.
# This keeps the API thin and makes the core recommendation engine easy to test and reuse.

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request format
class UserInput(BaseModel):
    description: str = Field(..., min_length=1)
    budget: int = Field(..., ge=0)
    gpu_name: str = Field(..., min_length=1)
    ram: int = Field(..., ge=0)
    cpu_name: Optional[str] = None       # Phase 5: optional CPU name for compatibility eval
    storage_gb: Optional[float] = None   # Phase 5: optional free storage (GB)

# Home route - serve index.html
@app.get("/")
async def home():
    return FileResponse(os.path.join(os.path.dirname(__file__), "index.html"))

# Recommendation route
@app.post("/recommend")
def recommend(data: UserInput):
    try:
        return recommend_game(
            user_input=data.description,
            budget=data.budget,
            gpu_name=data.gpu_name,
            ram=data.ram,
            cpu_name=data.cpu_name,
            storage_gb=data.storage_gb,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Serve static files directly
@app.get("/style.css")
async def serve_css():
    return FileResponse(os.path.join(os.path.dirname(__file__), "style.css"), media_type="text/css")

@app.get("/script.js")
async def serve_js():
    return FileResponse(os.path.join(os.path.dirname(__file__), "script.js"), media_type="application/javascript")