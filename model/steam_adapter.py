"""
RigCheck Steam Adapter
=======================
Converts a single Steam game object (from games_database_final.json) into
the exact flat-dict schema expected by the existing compatibility engine.

This is a pure data-mapping module — no I/O, no side effects, no engine logic.

Input:  One game dict from games_database_final.json
Output: One flat dict with the same column names as games_dataset.csv

Field mapping:
    Steam JSON field              →  Flat dict key
    ─────────────────────────────    ────────────────────
    name                          →  Title
    short_description             →  Description
    genres (list)                 →  Tags (comma string)
    price_overview.initial / 100  →  Price_INR
    minimum.gpu_tiers[].tier      →  Min_GPU_Tier (int 1-5)
    recommended.gpu_tiers[].tier  →  Rec_GPU_Tier (int 1-5)
    minimum.cpu_tiers[].tier      →  Min_CPU_Tier (int 1-5)
    recommended.cpu_tiers[].tier  →  Rec_CPU_Tier (int 1-5)
    minimum.ram_gb                →  Min_RAM_GB
    minimum.storage_gb            →  Required_Storage_GB
    appid                         →  Steam_AppID
"""

from __future__ import annotations

from typing import Any, Optional


# ─────────────────────────────────────────────────────────────────────────────
# TIER CONVERSION
# ─────────────────────────────────────────────────────────────────────────────

# Letter tiers from the Steam pipeline → integer tiers used by the engine
_LETTER_TO_INT: dict[str, int] = {
    "D": 1,
    "C": 2,
    "B": 3,
    "A": 4,
    "S": 5,
}

# Default tier when no hardware tier data is available
_DEFAULT_TIER: int = 1


def _letter_tier_to_int(letter: str) -> int:
    """Convert a single letter tier (D/C/B/A/S) to an integer (1-5)."""
    return _LETTER_TO_INT.get(str(letter).upper(), _DEFAULT_TIER)


def _extract_lowest_tier(tier_entries: list[dict[str, Any]]) -> int:
    """
    Extract the lowest (least demanding) tier from a list of hardware tier entries.

    Each entry looks like: {"name": "GTX 1060", "tier": "B"}

    When a game lists multiple CPUs/GPUs as alternatives (e.g. "Intel i5 OR AMD
    Ryzen 5"), the player only needs to meet ONE of them.  We take the lowest
    tier so the compatibility engine uses the least demanding requirement.

    Returns _DEFAULT_TIER if the list is empty or contains no valid tiers.
    """
    if not tier_entries:
        return _DEFAULT_TIER

    int_tiers: list[int] = []
    for entry in tier_entries:
        tier_val = entry.get("tier")
        if tier_val is not None:
            int_tiers.append(_letter_tier_to_int(tier_val))

    return min(int_tiers) if int_tiers else _DEFAULT_TIER


# ─────────────────────────────────────────────────────────────────────────────
# PRICE EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

def _extract_price_inr(game: dict[str, Any]) -> int:
    """
    Extract game price in INR (paise → rupees).

    Steam stores prices in the smallest currency unit (paise for INR),
    so 299900 = ₹2999.  Free-to-play games have is_free=True.

    Returns 0 for free games or when price data is missing.
    """
    if game.get("is_free"):
        return 0

    price_overview = game.get("price_overview")
    if not price_overview:
        return 0

    # Use 'initial' (base price before discount) for budget comparison
    raw_price = price_overview.get("initial")
    if raw_price is None:
        return 0

    # Steam prices are in paise (1/100 of a rupee) for INR
    # e.g., 299900 paise = ₹2999
    return int(raw_price) // 100


# ─────────────────────────────────────────────────────────────────────────────
# REQUIREMENT EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

