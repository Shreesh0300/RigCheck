import os
import re
import secrets
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple

import bcrypt
import httpx
from bson import ObjectId
from pydantic import BaseModel, EmailStr, Field
from dotenv import load_dotenv

from db import get_database

load_dotenv()

# OAuth / OpenID Environment Configurations
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").strip()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", f"{FRONTEND_URL}/auth/google/callback").strip()

STEAM_API_KEY = os.getenv("STEAM_API_KEY", "").strip()
STEAM_RETURN_URL = os.getenv("STEAM_RETURN_URL", f"{FRONTEND_URL}/auth/steam/callback").strip()
STEAM_REALM = os.getenv("STEAM_REALM", f"{FRONTEND_URL}/").strip()

SESSION_COOKIE_NAME = "rigcheck_session"
SESSION_DURATION_DAYS = 14

class UserAuthRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")

# --- Password Utilities ---

def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using bcrypt with a secure salt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

# --- Session Management ---

async def create_user_session(user_id: str) -> str:
    """Generates an opaque cryptographic session token and saves it in MongoDB."""
    token = secrets.token_urlsafe(36)
    db = get_database()
    sessions_col = db["sessions"]
    
    expires_at = (datetime.now(timezone.utc) + timedelta(days=SESSION_DURATION_DAYS)).isoformat()
    created_at = datetime.now(timezone.utc).isoformat()
    
    await sessions_col.insert_one({
        "token": token,
        "user_id": str(user_id),
        "created_at": created_at,
        "expires_at": expires_at,
    })
    return token

async def get_session_user(token: str) -> Optional[Dict[str, Any]]:
    """Retrieves the authenticated user for a valid session token."""
    if not token:
        return None
    db = get_database()
    sessions_col = db["sessions"]
    users_col = db["users"]

    session = await sessions_col.find_one({"token": token})
    if not session:
        return None

    # Check expiration
    expires_at = session.get("expires_at")
    if expires_at and datetime.fromisoformat(expires_at) < datetime.now(timezone.utc):
        await sessions_col.delete_one({"token": token})
        return None

    try:
        user_obj_id = ObjectId(session["user_id"])
    except Exception:
        return None

    user = await users_col.find_one({"_id": user_obj_id})
    if not user:
        return None

    return sanitize_user(user)

async def invalidate_session(token: str) -> bool:
    """Revokes a session token from MongoDB."""
    if not token:
        return False
    db = get_database()
    res = await db["sessions"].delete_one({"token": token})
    return res.deleted_count > 0

def sanitize_user(user_doc: Dict[str, Any]) -> Dict[str, Any]:
    """Prepares user dictionary for frontend transmission (strips sensitive fields)."""
    return {
        "id": str(user_doc["_id"]),
        "email": user_doc.get("email"),
        "display_name": user_doc.get("display_name") or (user_doc.get("email") or "Gamer").split("@")[0],
        "avatar": user_doc.get("avatar"),
        "avatar_url": user_doc.get("avatar"),
        "auth_provider": user_doc.get("auth_provider", "email"),
        "google_id": user_doc.get("google_id"),
        "steam_id": user_doc.get("steam_id"),
        "created_at": user_doc.get("created_at"),
        "last_login": user_doc.get("last_login"),
        "saved_rig": user_doc.get("saved_rig"),
    }

# --- Email / Password Authentication ---

async def register_user(email: str, password: str) -> Dict[str, Any]:
    """Registers a new email/password user in MongoDB."""
    normalized_email = email.strip().lower()
    db = get_database()
    users_col = db["users"]

    # Check if this email is already registered with email provider
    existing = await users_col.find_one({"email": normalized_email, "auth_provider": "email"})
    if existing:
        raise ValueError("An account with this email already exists.")

    password_hash = hash_password(password)
    now = datetime.now(timezone.utc).isoformat()

    user_doc = {
        "email": normalized_email,
        "display_name": normalized_email.split("@")[0],
        "avatar": None,
        "auth_provider": "email",
        "password_hash": password_hash,
        "google_id": None,
        "steam_id": None,
        "created_at": now,
        "last_login": now,
        "saved_rig": None,
    }

    result = await users_col.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id
    return sanitize_user(user_doc)

