"""
RigCheck Steam Database Loader
================================
Loads and caches games_database_final.json — the output of the Steam pipeline.

Responsibilities:
  - Load the JSON database once from disk
  - Cache it in memory for the lifetime of the process
  - Provide helper methods for game lookup and search

This module handles I/O only.  It does NOT contain compatibility logic,
tier conversion, or schema adaptation — those live in steam_adapter.py.

Usage:
    from model.steam_database import load_database, get_all_games, search_games

    db = load_database()            # loads + caches
    games = get_all_games()         # returns full list
    game = get_game_by_appid(730)   # exact appid lookup
    results = search_games("witcher")  # name search
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE PATH
# ─────────────────────────────────────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DB_PATH = _PROJECT_ROOT / "data" / "games_database_final.json"


# ─────────────────────────────────────────────────────────────────────────────
# IN-MEMORY CACHE
# ─────────────────────────────────────────────────────────────────────────────

_cached_games: Optional[list[dict[str, Any]]] = None
_appid_index: Optional[dict[int, dict[str, Any]]] = None
_name_index: Optional[dict[str, dict[str, Any]]] = None


def _build_indices(games: list[dict[str, Any]]) -> None:
    """Build O(1) lookup indices for appid and name."""
    global _appid_index, _name_index

    _appid_index = {}
    _name_index = {}

    for game in games:
        # Index by appid
        appid = game.get("appid")
        if appid is not None:
            _appid_index[int(appid)] = game

        # Index by normalized name (lowercase, stripped)
        name = game.get("name")
        if name:
            _name_index[str(name).lower().strip()] = game


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def load_database(path: Optional[str | Path] = None) -> list[dict[str, Any]]:
    """
    Load the Steam game database from disk and cache it in memory.

    Subsequent calls return the cached version unless the cache is cleared.

    Parameters
    ----------
    path : str or Path, optional
        Override path to the JSON file.  Defaults to data/games_database_final.json.

    Returns
    -------
    list of dict
        The full list of game objects from the database.

    Raises
    ------
    FileNotFoundError
        If the database file does not exist.
    json.JSONDecodeError
        If the file contains invalid JSON.
    """
    global _cached_games

    if _cached_games is not None:
        return _cached_games

    db_path = Path(path) if path else _DB_PATH

    if not db_path.exists():
        raise FileNotFoundError(
            f"Steam database not found at {db_path}.\n"
            f"Run the Steam pipeline (steam/01–05) to generate it."
        )

    with open(db_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array in {db_path}, got {type(data).__name__}.")

    _cached_games = data
    _build_indices(data)

    return _cached_games


def get_all_games() -> list[dict[str, Any]]:
    """
    Return all games in the database.

    Automatically loads the database on first call.
    """
    if _cached_games is None:
        load_database()
    return _cached_games  # type: ignore[return-value]


def get_game_by_appid(appid: int) -> Optional[dict[str, Any]]:
    """
    Look up a single game by its Steam App ID.

    Parameters
    ----------
    appid : int
        The Steam application ID (e.g. 1091500 for Cyberpunk 2077).

    Returns
    -------
    dict or None
        The game object, or None if not found.
    """
    if _appid_index is None:
        load_database()
    return _appid_index.get(int(appid))  # type: ignore[union-attr]


def get_game_by_name(name: str) -> Optional[dict[str, Any]]:
    """
    Look up a single game by exact name (case-insensitive).

    Parameters
    ----------
    name : str
        The game title (e.g. "Cyberpunk 2077").

    Returns
    -------
    dict or None
        The game object, or None if not found.
    """
    if _name_index is None:
        load_database()
    return _name_index.get(name.lower().strip())  # type: ignore[union-attr]


def search_games(query: str) -> list[dict[str, Any]]:
    """
    Search games by name (case-insensitive partial match).

    Supports:
      - Exact match (highest priority)
      - Partial / substring match

    Parameters
    ----------
    query : str
        Search string (e.g. "witcher", "cyber", "flight sim").

    Returns
    -------
    list of dict
        Matching game objects, ordered by relevance:
        exact matches first, then partial matches.
    """
    if _cached_games is None:
        load_database()

    query_lower = query.lower().strip()
    if not query_lower:
        return []

    exact: list[dict[str, Any]] = []
    partial: list[dict[str, Any]] = []

    for game in _cached_games:  # type: ignore[union-attr]
        name = str(game.get("name", "")).lower()
        if name == query_lower:
            exact.append(game)
        elif query_lower in name:
            partial.append(game)

    return exact + partial


def get_database_stats() -> dict[str, Any]:
    """
    Return summary statistics about the loaded database.

    Useful for diagnostics and logging.
    """
    if _cached_games is None:
        load_database()

    games = _cached_games  # type: ignore[assignment]
    total = len(games)

    with_min = sum(1 for g in games if g.get("minimum"))
    with_rec = sum(1 for g in games if g.get("recommended"))
    with_price = sum(1 for g in games if g.get("price_overview"))
    free = sum(1 for g in games if g.get("is_free"))

    return {
        "total_games": total,
        "with_minimum_reqs": with_min,
        "with_recommended_reqs": with_rec,
        "with_price_data": with_price,
        "free_to_play": free,
    }


def clear_cache() -> None:
    """
    Clear the in-memory cache.

    Useful for testing or if the database file is updated at runtime.
    """
    global _cached_games, _appid_index, _name_index
    _cached_games = None
    _appid_index = None
    _name_index = None
