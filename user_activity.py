"""Private user/game relationships. Call with a principal from require_authenticated_user.

One document per (ObjectId user_id, integer appid), with BSON UTC created_at and
updated_at. Future library flags, rating, review and their change times belong
on this relationship. Only an effective change should advance updated_at.

Account-level preferences, genres/interests and a feed revision belong to the
owner. AI query occurrences and attributed interactions can reference that
owner and these same App IDs independently of the library relationship.
"""
from datetime import datetime, timezone
import re
from typing import Optional, Any

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from auth import AuthenticatedUser
from db import get_database, get_activity_collection, get_ai_history_collection
from model.steam_database import get_game_by_appid


def _activity_key(user: AuthenticatedUser, appid: int) -> dict:
    if not isinstance(user, AuthenticatedUser) or not isinstance(user.id, ObjectId):
        raise TypeError("Expected a session-authenticated user")
    if get_game_by_appid(appid) is None:
        raise ValueError("Expected a catalog Steam App ID")
    return {"user_id": user.id, "appid": appid}


async def get_activity(user: AuthenticatedUser, appid: int):
    key = _activity_key(user, appid)
    collection = await get_activity_collection()
    return await collection.find_one(key)


async def ensure_activity(user: AuthenticatedUser, appid: int):
    """Create the relationship once. A retry leaves both timestamps intact."""
    key = _activity_key(user, appid)
    collection = await get_activity_collection()
    now = datetime.now(timezone.utc)
    try:
        return await collection.find_one_and_update(
            key, {"$setOnInsert": {"created_at": now, "updated_at": now}},
            upsert=True, return_document=ReturnDocument.AFTER,
        )
    except DuplicateKeyError:
        # A concurrent first insert may have won the unique-key race.
        existing = await collection.find_one(key)
        if existing is None:
            raise
        return existing


def serialize_activity(doc: Optional[dict]) -> dict:
    if not doc:
        return {
            "appid": 0,
            "is_favourite": False,
            "want_to_play": False,
            "already_played": False,
            "rating": None,
            "review": None,
            "created_at": None,
            "updated_at": None,
        }
    created_at = doc.get("created_at")
    updated_at = doc.get("updated_at")
    return {
        "appid": doc.get("appid"),
        "is_favourite": bool(doc.get("is_favourite", False)),
        "want_to_play": bool(doc.get("want_to_play", False)),
        "already_played": bool(doc.get("already_played", False)),
        "rating": doc.get("rating"),
        "review": doc.get("review") or doc.get("review_text"),
        "created_at": created_at.isoformat() if isinstance(created_at, datetime) else created_at,
        "updated_at": updated_at.isoformat() if isinstance(updated_at, datetime) else updated_at,
    }


async def get_library_state(user: AuthenticatedUser, appid: int) -> dict:
    """Retrieve the library state for a specific user and game."""
    doc = await get_activity(user, appid)
    if doc is None:
        return {
            "appid": appid,
            "is_favourite": False,
            "want_to_play": False,
            "already_played": False,
            "rating": None,
            "review": None,
            "created_at": None,
            "updated_at": None,
        }
    serialized = serialize_activity(doc)
    serialized["appid"] = appid
    return serialized


async def get_user_library(user: AuthenticatedUser, category: Optional[str] = None) -> list[dict]:
    """Retrieve all library items belonging to the user, optionally filtered by category."""
    if not isinstance(user, AuthenticatedUser) or not isinstance(user.id, ObjectId):
        raise TypeError("Expected a session-authenticated user")
    collection = await get_activity_collection()
    query: dict[str, Any] = {"user_id": user.id}

    if category:
        cat = category.strip().lower()
        if cat in ("favourite", "is_favourite"):
            query["is_favourite"] = True
        elif cat in ("want_to_play", "wanttoplay"):
            query["want_to_play"] = True
        elif cat in ("already_played", "alreadyplayed", "played"):
            query["already_played"] = True
        else:
            raise ValueError(f"Unknown library category: {category}")
    else:
        query["$or"] = [
            {"is_favourite": True},
            {"want_to_play": True},
            {"already_played": True},
        ]

    cursor = collection.find(query).sort("updated_at", -1)
    raw_docs = await cursor.to_list(length=1000)

    results = []
    for doc in raw_docs:
        serialized = serialize_activity(doc)
        game_meta = get_game_by_appid(doc["appid"])
        if game_meta:
            serialized["title"] = game_meta.get("name")
            serialized["name"] = game_meta.get("name")
            serialized["header_image"] = game_meta.get("header_image")
            serialized["image"] = game_meta.get("header_image")
            serialized["genres"] = game_meta.get("genres", [])
            serialized["price"] = game_meta.get("price_overview", {})
            serialized["is_free"] = game_meta.get("is_free", False)
            serialized["release_date"] = game_meta.get("release_date")
            serialized["short_description"] = game_meta.get("short_description")
        results.append(serialized)
    return results


