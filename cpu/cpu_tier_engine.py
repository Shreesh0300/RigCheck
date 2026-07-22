"""
RigCheck CPU Tier Engine — Runtime Lookup
==========================================
Loads generated JSON files and provides lookup functions.

Functions:
    getCpuTier(cpu_name)   → str   (S/A/B/C/D)
    getCpuScore(cpu_name)  → int   (benchmark score)
    validateCpu(cpu_name)  → dict  (full validation result)
"""

from __future__ import annotations

import json
import re
import difflib
from pathlib import Path
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────────────────────

CPU_DIR = Path(__file__).parent

_cpu_lookup: dict = {}
_cpu_tiers: dict = {}
_cpu_aliases: dict = {}
_normalised_keys: dict[str, str] = {}   # lowercase_normalised → original key


def _load_data():
    """Load cpu_lookup.json, cpu_tiers.json, and cpu_aliases.json from disk (once)."""
    global _cpu_lookup, _cpu_tiers, _cpu_aliases, _normalised_keys

    lookup_path = CPU_DIR / "cpu_lookup.json"
    tiers_path = CPU_DIR / "cpu_tiers.json"
    aliases_path = CPU_DIR / "cpu_aliases.json"

    if lookup_path.exists():
        with open(lookup_path, "r", encoding="utf-8") as f:
            _cpu_lookup = json.load(f)
    else:
        _cpu_lookup = {}

    if tiers_path.exists():
        with open(tiers_path, "r", encoding="utf-8") as f:
            _cpu_tiers = json.load(f)
    else:
        _cpu_tiers = {}

    if aliases_path.exists():
        with open(aliases_path, "r", encoding="utf-8") as f:
            _cpu_aliases = json.load(f)
    else:
        _cpu_aliases = {}

    # Build normalised key → original name index for fuzzy matching
    _normalised_keys = {}
    for name in _cpu_lookup:
        key = _normalize_for_search(name)
        _normalised_keys[key] = name


# ─────────────────────────────────────────────────────────────────────────────
# NAME NORMALISATION (mirrors build_cpu_tiers.py)
# ─────────────────────────────────────────────────────────────────────────────

_STRIP_PREFIXES = [
    r"^intel\s+",
    r"^amd\s+",
    r"^apple\s+",
    r"^core\s+",
    r"\s+processor\s*$",
    r"\s+cpu\s*$",
]


def strip_clock_suffix(name: str) -> str:
    """Strips clock suffixes like ' @ 2.60GHz' from CPU names."""
    if not isinstance(name, str):
        return ""
    return re.sub(r"\s*@\s*[\d\.]+\s*[Gg][Hh][Zz].*$", "", name).strip()


def _normalize_for_search(raw: str) -> str:
    """Normalize a CPU name for search/matching."""
    if not isinstance(raw, str):
        return ""
    name = strip_clock_suffix(raw)
    for pat in _STRIP_PREFIXES:
        name = re.sub(pat, "", name, flags=re.IGNORECASE).strip()
    name = re.sub(r"[-_]", " ", name)
    name = re.sub(r"\s{2,}", " ", name).strip()
    return name.lower()


def _fuzzy_match(query: str) -> Optional[str]:
    """
    Try to match a user-provided CPU name against the lookup database.
    Returns the original (un-normalised) key from cpu_lookup, or None.
    """
    if not _cpu_lookup:
        return None

    # 1. Alias lookup (using the pre-generated cpu_aliases.json)
    norm_query = re.sub(r"\s+", " ", re.sub(r"[-_]", " ", query.strip())).lower()
    if norm_query in _cpu_aliases:
        return _cpu_aliases[norm_query]

    # Check normalized stripped of clock suffix
    stripped_query = strip_clock_suffix(query)
    norm_stripped = re.sub(r"\s+", " ", re.sub(r"[-_]", " ", stripped_query.strip())).lower()
    if norm_stripped in _cpu_aliases:
        return _cpu_aliases[norm_stripped]

    # 2. Exact match in canonical keys
    normalised_query_search = _normalize_for_search(query)
    if normalised_query_search in _normalised_keys:
        return _normalised_keys[normalised_query_search]

    # 3. Substring match — check if query is contained in any key or vice versa with word boundaries
    for key, original in _normalised_keys.items():
        if len(key) <= 3 and key in ["cpu", "pro", "max"]:
            continue
        try:
            if (re.search(r'\b' + re.escape(normalised_query_search) + r'\b', key) or 
                    re.search(r'\b' + re.escape(key) + r'\b', normalised_query_search)):
                return original
        except Exception:
            pass

    # 4. difflib close match
    candidates = list(_normalised_keys.keys())
    matches = difflib.get_close_matches(normalised_query_search, candidates, n=1, cutoff=0.6)
    if matches:
        return _normalised_keys[matches[0]]

    return None


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def getCpuTier(cpu_name: str) -> Optional[str]:
    """
    Return the tier (S/A/B/C/D) for a given CPU name.
    Returns None if the CPU is not found.
    """
    if not _cpu_lookup:
        _load_data()

    matched = _fuzzy_match(cpu_name)
    if matched and matched in _cpu_lookup:
        return _cpu_lookup[matched]["tier"]
    return None


