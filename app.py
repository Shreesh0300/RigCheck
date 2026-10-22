from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
import os
import urllib.parse

from model.rigcheck_engine import recommend_game
from model.steam_database import get_all_games, get_game_by_appid, search_games, get_database_stats
from db import init_db
from auth import (
    UserAuthRequest,
    register_user,
    authenticate_user,
    create_user_session,
    get_session_user,
    invalidate_session,
    SESSION_COOKIE_NAME,
    is_google_configured,
    generate_google_auth_url,
    handle_google_callback,
    generate_steam_login_url,
    handle_steam_callback,
)

# app.py should only deal with HTTP, validation, and routing. All AI/NLP logic lives in rigcheck_engine.
# This keeps the API thin and makes the core recommendation engine easy to test and reuse.

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    await init_db()

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

# --- User Authentication & Session Endpoints ---

@app.get("/auth/status")
async def auth_status():
    """Checks provider availability (e.g. whether Google credentials are set)."""
    return {
        "google_configured": is_google_configured(),
        "steam_configured": True,
    }

@app.get("/auth/me")
async def get_current_user_profile(request: Request):
    """Returns the authenticated user for the active session, if any."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        # Check Authorization header as fallback
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    user = await get_session_user(token) if token else None
    if not user:
        return {"authenticated": False, "user": None}
    return {"authenticated": True, "user": user}

@app.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Terminates session and clears session cookie."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        await invalidate_session(token)
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return {"success": True, "message": "Logged out successfully"}

@app.post("/auth/register")
async def register(data: UserAuthRequest, response: Response):
    try:
        user = await register_user(email=data.email, password=data.password)
        token = await create_user_session(user["id"])
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=token,
            httponly=True,
            samesite="lax",
            max_age=14 * 24 * 3600,
            path="/"
        )
        return {"success": True, "message": "Account created successfully!", "user": user, "token": token}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/auth/login")
async def login(data: UserAuthRequest, response: Response):
    try:
        user = await authenticate_user(email=data.email, password=data.password)
        token = await create_user_session(user["id"])
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=token,
            httponly=True,
            samesite="lax",
            max_age=14 * 24 * 3600,
            path="/"
        )
        return {"success": True, "message": "Login successful!", "user": user, "token": token}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")

def get_client_base_url(request: Request) -> str:
    """Returns the base frontend URL (e.g. http://localhost:5173) for OAuth returns."""
    from auth import FRONTEND_URL
    if FRONTEND_URL:
        return FRONTEND_URL.rstrip("/")
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "localhost:5173")
    proto = request.headers.get("x-forwarded-proto") or ("https" if request.url.is_secure else "http")
    return f"{proto}://{host}"

# --- Google OAuth 2.0 / OpenID Connect Endpoints ---

@app.get("/auth/google/login")
async def google_login(request: Request):
    """Initiates Google OAuth 2.0 / OpenID flow."""
    if not is_google_configured():
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "Google OAuth is not configured. Please add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to .env."
            }
        )
    try:
        base_url = get_client_base_url(request)
        redirect_uri = f"{base_url}/auth/google/callback"
        url, _ = generate_google_auth_url(redirect_uri=redirect_uri)
        return RedirectResponse(url)
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.get("/auth/google/callback")
async def google_callback(request: Request):
    """Handles Google OAuth callback, verifies identity, establishes session."""
    base_url = get_client_base_url(request)
    query = request.query_params
    if query.get("error"):
        error_reason = query.get("error_description") or query.get("error")
        return RedirectResponse(f"{base_url}/?auth_error={urllib.parse.quote(f'Google authentication error: {error_reason}')}")

    code = query.get("code")
    if not code:
        return RedirectResponse(f"{base_url}/?auth_error=Missing+Google+authorization+code")

    try:
        redirect_uri = f"{base_url}/auth/google/callback"
        user = await handle_google_callback(code=code, redirect_uri=redirect_uri)
        token = await create_user_session(user["id"])
        
        resp = RedirectResponse(f"{base_url}/?login_success=true")
        resp.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=token,
            httponly=True,
            samesite="lax",
            max_age=14 * 24 * 3600,
            path="/"
        )
        return resp
    except Exception as e:
        return RedirectResponse(f"{base_url}/?auth_error={urllib.parse.quote(str(e))}")

# --- Steam OpenID 2.0 Endpoints ---

@app.get("/auth/steam/login")
async def steam_login(request: Request):
    """Initiates official Steam OpenID 2.0 authentication flow."""
    base_url = get_client_base_url(request)
    return_url = f"{base_url}/auth/steam/callback"
    url = generate_steam_login_url(return_url=return_url, realm=base_url)
    return RedirectResponse(url)

@app.get("/auth/steam/callback")
async def steam_callback(request: Request):
    """Validates Steam OpenID assertion with Steam servers, finds/creates user in MongoDB, sets session."""
    base_url = get_client_base_url(request)
    query_dict = dict(request.query_params)
    if query_dict.get("openid.mode") == "cancel":
        return RedirectResponse(f"{base_url}/?auth_error=Steam+login+was+cancelled")

    try:
        user = await handle_steam_callback(query_dict)
        token = await create_user_session(user["id"])
        
        resp = RedirectResponse(f"{base_url}/?login_success=true")
        resp.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=token,
            httponly=True,
            samesite="lax",
            max_age=14 * 24 * 3600,
            path="/"
        )
        return resp
    except Exception as e:
        return RedirectResponse(f"{base_url}/?auth_error={urllib.parse.quote(str(e))}")

