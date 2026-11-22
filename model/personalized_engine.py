"""Personalized Recommendation Engine for RigCheck (Phase 4).

Ranks games according to user preferences, favourites, want-to-play, ratings,
play history, and Ask RigCheck AI search/interaction history.

Key Requirements:
1. Excludes Already Played games from main recommendations and returns them in a separate section.
2. Positive ratings (7-10) boost relevant genres/concepts; negative ratings (1-4) penalize them.
3. Favourites and Want to Play provide strong positive interest signals.
4. Preferred genres and interests provide direct personalization signals.
5. Previous Ask RigCheck AI queries and interactions contribute to interest profile.
6. Diverse recommendations without excessive repetition.
7. Meaningful explanations ("Because you favourited...", "Because you enjoyed...", etc.).
8. Sensible discovery recommendations for new users with little or no history.
9. Fast and efficient computation over catalog Steam App IDs.
"""
from collections import Counter
import random
from typing import Any, Optional

from bson import ObjectId

from auth import AuthenticatedUser
from db import get_activity_collection
from model.concept_engine import extract_game_concepts, extract_query_concepts
from model.steam_database import get_all_games, get_game_by_appid
from user_activity import get_user_preferences, get_user_ai_history


def extract_game_concepts_from_meta(game: dict[str, Any]) -> list[str]:
    """Helper to adapt catalog game metadata into concept extractor format."""
    genres_list = game.get("genres", [])
    genres_str = ", ".join(genres_list) if isinstance(genres_list, list) else str(genres_list or "")

    cats = game.get("categories", [])
    cat_items = []
    if isinstance(cats, list):
        for c in cats:
            if isinstance(c, dict):
                cat_items.append(c.get("description", ""))
            elif isinstance(c, str):
                cat_items.append(c)
    cats_str = ", ".join(cat_items)

    row = {
        "Genres": genres_str,
        "Categories": cats_str,
        "Title": game.get("name", ""),
        "Description": game.get("short_description", ""),
        "Tags": "",
    }
    return extract_game_concepts(row)


def _compute_popularity_prior(game: dict[str, Any]) -> float:
    """Computes a baseline quality prior between 0.0 and 2.0 based on recommendations and metacritic."""
    prior = 0.0
    recs = game.get("recommendations", 0)
    if isinstance(recs, (int, float)) and recs > 0:
        # 1,000 recs -> ~0.4, 50,000 recs -> ~1.0, 200,000 recs -> ~1.4
        import math
        prior += min(1.3, math.log10(max(10, recs)) / 4.0)

    metacritic = game.get("metacritic")
    if isinstance(metacritic, (int, float)) and metacritic > 0:
        prior += min(0.7, (metacritic - 60) / 40.0) if metacritic > 60 else 0.0

    return prior


