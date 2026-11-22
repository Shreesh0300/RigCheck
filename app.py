from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
import os
import secrets
import urllib.parse
from bson import ObjectId

from model.rigcheck_engine import recommend_game
from model.personalized_engine import generate_personalized_feed
from model.steam_database import get_all_games, get_game_by_appid, search_games, get_database_stats
from db import init_db
from auth import (
    UserAuthRequest,
    register_user,
    authenticate_user,
    create_user_session,
    optional_session_user,
    require_authenticated_user,
    require_csrf,
    invalidate_session,
    SESSION_COOKIE_NAME,
    CSRF_COOKIE_NAME,
    SESSION_DURATION_DAYS,
    generate_csrf_token,
    is_google_configured,
    generate_google_auth_url,
    handle_google_callback,
    generate_steam_login_url,
    handle_steam_callback,
    AuthenticatedUser,
)
from user_activity import (
    get_library_state,
    get_user_library,
    update_library_state,
    remove_library_state,
    serialize_activity,
    submit_review,
    delete_user_review,
    get_public_reviews,
    report_public_review,
    get_user_preferences,
    update_user_preferences,
    record_ai_query,
    get_user_ai_history,
    delete_user_ai_history,
    record_ai_interaction,
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

# Home and SPA routes - serve index.html
@app.get("/")
@app.get("/for-you")
@app.get("/my-games")
async def home():
    return FileResponse(os.path.join(os.path.dirname(__file__), "index.html"))

# Recommendation route
@app.post("/recommend")
async def recommend(data: UserInput, user=Depends(optional_session_user)):
    try:
        rec = recommend_game(
            user_input=data.description,
            budget=data.budget,
            gpu_name=data.gpu_name,
            ram=data.ram,
            cpu_name=data.cpu_name,
            storage_gb=data.storage_gb,
        )
        if user and user.get("id"):
            try:
                rec_appid = rec.get("appid")
                alt_appids = [g["appid"] for g in rec.get("alternative_games", []) if "appid" in g]
                auth_user = AuthenticatedUser(ObjectId(user["id"]))
                query_record = await record_ai_query(
                    user=auth_user,
                    query=data.description,
                    recommended_appid=rec_appid,
                    alternative_appids=alt_appids,
                    budget=data.budget,
                    gpu_name=data.gpu_name,
                    ram=data.ram,
                    cpu_name=data.cpu_name,
                    storage_gb=data.storage_gb,
                )
                rec["query_id"] = query_record.get("id")
            except Exception:
                # Do not block recommendation if recording fails
                pass
        return rec
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
        "capsule_image": game.get("header_image"),
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
async def get_current_user_profile(request: Request, response: Response, user=Depends(optional_session_user)):
    """Returns the authenticated user for the active session, if any."""
    response.headers["Cache-Control"] = "no-store"
    if not user:
        return {"authenticated": False, "user": None}
    csrf_token = request.cookies.get(CSRF_COOKIE_NAME)
    if not csrf_token:
        csrf_token = generate_csrf_token()
        response.set_cookie(
            CSRF_COOKIE_NAME,
            csrf_token,
            httponly=False,
            samesite="lax",
            secure=use_secure_cookie(request),
            max_age=SESSION_DURATION_DAYS * 86400,
            path="/",
        )
    return {"authenticated": True, "user": user, "csrf_token": csrf_token}

@app.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Terminates session and clears session cookie."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        await invalidate_session(token)
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return {"success": True, "message": "Logged out successfully"}

@app.post("/auth/register")
async def register(data: UserAuthRequest, request: Request, response: Response):
    try:
        user = await register_user(email=data.email, password=data.password)
        return await login_response(user, "Account created successfully!", request, response)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Registration failed")

@app.post("/auth/login")
async def login(data: UserAuthRequest, request: Request, response: Response):
    try:
        user = await authenticate_user(email=data.email, password=data.password)
        return await login_response(user, "Login successful!", request, response)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Authentication failed")

def use_secure_cookie(request: Request) -> bool:
    from auth import FRONTEND_URL
    return request.url.scheme == "https" or urllib.parse.urlsplit(FRONTEND_URL).scheme == "https"

async def set_session_cookie(user: dict, request: Request, response: Response) -> str:
    token = await create_user_session(user["id"])
    response.headers["Cache-Control"] = "no-store"
    response.set_cookie(SESSION_COOKIE_NAME, token, httponly=True, samesite="lax",
                        secure=use_secure_cookie(request), max_age=SESSION_DURATION_DAYS * 86400, path="/")
    csrf_token = generate_csrf_token()
    response.set_cookie(CSRF_COOKIE_NAME, csrf_token, httponly=False, samesite="lax",
                        secure=use_secure_cookie(request), max_age=SESSION_DURATION_DAYS * 86400, path="/")
    return token

async def login_response(user: dict, message: str, request: Request, response: Response):
    token = await set_session_cookie(user, request, response)
    result = {"success": True, "message": message, "user": user}
    if request.headers.get("X-Session-Mode") != "cookie":
        result["token"] = token
    return result

def get_client_base_url(request: Request) -> str:
    """Returns the base frontend URL (e.g. http://localhost:5173) for OAuth returns."""
    from auth import FRONTEND_URL
    if FRONTEND_URL:
        return FRONTEND_URL.rstrip("/")
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "localhost:5173")
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    return f"{proto}://{host}"