def getCpuScore(cpu_name: str) -> Optional[int]:
    """
    Return the benchmark score for a given CPU name.
    Returns None if the CPU is not found.
    """
    if not _cpu_lookup:
        _load_data()

    matched = _fuzzy_match(cpu_name)
    if matched and matched in _cpu_lookup:
        return _cpu_lookup[matched]["benchmark_score"]
    return None


def validateCpu(cpu_name: str) -> dict:
    """
    Full validation result for a given CPU name.

    Returns a dict with:
        matched_name     : str | None  — the canonical name found
        tier             : str | None  — S/A/B/C/D
        benchmark_score  : int | None
        manufacturer     : str | None
        cores            : int | None
        threads          : int | None
        category         : str | None
        error            : str | None  — set if CPU not found
    """
    if not _cpu_lookup:
        _load_data()

    matched = _fuzzy_match(cpu_name)
    if matched is None or matched not in _cpu_lookup:
        return {
            "matched_name": None,
            "tier": None,
            "benchmark_score": None,
            "manufacturer": None,
            "cores": None,
            "threads": None,
            "category": None,
            "error": f"CPU not found: '{cpu_name}'",
        }

    entry = _cpu_lookup[matched]
    return {
        "matched_name": matched,
        "tier": entry.get("tier"),
        "benchmark_score": entry.get("benchmark_score"),
        "manufacturer": entry.get("manufacturer"),
        "cores": entry.get("cores"),
        "threads": entry.get("threads"),
        "category": entry.get("category"),
        "error": None,
    }


def get_tier_score_range(tier: str) -> Optional[tuple[int, int]]:
    """
    Return (min_score, max_score) for a given tier.
    Useful for compatibility comparisons against game requirements
    that specify minimum tier as an integer.
    """
    if not _cpu_tiers:
        _load_data()

    tier = tier.upper()
    if tier not in _cpu_tiers or not _cpu_tiers[tier]:
        return None

    scores = [entry["benchmark_score"] for entry in _cpu_tiers[tier]]
    return (min(scores), max(scores))


def get_tier_representative_score(tier_int: int) -> int:
    """
    Given a tier as integer (1-5 mapping used in games_dataset.csv),
    return a representative benchmark score for comparison.

    Mapping: 1 → D midpoint, 2 → C midpoint, 3 → B midpoint,
             4 → A midpoint, 5 → S midpoint
    """
    if not _cpu_tiers:
        _load_data()

    tier_map = {1: "D", 2: "C", 3: "B", 4: "A", 5: "S"}
    tier_letter = tier_map.get(tier_int, "D")

    entries = _cpu_tiers.get(tier_letter, [])
    if not entries:
        # Fallback scores if tiers aren't loaded
        fallbacks = {1: 5000, 2: 12000, 3: 20000, 4: 35000, 5: 55000}
        return fallbacks.get(tier_int, 5000)

    scores = [e["benchmark_score"] for e in entries]
    # Return the median score of the tier
    scores.sort()
    mid = len(scores) // 2
    return scores[mid]


# ─────────────────────────────────────────────────────────────────────────────
# MODULE INIT — Eagerly load data on import
# ─────────────────────────────────────────────────────────────────────────────

_load_data()