async def authenticate_user(email: str, password: str) -> Dict[str, Any]:
    """Authenticates an email/password user."""
    normalized_email = email.strip().lower()
    db = get_database()
    users_col = db["users"]

    user = await users_col.find_one({"email": normalized_email, "auth_provider": "email"})
    if not user:
        raise ValueError("Invalid email or password.")

    stored_hash = user.get("password_hash", "")
    if not verify_password(password, stored_hash):
        raise ValueError("Invalid email or password.")

    # Update last login timestamp
    now = datetime.now(timezone.utc).isoformat()
    await users_col.update_one({"_id": user["_id"]}, {"$set": {"last_login": now}})
    user["last_login"] = now

    return sanitize_user(user)

# --- Google OAuth 2.0 / OpenID Connect ---

def is_google_configured() -> bool:
    """Returns True if Google Client ID and Secret are configured in environment."""
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and GOOGLE_CLIENT_ID != "your_google_client_id_here")

def generate_google_auth_url(redirect_uri: str = None) -> Tuple[str, str]:
    """Generates the Google OAuth authorization URL along with a secure CSRF state token."""
    if not is_google_configured():
        raise ValueError("Google OAuth credentials are not configured in .env.")
    
    state = secrets.token_urlsafe(24)
    r_uri = redirect_uri or GOOGLE_REDIRECT_URI
    
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": r_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account"
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return url, state

async def handle_google_callback(code: str, redirect_uri: str = None) -> Dict[str, Any]:
    """
    Exchanges authorization code for Google user profile,
    finds or creates the user in MongoDB, and updates login timestamp.
    """
    if not is_google_configured():
        raise ValueError("Google OAuth credentials are not configured in .env.")

    r_uri = redirect_uri or GOOGLE_REDIRECT_URI

    # Exchange code for access token
    async with httpx.AsyncClient(timeout=10.0) as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": r_uri,
            },
        )
        if token_res.status_code != 200:
            raise ValueError(f"Failed to obtain Google access token: {token_res.text}")

        token_data = token_res.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise ValueError("No access token returned from Google.")

        # Fetch user info
        userinfo_res = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if userinfo_res.status_code != 200:
            raise ValueError("Failed to fetch Google user profile.")

        profile = userinfo_res.json()

    google_id = profile.get("sub")
    email = profile.get("email")
    display_name = profile.get("name") or (email.split("@")[0] if email else "Google User")
    avatar = profile.get("picture")

    if not google_id:
        raise ValueError("Google profile missing account ID (sub).")

    db = get_database()
    users_col = db["users"]
    now = datetime.now(timezone.utc).isoformat()

    # Find existing Google user by google_id (prevents duplicate accounts)
    user = await users_col.find_one({"google_id": google_id})
    if user:
        # Update last login & profile info
        await users_col.update_one(
            {"_id": user["_id"]},
            {"$set": {"last_login": now, "display_name": display_name, "avatar": avatar, "email": email}}
        )
        user["last_login"] = now
        user["display_name"] = display_name
        user["avatar"] = avatar
        user["email"] = email
    else:
        # Create new Google user
        new_doc = {
            "google_id": google_id,
            "email": email,
            "display_name": display_name,
            "avatar": avatar,
            "auth_provider": "google",
            "password_hash": None,
            "steam_id": None,
            "created_at": now,
            "last_login": now,
            "saved_rig": None,
        }
        res = await users_col.insert_one(new_doc)
        new_doc["_id"] = res.inserted_id
        user = new_doc

    return sanitize_user(user)

# --- Steam OpenID 2.0 ---