# --- Google OAuth 2.0 / OpenID Connect Endpoints ---
GOOGLE_STATE_COOKIE = "rigcheck_google_state"
GOOGLE_CALLBACK_PATH = "/auth/google/callback"

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
        url, state = generate_google_auth_url(redirect_uri=redirect_uri)
        response = RedirectResponse(url)
        response.headers["Cache-Control"] = "no-store"
        response.set_cookie(GOOGLE_STATE_COOKIE, state, max_age=600, path=GOOGLE_CALLBACK_PATH,
                            httponly=True, secure=use_secure_cookie(request), samesite="lax")
        return response
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.get("/auth/google/callback")
async def google_callback(request: Request):
    """Handles Google OAuth callback, verifies identity, establishes session."""
    base_url = get_client_base_url(request)
    query = request.query_params
    def finish(destination):
        response = RedirectResponse(f"{base_url}/?{destination}")
        response.headers["Cache-Control"] = "no-store"
        response.delete_cookie(GOOGLE_STATE_COOKIE, path=GOOGLE_CALLBACK_PATH)
        return response

    state = query.get("state", "")
    expected = request.cookies.get(GOOGLE_STATE_COOKIE, "")
    if not expected or not secrets.compare_digest(expected.encode(), state.encode()):
        return finish("auth_error=Invalid+or+expired+Google+sign-in+state")
    if query.get("error"):
        return finish("auth_error=Google+sign-in+was+not+completed")

    code = query.get("code")
    if not code:
        return finish("auth_error=Missing+Google+authorization+code")

    try:
        redirect_uri = f"{base_url}/auth/google/callback"
        user = await handle_google_callback(code=code, redirect_uri=redirect_uri)
        resp = finish("login_success=true")
        await set_session_cookie(user, request, resp)
        return resp
    except Exception:
        return finish("auth_error=Google+sign-in+failed")

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
        resp = RedirectResponse(f"{base_url}/?login_success=true")
        await set_session_cookie(user, request, resp)
        return resp
    except Exception:
        return RedirectResponse(f"{base_url}/?auth_error=Steam+sign-in+failed")

# --- Game Library Endpoints (Phase 2) ---

class LibraryUpdateRequest(BaseModel):
    is_favourite: Optional[bool] = None
    favourite: Optional[bool] = None
    want_to_play: Optional[bool] = None
    already_played: Optional[bool] = None

@app.get("/api/library")
async def get_library(
    category: Optional[str] = Query(None),
    user=Depends(require_authenticated_user),
):
    try:
        games = await get_user_library(user, category=category)
        return {"success": True, "games": games}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/library/{appid}")
async def get_game_library_status(
    appid: int,
    user=Depends(require_authenticated_user),
):
    if get_game_by_appid(appid) is None:
        raise HTTPException(status_code=404, detail="Game not found in catalog")
    state = await get_library_state(user, appid)
    return {"success": True, "state": state}

@app.put("/api/library/{appid}", dependencies=[Depends(require_csrf)])
@app.patch("/api/library/{appid}", dependencies=[Depends(require_csrf)])
async def update_game_library_status(
    appid: int,
    body: LibraryUpdateRequest,
    user=Depends(require_authenticated_user),
):
    if get_game_by_appid(appid) is None:
        raise HTTPException(status_code=404, detail="Game not found in catalog")
    fav = body.is_favourite if body.is_favourite is not None else body.favourite
    updated = await update_library_state(
        user=user,
        appid=appid,
        is_favourite=fav,
        want_to_play=body.want_to_play,
        already_played=body.already_played,
    )
    return {"success": True, "state": serialize_activity(updated)}