def _safe_int(value: Any, default: int = 0) -> int:
    """Safely convert a value to int, returning default on failure."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _get_requirement_block(game: dict[str, Any], level: str) -> dict[str, Any]:
    """
    Get the 'minimum' or 'recommended' requirement block from a game.

    Returns an empty dict if the block is missing or None.
    """
    block = game.get(level)
    return block if isinstance(block, dict) else {}


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def adapt_steam_game(game: dict[str, Any]) -> dict[str, Any]:
    """
    Convert one Steam game object into the flat schema expected by the
    existing RigCheck compatibility engine.

    Parameters
    ----------
    game : dict
        A single game dict from games_database_final.json.

    Returns
    -------
    dict
        Flat dict with these exact keys:
        Title, Description, Tags, Price_INR,
        Min_GPU_Tier, Rec_GPU_Tier, Min_CPU_Tier, Rec_CPU_Tier,
        Min_RAM_GB, Required_Storage_GB, Steam_AppID, Header_Image, Release_Date
    """
    min_req = _get_requirement_block(game, "minimum")
    rec_req = _get_requirement_block(game, "recommended")

    # Collect metadata for indexing
    combined_tags = []
    
    # Genres
    genres = game.get("genres", [])
    if isinstance(genres, list):
        for g in genres:
            if isinstance(g, dict):
                combined_tags.append(g.get("description", ""))
            elif isinstance(g, str):
                combined_tags.append(g)

    # Categories
    categories = game.get("categories", [])
    if isinstance(categories, list):
        for c in categories:
            if isinstance(c, dict):
                combined_tags.append(c.get("description", ""))
            elif isinstance(c, str):
                combined_tags.append(c)

    # Developers
    developers = game.get("developers", [])
    if isinstance(developers, list):
        combined_tags.extend([str(d) for d in developers])

    # Detailed description for BM25 text corpus
    about = game.get("about_the_game", "")
    if about:
        combined_tags.append(str(about))

    tags_str = ", ".join([t for t in combined_tags if t])

    # GPU tiers
    min_gpu_tier = _extract_lowest_tier(min_req.get("gpu_tiers", []))
    rec_gpu_tier = _extract_lowest_tier(rec_req.get("gpu_tiers", []))
    # Recommended should never be lower than minimum
    rec_gpu_tier = max(rec_gpu_tier, min_gpu_tier)

    # CPU tiers
    min_cpu_tier = _extract_lowest_tier(min_req.get("cpu_tiers", []))
    rec_cpu_tier = _extract_lowest_tier(rec_req.get("cpu_tiers", []))
    rec_cpu_tier = max(rec_cpu_tier, min_cpu_tier)

    # RAM: use minimum requirement; fall back to recommended if minimum is missing
    min_ram = _safe_int(min_req.get("ram_gb"), default=0)
    if min_ram == 0:
        min_ram = _safe_int(rec_req.get("ram_gb"), default=2)

    # Storage: use minimum requirement; fall back to recommended
    min_storage = _safe_int(min_req.get("storage_gb"), default=0)
    if min_storage == 0:
        min_storage = _safe_int(rec_req.get("storage_gb"), default=0)

    return {
        "Title": str(game.get("name", "")),
        "Description": str(game.get("short_description", "")),
        "Tags": tags_str,
        "Price_INR": _extract_price_inr(game),
        "Min_GPU_Tier": min_gpu_tier,
        "Rec_GPU_Tier": rec_gpu_tier,
        "Min_CPU_Tier": min_cpu_tier,
        "Rec_CPU_Tier": rec_cpu_tier,
        "Min_RAM_GB": min_ram,
        "Required_Storage_GB": min_storage,
        "Steam_AppID": _safe_int(game.get("appid"), default=0),
        "Header_Image": game.get("header_image", ""),
    }


def adapt_all_games(games: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert a list of Steam game objects into the flat schema.

    Skips games that have no title (defensive filter).

    Parameters
    ----------
    games : list of dict
        All game dicts from games_database_final.json.

    Returns
    -------
    list of dict
        Each dict has the same keys as a row in games_dataset.csv.
    """
    adapted: list[dict[str, Any]] = []
    for game in games:
        if not game.get("name"):
            continue
        adapted.append(adapt_steam_game(game))
    return adapted