async def update_library_state(
    user: AuthenticatedUser,
    appid: int,
    is_favourite: Optional[bool] = None,
    want_to_play: Optional[bool] = None,
    already_played: Optional[bool] = None,
) -> dict:
    """Atomically updates library state flags for a user and game.
    Preserves existing activity records, ratings, and reviews.
    Advances updated_at only when an effective change occurs.
    """
    key = _activity_key(user, appid)
    collection = await get_activity_collection()

    doc = await collection.find_one(key)
    now = datetime.now(timezone.utc)

    if doc is None:
        fav = bool(is_favourite) if is_favourite is not None else False
        wtp = bool(want_to_play) if want_to_play is not None else False
        ply = bool(already_played) if already_played is not None else False
        insert_doc = {
            "user_id": user.id,
            "appid": appid,
            "created_at": now,
            "updated_at": now,
            "is_favourite": fav,
            "want_to_play": wtp,
            "already_played": ply,
        }
        try:
            return await collection.find_one_and_update(
                key,
                {"$setOnInsert": insert_doc},
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError:
            doc = await collection.find_one(key)

    updates = {}
    if is_favourite is not None:
        val = bool(is_favourite)
        if doc.get("is_favourite") != val:
            updates["is_favourite"] = val

    if want_to_play is not None:
        val = bool(want_to_play)
        if doc.get("want_to_play") != val:
            updates["want_to_play"] = val

    if already_played is not None:
        val = bool(already_played)
        if doc.get("already_played") != val:
            updates["already_played"] = val

    if not updates:
        # Only an effective change should advance updated_at
        return doc

    updates["updated_at"] = now
    result = await collection.find_one_and_update(
        key,
        {"$set": updates},
        return_document=ReturnDocument.AFTER,
    )
    try:
        await get_database()["users"].update_one({"_id": user.id}, {"$inc": {"feed_revision": 1}})
    except Exception:
        pass
    return result


async def remove_library_state(
    user: AuthenticatedUser,
    appid: int,
    category: Optional[str] = None,
) -> dict:
    """Removes a specific library state category or resets all categories."""
    _activity_key(user, appid)
    if category is None or category in ("all", "library"):
        return await update_library_state(
            user, appid, is_favourite=False, want_to_play=False, already_played=False
        )
    cat = category.strip().lower()
    if cat in ("favourite", "is_favourite"):
        return await update_library_state(user, appid, is_favourite=False)
    elif cat in ("want_to_play", "wanttoplay"):
        return await update_library_state(user, appid, want_to_play=False)
    elif cat in ("already_played", "alreadyplayed", "played"):
        return await update_library_state(user, appid, already_played=False)
    else:
        raise ValueError(f"Unknown library category: {category}")


def sanitize_review_text(text: Optional[str]) -> Optional[str]:
    """Sanitizes review text by stripping HTML tags and limiting length."""
    if not text:
        return None
    cleaned = re.sub(r"<[^>]*>", "", str(text)).strip()
    if not cleaned:
        return None
    if len(cleaned) > 1000:
        cleaned = cleaned[:1000].strip()
    return cleaned


async def submit_review(
    user: AuthenticatedUser,
    appid: int,
    rating: int,
    review_text: Optional[str] = None,
) -> dict:
    """Submits or updates a 1-10 rating and optional review comment for a game.
    Enforces only one active review per user per game.
    Marks the game as already_played without altering recommendation scores.
    """
    key = _activity_key(user, appid)
    if not isinstance(rating, int) or rating < 1 or rating > 10:
        raise ValueError("Rating must be an integer between 1 and 10")

    sanitized_text = sanitize_review_text(review_text)
    collection = await get_activity_collection()
    now = datetime.now(timezone.utc)

    doc = await collection.find_one(key)
    if doc is None:
        insert_doc = {
            "user_id": user.id,
            "appid": appid,
            "created_at": now,
            "updated_at": now,
            "is_favourite": False,
            "want_to_play": False,
            "already_played": True,
            "rating": rating,
            "review_text": sanitized_text,
            "review_created_at": now,
            "review_updated_at": now,
            "reported": False,
            "report_count": 0,
            "is_hidden": False,
        }
        try:
            return await collection.find_one_and_update(
                key,
                {"$setOnInsert": insert_doc},
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError:
            doc = await collection.find_one(key)

    review_created_at = doc.get("review_created_at") or now
    updates = {
        "rating": rating,
        "review_text": sanitized_text,
        "review_created_at": review_created_at,
        "review_updated_at": now,
        "already_played": True,
        "updated_at": now,
    }
    result = await collection.find_one_and_update(
        key,
        {"$set": updates},
        return_document=ReturnDocument.AFTER,
    )
    try:
        await get_database()["users"].update_one({"_id": user.id}, {"$inc": {"feed_revision": 1}})
    except Exception:
        pass
    return result


async def delete_user_review(user: AuthenticatedUser, appid: int) -> dict:
    """Deletes a user's review and rating, preserving the underlying activity record."""
    key = _activity_key(user, appid)
    collection = await get_activity_collection()
    doc = await collection.find_one(key)
    if doc is None:
        raise ValueError("No record found to delete review")

    now = datetime.now(timezone.utc)
    updated = await collection.find_one_and_update(
        key,
        {
            "$set": {
                "rating": None,
                "review_text": None,
                "review_updated_at": now,
                "updated_at": now,
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    try:
        await get_database()["users"].update_one({"_id": user.id}, {"$inc": {"feed_revision": 1}})
    except Exception:
        pass
    return updated


async def get_public_reviews(appid: int, current_user_id: Optional[ObjectId] = None) -> dict:
    """Retrieves public reviews and average rating for a game."""
    if get_game_by_appid(appid) is None:
        raise ValueError("Game not found in catalog")

    collection = await get_activity_collection()
    query = {
        "appid": appid,
        "rating": {"$ne": None},
        "is_hidden": {"$ne": True},
    }
    cursor = collection.find(query).sort("review_updated_at", -1)
    review_docs = await cursor.to_list(length=500)

    total_ratings = len(review_docs)
    total_reviews = sum(1 for d in review_docs if d.get("review_text"))
    average_rating = (
        round(sum(d["rating"] for d in review_docs) / total_ratings, 1)
        if total_ratings > 0
        else None
    )

    # Batch fetch author profiles
    user_ids = [d["user_id"] for d in review_docs if isinstance(d.get("user_id"), ObjectId)]
    users_map = {}
    if user_ids:
        db = get_database()
        user_cursor = db["users"].find({"_id": {"$in": user_ids}})
        users_list = await user_cursor.to_list(length=len(user_ids))
        for u in users_list:
            users_map[u["_id"]] = {
                "display_name": u.get("display_name") or (u.get("email") or "Gamer").split("@")[0],
                "avatar": u.get("avatar") or u.get("avatar_url"),
            }

    serialized_reviews = []
    for d in review_docs:
        uid = d.get("user_id")
        user_info = users_map.get(uid, {"display_name": "Gamer", "avatar": None})
        r_created = d.get("review_created_at") or d.get("created_at")
        r_updated = d.get("review_updated_at") or d.get("updated_at")
        serialized_reviews.append({
            "id": str(d.get("_id", "")),
            "user_id": str(uid),
            "user_display_name": user_info["display_name"],
            "user_avatar": user_info["avatar"],
            "rating": d.get("rating"),
            "comment": d.get("review_text"),
            "created_at": r_created.isoformat() if isinstance(r_created, datetime) else str(r_created),
            "updated_at": r_updated.isoformat() if isinstance(r_updated, datetime) else str(r_updated),
            "is_owner": bool(current_user_id and uid == current_user_id),
            "report_count": d.get("report_count", 0),
        })

    return {
        "appid": appid,
        "average_rating": average_rating,
        "total_ratings": total_ratings,
        "total_reviews": total_reviews,
        "reviews": serialized_reviews,
    }


async def report_public_review(
    user: AuthenticatedUser,
    appid: int,
    target_user_id: str,
    reason: Optional[str] = None,
) -> dict:
    """Reports a public review. Automatically hides it if report threshold >= 3 is reached."""
    _activity_key(user, appid)
    if not ObjectId.is_valid(target_user_id):
        raise ValueError("Invalid target user ID")

    target_uid = ObjectId(target_user_id)
    if user.id == target_uid:
        raise ValueError("Cannot report your own review")

    collection = await get_activity_collection()
    key = {"user_id": target_uid, "appid": appid}

    target_doc = await collection.find_one(key)
    if target_doc is None or target_doc.get("rating") is None:
        raise ValueError("Target review not found")

    new_count = target_doc.get("report_count", 0) + 1
    is_hidden = new_count >= 3

    updated = await collection.find_one_and_update(
        key,
        {
            "$inc": {"report_count": 1},
            "$set": {
                "reported": True,
                "is_hidden": is_hidden,
            },
        },
        return_document=ReturnDocument.AFTER,
    )

    return {
        "success": True,
        "reported": True,
        "is_hidden": is_hidden,
        "report_count": updated.get("report_count", new_count),
    }


# --- User Preferences (Phase 3) ---

def sanitize_preference_tags(tags: Optional[list[str]], max_count: int = 20) -> list[str]:
    """Sanitizes preference genre or interest tags: strips HTML, whitespace, limits lengths and count."""
    if not tags or not isinstance(tags, (list, tuple)):
        return []
    cleaned: list[str] = []
    seen = set()
    for item in tags:
        if not isinstance(item, str):
            continue
        tag = re.sub(r"<[^>]*>", "", item).strip()
        if not tag:
            continue
        if len(tag) > 50:
            tag = tag[:50].strip()
        lower_tag = tag.lower()
        if lower_tag not in seen:
            seen.add(lower_tag)
            cleaned.append(tag)
        if len(cleaned) >= max_count:
            break
    return cleaned


async def get_user_preferences(user: AuthenticatedUser) -> dict:
    """Retrieves stored genre and interest preferences for the authenticated user."""
    if not isinstance(user, AuthenticatedUser) or not isinstance(user.id, ObjectId):
        raise TypeError("Expected a session-authenticated user")
    db = get_database()
    user_doc = await db["users"].find_one({"_id": user.id})
    if not user_doc:
        raise ValueError("User not found")
    return {
        "preferred_genres": user_doc.get("preferred_genres", []),
        "interests": user_doc.get("interests", []),
        "onboarding_completed": bool(user_doc.get("onboarding_completed", False)),
        "feed_revision": int(user_doc.get("feed_revision", 1)),
    }


async def update_user_preferences(
    user: AuthenticatedUser,
    preferred_genres: Optional[list[str]] = None,
    interests: Optional[list[str]] = None,
    onboarding_completed: Optional[bool] = None,
) -> dict:
    """Updates user genre and interest preferences, bumping feed_revision for personalized recommendations."""
    if not isinstance(user, AuthenticatedUser) or not isinstance(user.id, ObjectId):
        raise TypeError("Expected a session-authenticated user")
    db = get_database()
    users_col = db["users"]

    updates: dict[str, Any] = {
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    if preferred_genres is not None:
        updates["preferred_genres"] = sanitize_preference_tags(preferred_genres)
    if interests is not None:
        updates["interests"] = sanitize_preference_tags(interests)
    if onboarding_completed is not None:
        updates["onboarding_completed"] = bool(onboarding_completed)

    updated_doc = await users_col.find_one_and_update(
        {"_id": user.id},
        {"$set": updates, "$inc": {"feed_revision": 1}},
        return_document=ReturnDocument.AFTER,
    )
    if not updated_doc:
        raise ValueError("User not found")

    return {
        "preferred_genres": updated_doc.get("preferred_genres", []),
        "interests": updated_doc.get("interests", []),
        "onboarding_completed": bool(updated_doc.get("onboarding_completed", False)),
        "feed_revision": int(updated_doc.get("feed_revision", 1)),
    }


# --- AI History & Interaction Tracking (Phase 3) ---

ALLOWED_AI_ACTIONS = frozenset({"click", "view", "favourite", "want_to_play", "already_played", "rating"})


async def record_ai_query(
    user: AuthenticatedUser,
    query: str,
    recommended_appid: Optional[int],
    alternative_appids: Optional[list[int]] = None,
    budget: Optional[int] = None,
    gpu_name: Optional[str] = None,
    ram: Optional[int] = None,
    cpu_name: Optional[str] = None,
    storage_gb: Optional[float] = None,
) -> dict:
    """Persists an Ask RigCheck AI query and its recommendations for an authenticated user."""
    if not isinstance(user, AuthenticatedUser) or not isinstance(user.id, ObjectId):
        raise TypeError("Expected a session-authenticated user")

    cleaned_query = (query or "").strip()
    if not cleaned_query:
        raise ValueError("AI query string cannot be empty")
    if len(cleaned_query) > 500:
        cleaned_query = cleaned_query[:500].strip()

    valid_rec_appid = None
    if recommended_appid is not None:
        if get_game_by_appid(recommended_appid) is not None:
            valid_rec_appid = int(recommended_appid)

    valid_alts = []
    if alternative_appids:
        for aid in alternative_appids:
            if isinstance(aid, int) and get_game_by_appid(aid) is not None:
                if aid not in valid_alts and aid != valid_rec_appid:
                    valid_alts.append(aid)

    now = datetime.now(timezone.utc)
    doc = {
        "user_id": user.id,
        "query": cleaned_query,
        "recommended_appid": valid_rec_appid,
        "alternative_appids": valid_alts,
        "budget": int(budget) if budget is not None and budget >= 0 else None,
        "gpu_name": str(gpu_name).strip()[:100] if gpu_name else None,
        "ram": int(ram) if ram is not None and ram >= 0 else None,
        "cpu_name": str(cpu_name).strip()[:100] if cpu_name else None,
        "storage_gb": float(storage_gb) if storage_gb is not None and storage_gb >= 0 else None,
        "timestamp": now,
        "interactions": [],
    }

    collection = await get_ai_history_collection()
    insert_res = await collection.insert_one(doc)
    doc["_id"] = insert_res.inserted_id

    try:
        await get_database()["users"].update_one({"_id": user.id}, {"$inc": {"feed_revision": 1}})
    except Exception:
        pass

    return {
        "id": str(doc["_id"]),
        "query": doc["query"],
        "recommended_appid": doc["recommended_appid"],
        "alternative_appids": doc["alternative_appids"],
        "budget": doc["budget"],
        "gpu_name": doc["gpu_name"],
        "ram": doc["ram"],
        "timestamp": now.isoformat(),
        "interactions": [],
    }


async def get_user_ai_history(user: AuthenticatedUser, limit: int = 50) -> list[dict]:
    """Retrieves AI search history for the authenticated user, hydrated with game titles & images."""
    if not isinstance(user, AuthenticatedUser) or not isinstance(user.id, ObjectId):
        raise TypeError("Expected a session-authenticated user")

    bounded_limit = max(1, min(100, int(limit)))
    collection = await get_ai_history_collection()
    cursor = collection.find({"user_id": user.id}).sort("timestamp", -1).limit(bounded_limit)
    docs = await cursor.to_list(length=bounded_limit)

    results = []
    for doc in docs:
        rec_appid = doc.get("recommended_appid")
        rec_meta = get_game_by_appid(rec_appid) if rec_appid else None

        alt_list = []
        for aid in doc.get("alternative_appids", []):
            am = get_game_by_appid(aid)
            if am:
                alt_list.append({
                    "appid": aid,
                    "title": am.get("name"),
                    "header_image": am.get("header_image"),
                })

        ts = doc.get("timestamp")
        serialized_interactions = []
        for act in doc.get("interactions", []):
            act_ts = act.get("timestamp")
            serialized_interactions.append({
                "appid": act.get("appid"),
                "action": act.get("action"),
                "timestamp": act_ts.isoformat() if isinstance(act_ts, datetime) else act_ts,
            })

        results.append({
            "id": str(doc["_id"]),
            "query": doc.get("query"),
            "recommended_game": {
                "appid": rec_appid,
                "title": rec_meta.get("name") if rec_meta else None,
                "header_image": rec_meta.get("header_image") if rec_meta else None,
            } if rec_appid else None,
            "alternative_games": alt_list,
            "budget": doc.get("budget"),
            "gpu_name": doc.get("gpu_name"),
            "ram": doc.get("ram"),
            "cpu_name": doc.get("cpu_name"),
            "storage_gb": doc.get("storage_gb"),
            "timestamp": ts.isoformat() if isinstance(ts, datetime) else ts,
            "interactions": serialized_interactions,
        })
    return results


async def delete_user_ai_history(user: AuthenticatedUser, query_id: Optional[str] = None) -> dict:
    """Deletes one specific query or all AI search history records belonging to the authenticated user."""
    if not isinstance(user, AuthenticatedUser) or not isinstance(user.id, ObjectId):
        raise TypeError("Expected a session-authenticated user")

    collection = await get_ai_history_collection()
    if query_id:
        if not ObjectId.is_valid(query_id):
            raise ValueError("Invalid query ID format")
        res = await collection.delete_one({"_id": ObjectId(query_id), "user_id": user.id})
        return {"deleted_count": res.deleted_count}
    else:
        res = await collection.delete_many({"user_id": user.id})
        return {"deleted_count": res.deleted_count}


async def record_ai_interaction(
    user: AuthenticatedUser,
    appid: int,
    action: str,
    query_id: Optional[str] = None,
) -> dict:
    """Tracks a user interaction (click, favourite, want_to_play, already_played, rating) with an AI recommendation.
    Deduplicates repeated interactions to avoid clutter and preserve unique signals.
    """
    if not isinstance(user, AuthenticatedUser) or not isinstance(user.id, ObjectId):
        raise TypeError("Expected a session-authenticated user")

    if get_game_by_appid(appid) is None:
        raise ValueError("Invalid Steam App ID")

    act = (action or "").strip().lower()
    if act not in ALLOWED_AI_ACTIONS:
        raise ValueError(f"Invalid interaction action: {action}. Allowed: {sorted(ALLOWED_AI_ACTIONS)}")

    collection = await get_ai_history_collection()
    now = datetime.now(timezone.utc)

    filter_query: dict[str, Any] = {"user_id": user.id}
    if query_id:
        if not ObjectId.is_valid(query_id):
            raise ValueError("Invalid query ID format")
        filter_query["_id"] = ObjectId(query_id)
        target_doc = await collection.find_one(filter_query)
        if not target_doc:
            raise ValueError("Target AI history query not found or not owned by user")
    else:
        # Find the most recent AI query that contained this appid
        target_doc = await collection.find_one(
            {"user_id": user.id, "$or": [{"recommended_appid": appid}, {"alternative_appids": appid}]},
            sort=[("timestamp", -1)],
        )
        if not target_doc:
            # Fallback to the latest query by user overall
            target_doc = await collection.find_one({"user_id": user.id}, sort=[("timestamp", -1)])

    if not target_doc:
        return {"success": True, "attached_to_query": None, "action": act, "appid": appid, "deduplicated": False}

    doc_id = target_doc["_id"]

    # Deduplication check
    has_existing = any(
        it.get("appid") == appid and it.get("action") == act
        for it in target_doc.get("interactions", [])
    )

    if has_existing:
        await collection.update_one(
            {"_id": doc_id, "user_id": user.id, "interactions": {"$elemMatch": {"appid": appid, "action": act}}},
            {"$set": {"interactions.$.timestamp": now}},
        )
        return {
            "success": True,
            "query_id": str(doc_id),
            "action": act,
            "appid": appid,
            "deduplicated": True,
        }
    else:
        await collection.update_one(
            {"_id": doc_id, "user_id": user.id},
            {"$push": {"interactions": {"appid": appid, "action": act, "timestamp": now}}},
        )
        try:
            await get_database()["users"].update_one({"_id": user.id}, {"$inc": {"feed_revision": 1}})
        except Exception:
            pass
        return {
            "success": True,
            "query_id": str(doc_id),
            "action": act,
            "appid": appid,
            "deduplicated": False,
        }