async def generate_personalized_feed(
    user: AuthenticatedUser,
    limit: int = 20,
    refresh: bool = False,
) -> dict[str, Any]:
    """Generates personalized game recommendations for an authenticated user.
    Returns both the main recommendation feed (excluding already played games)
    and a separate section for already played games.
    """
    if not isinstance(user, AuthenticatedUser) or not isinstance(user.id, ObjectId):
        raise TypeError("Expected an AuthenticatedUser instance")

    # 1. Fetch user preferences
    prefs = await get_user_preferences(user)
    pref_genres = [g.strip().lower() for g in prefs.get("preferred_genres", []) if g]
    pref_interests = [i.strip().lower() for i in prefs.get("interests", []) if i]
    feed_revision = prefs.get("feed_revision", 1)

    # 2. Fetch user library activity
    activity_col = await get_activity_collection()
    cursor = activity_col.find({"user_id": user.id})
    activities = await cursor.to_list(length=1000)

    # 3. Fetch user AI history
    ai_history = await get_user_ai_history(user, limit=25)

    # Build user interest profile
    positive_genres: Counter[str] = Counter()
    negative_genres: Counter[str] = Counter()

    positive_concepts: Counter[str] = Counter()
    negative_concepts: Counter[str] = Counter()

    favourited_appids: set[int] = set()
    want_to_play_appids: set[int] = set()
    already_played_appids: set[int] = set()

    favourited_games: list[dict[str, Any]] = []
    played_games_records: list[dict[str, Any]] = []
    high_rated_games: list[tuple[int, dict[str, Any]]] = []

    # Process activities
    for act in activities:
        appid = act.get("appid")
        if not isinstance(appid, int):
            continue
        game = get_game_by_appid(appid)
        if not game:
            continue

        g_genres = [g.lower() for g in game.get("genres", [])]
        g_concepts = extract_game_concepts_from_meta(game)

        is_fav = bool(act.get("is_favourite", False))
        wtp = bool(act.get("want_to_play", False))
        played = bool(act.get("already_played", False))
        rating = act.get("rating")

        if is_fav:
            favourited_appids.add(appid)
            favourited_games.append(game)
            for g in g_genres:
                positive_genres[g] += 3.5
            for c in g_concepts:
                positive_concepts[c] += 3.0

        if wtp:
            want_to_play_appids.add(appid)
            for g in g_genres:
                positive_genres[g] += 2.0
            for c in g_concepts:
                positive_concepts[c] += 2.0

        if played:
            already_played_appids.add(appid)
            played_games_records.append({
                "activity": act,
                "game": game,
            })
            if rating is not None and isinstance(rating, (int, float)):
                # Ratings 1 to 10
                if rating >= 7:
                    # Positive signal
                    weight = 1.0 + (rating - 7.0) * 0.8  # 7 -> 1.0, 10 -> 3.4
                    if rating >= 8:
                        high_rated_games.append((int(rating), game))
                    for g in g_genres:
                        positive_genres[g] += weight
                    for c in g_concepts:
                        positive_concepts[c] += weight
                elif rating <= 4:
                    # Negative signal (penalize)
                    penalty = (5.0 - rating) * 0.8  # 4 -> 0.8, 1 -> 3.2
                    for g in g_genres:
                        negative_genres[g] += penalty
                    for c in g_concepts:
                        negative_concepts[c] += penalty
                else:
                    # Neutral rating (5-6)
                    for g in g_genres:
                        positive_genres[g] += 0.5
            else:
                # Played but unrated: mild positive
                for g in g_genres:
                    positive_genres[g] += 1.0
                for c in g_concepts:
                    positive_concepts[c] += 0.8

    # Process explicit preferences
    for g in pref_genres:
        positive_genres[g] += 3.0
    for interest in pref_interests:
        positive_concepts[interest] += 2.5
        for c in extract_query_concepts(interest):
            positive_concepts[c] += 2.5

    # Process AI history & interactions
    ai_searched_concepts: Counter[str] = Counter()
    for q_item in ai_history:
        q_text = q_item.get("query", "")
        q_concepts = extract_query_concepts(q_text)
        for c in q_concepts:
            positive_concepts[c] += 1.5
            ai_searched_concepts[c] += 1

        for interaction in q_item.get("interactions", []):
            i_appid = interaction.get("appid")
            i_action = interaction.get("action")
            if isinstance(i_appid, int):
                i_game = get_game_by_appid(i_appid)
                if i_game:
                    i_concepts = extract_game_concepts_from_meta(i_game)
                    w = 1.0 if i_action == "click" else 1.8
                    for c in i_concepts:
                        positive_concepts[c] += w

    # Determine if user is in cold-start (no profile signals)
    is_cold_start = (
        len(positive_genres) == 0 and
        len(positive_concepts) == 0 and
        len(favourited_appids) == 0 and
        len(already_played_appids) == 0
    )

    all_catalog = get_all_games()
    scored_candidates = []

    for game in all_catalog:
        appid = game["appid"]

        # EXCLUDE Already Played games from main recommendations feed
        if appid in already_played_appids:
            continue

        # Exclude favourited games from main recommendations so user discovers new games
        if appid in favourited_appids:
            continue

        candidate_genres = [g.lower() for g in game.get("genres", [])]
        candidate_concepts = extract_game_concepts_from_meta(game)

        # 1. Genre alignment
        genre_score = sum(positive_genres.get(g, 0.0) for g in candidate_genres)
        genre_penalty = sum(negative_genres.get(g, 0.0) for g in candidate_genres)

        # 2. Concept alignment
        concept_score = sum(positive_concepts.get(c, 0.0) for c in candidate_concepts)
        concept_penalty = sum(negative_concepts.get(c, 0.0) for c in candidate_concepts)

        # 3. Similarity bonus to favourited or highly-rated games
        similarity_bonus = 0.0
        anchor_favourite = None
        anchor_rating = None

        if favourited_games:
            for fav in favourited_games:
                fav_genres = [fg.lower() for fg in fav.get("genres", [])]
                shared = set(candidate_genres).intersection(fav_genres)
                if shared:
                    sim = len(shared) * 1.2
                    if sim > similarity_bonus:
                        similarity_bonus = sim
                        anchor_favourite = fav

        if high_rated_games and not anchor_favourite:
            for r_score, hg in high_rated_games:
                hg_genres = [hg_g.lower() for hg_g in hg.get("genres", [])]
                shared = set(candidate_genres).intersection(hg_genres)
                if shared:
                    sim = len(shared) * 1.0
                    if sim > similarity_bonus:
                        similarity_bonus = sim
                        anchor_rating = (r_score, hg)

        # Want to play bonus (user already expressed interest in this specific game)
        wtp_bonus = 3.0 if appid in want_to_play_appids else 0.0

        # Baseline quality prior
        pop_prior = _compute_popularity_prior(game)

        # Net score
        score = (
            (genre_score * 1.2)
            + (concept_score * 1.0)
            + similarity_bonus
            + wtp_bonus
            + pop_prior
            - (genre_penalty * 1.0)
            - (concept_penalty * 0.8)
        )

        # Slight jitter if refresh is requested to provide varied discovery
        if refresh:
            score += random.uniform(-0.3, 0.3)

        # Determine explanation
        explanation = "Recommended for you"
        matched_tags = []

        if anchor_favourite and similarity_bonus > 1.0:
            fav_title = anchor_favourite.get("name") or "your favourite games"
            explanation = f"Similar to {fav_title} in your favourites"
            matched_tags.extend([g.title() for g in candidate_genres[:2]])
        elif anchor_rating and similarity_bonus > 1.0:
            r_num, hg = anchor_rating
            hg_title = hg.get("name") or "games you played"
            explanation = f"Because you enjoyed {hg_title} (Rated {r_num}/10)"
            matched_tags.extend([g.title() for g in candidate_genres[:2]])
        elif any(g in pref_genres for g in candidate_genres):
            matched = [g.title() for g in candidate_genres if g in pref_genres]
            explanation = f"Because you enjoy {matched[0]}"
            matched_tags.extend(matched)
        elif any(c in positive_concepts for c in candidate_concepts):
            matched_c = [c.title() for c in candidate_concepts if c in positive_concepts]
            if matched_c:
                explanation = f"Matches your interest in {matched_c[0]}"
                matched_tags.extend(matched_c)
        elif any(g in positive_genres for g in candidate_genres):
            matched_g = [g.title() for g in candidate_genres if g in positive_genres]
            explanation = f"Based on your interest in {matched_g[0]}"
            matched_tags.extend(matched_g)
        elif is_cold_start:
            top_genre = candidate_genres[0].title() if candidate_genres else "Gaming"
            explanation = f"Popular in {top_genre}"
            matched_tags.extend(candidate_genres[:2])

        scored_candidates.append({
            "appid": appid,
            "title": game.get("name"),
            "name": game.get("name"),
            "header_image": game.get("header_image"),
            "image": game.get("header_image"),
            "genres": game.get("genres", []),
            "price": game.get("price_overview", {}),
            "is_free": game.get("is_free", False),
            "release_date": game.get("release_date"),
            "short_description": game.get("short_description"),
            "trailer": game.get("trailers", [None])[0] if game.get("trailers") else None,
            "trailers": game.get("trailers", []),
            "explanation": explanation,
            "matched_tags": matched_tags or [g.title() for g in game.get("genres", [])[:2]],
            "raw_score": score,
        })

    # Sort descending by raw_score
    scored_candidates.sort(key=lambda x: x["raw_score"], reverse=True)

    # 4. Diversity Enforcement (Avoid excessive repetition of the same primary genre)
    selected_recs: list[dict[str, Any]] = []
    genre_distribution: Counter[str] = Counter()
    max_per_genre = max(3, limit // 4)

    for item in scored_candidates:
        if len(selected_recs) >= limit:
            break
        primary_genre = item["genres"][0].lower() if item.get("genres") else "other"
        if genre_distribution[primary_genre] >= max_per_genre:
            continue
        genre_distribution[primary_genre] += 1
        selected_recs.append(item)

    # If limit not filled due to aggressive filtering, fill with remaining top candidates
    if len(selected_recs) < limit:
        already_selected_ids = {r["appid"] for r in selected_recs}
        for item in scored_candidates:
            if len(selected_recs) >= limit:
                break
            if item["appid"] not in already_selected_ids:
                selected_recs.append(item)

    # Clean up internal scores from output
    cleaned_recs = []
    for idx, r in enumerate(selected_recs):
        item_copy = dict(r)
        item_copy.pop("raw_score", None)
        # Normalize match confidence score for UI display (75 - 98)
        item_copy["confidence"] = max(70, min(99, 98 - idx))
        cleaned_recs.append(item_copy)

    # 5. Build Already Played section
    # Sort played games: highest rated first, then unrated
    played_games_records.sort(
        key=lambda x: (
            x["activity"].get("rating") is not None,
            x["activity"].get("rating") or 0,
            x["activity"].get("updated_at") or "",
        ),
        reverse=True,
    )

    already_played_section = []
    for item in played_games_records[:limit]:
        g = item["game"]
        act = item["activity"]
        r = act.get("rating")
        review = act.get("review") or act.get("review_text")
        exp = f"Rated {r}/10 by you" if r is not None else "In your played collection"
        already_played_section.append({
            "appid": g.get("appid"),
            "title": g.get("name"),
            "name": g.get("name"),
            "header_image": g.get("header_image"),
            "image": g.get("header_image"),
            "genres": g.get("genres", []),
            "price": g.get("price_overview", {}),
            "is_free": g.get("is_free", False),
            "trailer": g.get("trailers", [None])[0] if g.get("trailers") else None,
            "trailers": g.get("trailers", []),
            "rating": r,
            "review": review,
            "explanation": exp,
        })

    return {
        "success": True,
        "feed_revision": feed_revision,
        "is_cold_start": is_cold_start,
        "recommendations": cleaned_recs,
        "already_played_recommendations": already_played_section,
        "total_recommendations": len(cleaned_recs),
        "total_already_played": len(already_played_section),
    }
