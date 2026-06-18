from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
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
    gpu_tier: int = Field(..., ge=0)
    ram: int = Field(..., ge=0)

# Home route - serve index.html
@app.get("/")
async def home():
    return FileResponse(os.path.join(os.path.dirname(__file__), "index.html"))

# Recommendation route
@app.post("/recommend")
def recommend(data: UserInput):
    return recommend_game(
        user_input=data.description,
        budget=data.budget,
        gpu_tier=data.gpu_tier,
        ram=data.ram,
    )

# Serve static files directly
@app.get("/style.css")
async def serve_css():
    return FileResponse(os.path.join(os.path.dirname(__file__), "style.css"), media_type="text/css")

@app.get("/script.js")
async def serve_js():
    return FileResponse(os.path.join(os.path.dirname(__file__), "script.js"), media_type="application/javascript")