def generate_steam_login_url(return_url: str = None, realm: str = None) -> str:
    """Builds the official Steam OpenID 2.0 authentication URL."""
    r_url = return_url or STEAM_RETURN_URL
    if realm:
        r_realm = realm
    else:
        parsed = urllib.parse.urlparse(r_url)
        r_realm = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else STEAM_REALM

    params = {
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.mode": "checkid_setup",
        "openid.return_to": r_url,
        "openid.realm": r_realm,
        "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
    }
    return "https://steamcommunity.com/openid/login?" + urllib.parse.urlencode(params)

async def verify_steam_assertion(query_params: Dict[str, str]) -> str:
    """
    Validates the OpenID response directly with Steam servers.
    Returns the verified 64-bit Steam ID upon success, or raises ValueError.
    """
    # Check if user cancelled
    if query_params.get("openid.mode") == "cancel":
        raise ValueError("Steam authentication was cancelled.")

    # Prepare validation request to Steam
    check_params = dict(query_params)
    check_params["openid.mode"] = "check_authentication"

    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.post(
            "https://steamcommunity.com/openid/login",
            data=check_params,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

    # Steam responds with plaintext e.g. "is_valid:true\n"
    response_text = res.text
    if "is_valid:true" not in response_text:
        raise ValueError("Invalid OpenID assertion from Steam.")

    # Extract 64-bit Steam ID from openid.claimed_id
    claimed_id = query_params.get("openid.claimed_id", "")
    match = re.search(r"openid/id/(\d+)", claimed_id)
    if not match:
        raise ValueError("Could not extract Steam ID from claimed identifier.")

    steam_id = match.group(1)
    return steam_id

async def fetch_steam_player_summary(steam_id: str) -> Tuple[str, Optional[str]]:
    """Fetches public player summary (display name and avatar) if STEAM_API_KEY is configured."""
    display_name = f"Steam Gamer ({steam_id[-4:]})"
    avatar = None

    if STEAM_API_KEY and STEAM_API_KEY != "your_steam_api_key_here":
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.get(
                    f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={STEAM_API_KEY}&steamids={steam_id}"
                )
                if res.status_code == 200:
                    data = res.json()
                    players = data.get("response", {}).get("players", [])
                    if players:
                        display_name = players[0].get("personaname", display_name)
                        avatar = players[0].get("avatarfull") or players[0].get("avatar")
        except Exception as e:
            print(f"[Steam API] Warning: Failed to fetch player summary: {e}")

    return display_name, avatar

async def handle_steam_callback(query_params: Dict[str, str]) -> Dict[str, Any]:
    """
    Verifies Steam OpenID response, retrieves or creates the Steam user in MongoDB,
    and updates login timestamp.
    """
    steam_id = await verify_steam_assertion(query_params)
    display_name, avatar = await fetch_steam_player_summary(steam_id)

    db = get_database()
    users_col = db["users"]
    now = datetime.now(timezone.utc).isoformat()

    # Find existing Steam user by steam_id (prevents duplicate accounts)
    user = await users_col.find_one({"steam_id": steam_id})
    if user:
        update_fields = {"last_login": now}
        if display_name and not user.get("display_name"):
            update_fields["display_name"] = display_name
        if avatar and not user.get("avatar"):
            update_fields["avatar"] = avatar

        await users_col.update_one({"_id": user["_id"]}, {"$set": update_fields})
        user.update(update_fields)
    else:
        # Create new Steam user (email is null since Steam does not supply emails)
        new_doc = {
            "steam_id": steam_id,
            "email": None,
            "display_name": display_name,
            "avatar": avatar,
            "auth_provider": "steam",
            "password_hash": None,
            "google_id": None,
            "created_at": now,
            "last_login": now,
            "saved_rig": None,
        }
        res = await users_col.insert_one(new_doc)
        new_doc["_id"] = res.inserted_id
        user = new_doc

    return sanitize_user(user)