@app.delete("/api/library/{appid}", dependencies=[Depends(require_csrf)])
async def remove_game_from_library(
    appid: int,
    category: Optional[str] = Query(None),
    user=Depends(require_authenticated_user),
):
    if get_game_by_appid(appid) is None:
        raise HTTPException(status_code=404, detail="Game not found in catalog")
    try:
        updated = await remove_library_state(user=user, appid=appid, category=category)
        return {"success": True, "state": serialize_activity(updated)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/library/{appid}/{category}", dependencies=[Depends(require_csrf)])
async def remove_game_category_from_library(
    appid: int,
    category: str,
    user=Depends(require_authenticated_user),
):
    if get_game_by_appid(appid) is None:
        raise HTTPException(status_code=404, detail="Game not found in catalog")
    try:
        updated = await remove_library_state(user=user, appid=appid, category=category)
        return {"success": True, "state": serialize_activity(updated)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Game Rating & Review Endpoints (Phase 2 Stage 2C) ---

class ReviewSubmissionRequest(BaseModel):
    rating: int = Field(..., ge=1, le=10, description="Rating from 1 to 10")
    comment: Optional[str] = Field(None, max_length=1000, description="Optional written review comment")

class ReviewReportRequest(BaseModel):
    target_user_id: str = Field(..., min_length=1, description="ID of review author to report")
    reason: Optional[str] = Field(None, max_length=200, description="Reason for report")

@app.get("/api/games/{appid}/reviews")
async def get_game_reviews_endpoint(
    appid: int,
    user=Depends(optional_session_user),
):
    if get_game_by_appid(appid) is None:
        raise HTTPException(status_code=404, detail="Game not found in catalog")
    current_uid = ObjectId(user["id"]) if (user and user.get("id")) else None
    data = await get_public_reviews(appid, current_user_id=current_uid)
    return {"success": True, **data}

@app.put("/api/games/{appid}/review", dependencies=[Depends(require_csrf)])
@app.post("/api/games/{appid}/review", dependencies=[Depends(require_csrf)])
async def submit_game_review_endpoint(
    appid: int,
    body: ReviewSubmissionRequest,
    user=Depends(require_authenticated_user),
):
    if get_game_by_appid(appid) is None:
        raise HTTPException(status_code=404, detail="Game not found in catalog")
    try:
        updated = await submit_review(
            user=user,
            appid=appid,
            rating=body.rating,
            review_text=body.comment,
        )
        return {"success": True, "state": serialize_activity(updated)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/games/{appid}/review", dependencies=[Depends(require_csrf)])
async def delete_game_review_endpoint(
    appid: int,
    user=Depends(require_authenticated_user),
):
    if get_game_by_appid(appid) is None:
        raise HTTPException(status_code=404, detail="Game not found in catalog")
    try:
        updated = await delete_user_review(user=user, appid=appid)
        return {"success": True, "state": serialize_activity(updated)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/games/{appid}/reviews/report", dependencies=[Depends(require_csrf)])
async def report_game_review_endpoint(
    appid: int,
    body: ReviewReportRequest,
    user=Depends(require_authenticated_user),
):
    if get_game_by_appid(appid) is None:
        raise HTTPException(status_code=404, detail="Game not found in catalog")
    try:
        res = await report_public_review(
            user=user,
            appid=appid,
            target_user_id=body.target_user_id,
            reason=body.reason,
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- User Preferences & AI History Endpoints (Phase 3) ---

class PreferencesUpdateRequest(BaseModel):
    preferred_genres: Optional[list[str]] = None
    interests: Optional[list[str]] = None
    onboarding_completed: Optional[bool] = None

class AIInteractionRequest(BaseModel):
    appid: int
    action: str
    query_id: Optional[str] = None

@app.get("/api/preferences")
async def get_preferences_endpoint(
    user=Depends(require_authenticated_user),
):
    try:
        prefs = await get_user_preferences(user)
        return {"success": True, "preferences": prefs}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.put("/api/preferences", dependencies=[Depends(require_csrf)])
async def update_preferences_endpoint(
    body: PreferencesUpdateRequest,
    user=Depends(require_authenticated_user),
):
    try:
        updated = await update_user_preferences(
            user=user,
            preferred_genres=body.preferred_genres,
            interests=body.interests,
            onboarding_completed=body.onboarding_completed,
        )
        return {"success": True, "preferences": updated}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/ai-history")
async def get_ai_history_endpoint(
    limit: int = Query(50, ge=1, le=100),
    user=Depends(require_authenticated_user),
):
    history = await get_user_ai_history(user, limit=limit)
    return {"success": True, "history": history}

@app.delete("/api/ai-history/{query_id}", dependencies=[Depends(require_csrf)])
async def delete_ai_history_item(
    query_id: str,
    user=Depends(require_authenticated_user),
):
    try:
        res = await delete_user_ai_history(user, query_id=query_id)
        if res.get("deleted_count", 0) == 0:
            raise HTTPException(status_code=404, detail="AI query record not found or not owned by user")
        return {"success": True, "message": "Query history item deleted"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/ai-history", dependencies=[Depends(require_csrf)])
async def clear_ai_history_endpoint(
    user=Depends(require_authenticated_user),
):
    res = await delete_user_ai_history(user)
    return {"success": True, "message": f"Cleared {res.get('deleted_count', 0)} history records"}

@app.post("/api/ai-history/interaction", dependencies=[Depends(require_csrf)])
async def log_ai_interaction_endpoint(
    body: AIInteractionRequest,
    user=Depends(require_authenticated_user),
):
    if get_game_by_appid(body.appid) is None:
        raise HTTPException(status_code=404, detail="Game not found in catalog")
    try:
        res = await record_ai_interaction(
            user=user,
            appid=body.appid,
            action=body.action,
            query_id=body.query_id,
        )
        return {"success": True, "interaction": res}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Personalized Recommendation Feed Endpoints (Phase 4) ---

@app.get("/api/recommendations/personalized")
async def get_personalized_recommendations_endpoint(
    limit: int = Query(20, ge=1, le=50),
    refresh: bool = Query(False),
    user=Depends(require_authenticated_user),
):
    try:
        feed = await generate_personalized_feed(user=user, limit=limit, refresh=refresh)
        return feed
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
