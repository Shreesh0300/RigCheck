from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional
import os

from model.rigcheck_engine import recommend_game
from model.steam_database import get_all_games, get_game_by_appid, search_games, get_database_stats

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

# --- Steam Database API Endpoints ---

@app.get("/games")
def get_games(limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
    games = get_all_games()
    paginated = games[offset:offset+limit]
    
    result = []
    for g in paginated:
        result.append({
            "appid": g.get("appid"),
            "name": g.get("name"),
            "short_description": g.get("short_description"),
            "genres": g.get("genres", []),
            "price": g.get("price_overview", {}),
            "is_free": g.get("is_free", False),
            "header_image": g.get("header_image"),
            "release_date": g.get("release_date")
        })
    return result

@app.get("/games/{appid}")
def get_game(appid: int):
    game = get_game_by_appid(appid)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
        
    return {
        "appid": game.get("appid"),
        "name": game.get("name"),
        "description": game.get("short_description"),
        "developers": game.get("developers", []),
        "publishers": game.get("publishers", []),
        "genres": game.get("genres", []),
        "categories": game.get("categories", []),
        "release_date": game.get("release_date"),
        "screenshots": game.get("screenshots", []),
        "trailers": game.get("trailers", []),
        "supported_platforms": game.get("platforms", {}),
        "minimum_requirements": game.get("minimum", {}),
        "recommended_requirements": game.get("recommended", {}),
        "header_image": game.get("header_image"),
        "capsule_image": game.get("header_image"), # Fallback since we didn't extract capsule_image
        "website": game.get("website"),
        "price": game.get("price_overview", {}),
        "is_free": game.get("is_free", False)
    }

@app.get("/search")
def search(q: str = Query(..., min_length=1), limit: int = Query(20, ge=1, le=100)):
    results = search_games(q)
    paginated = results[:limit]
    
    response = []
    for g in paginated:
        response.append({
            "appid": g.get("appid"),
            "name": g.get("name"),
            "header_image": g.get("header_image"),
            "genres": g.get("genres", []),
            "short_description": g.get("short_description"),
            "is_free": g.get("is_free", False)
        })
    return response

@app.get("/stats")
def get_stats():
    stats = get_database_stats()
    games = get_all_games()
    
    images_count = sum(1 for g in games if g.get("header_image") or g.get("screenshots"))
    trailers_count = sum(1 for g in games if g.get("trailers"))
    
    return {
        "games": stats.get("total_games", 0),
        "games_with_requirements": stats.get("with_minimum_reqs", 0),
        "games_with_images": images_count,
        "games_with_trailers": trailers_count,
        "games_with_prices": stats.get("with_price_data", 0)
    }