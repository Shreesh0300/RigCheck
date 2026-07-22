"""
RigCheck GPU Tier Engine — Runtime Lookup
==========================================
Loads generated JSON files and provides lookup functions for GPU models.
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

GPU_DIR = Path(__file__).parent

_gpu_lookup: dict = {}
_gpu_tiers: dict = {}
_normalised_keys: dict[str, str] = {}   # lowercase_normalised → original key


def _load_data():
    """Load gpu_lookup.json and gpu_tiers.json from disk (once)."""
    global _gpu_lookup, _gpu_tiers, _normalised_keys

    lookup_path = GPU_DIR / "gpu_lookup.json"
    tiers_path = GPU_DIR / "gpu_tiers.json"

    if lookup_path.exists():
        with open(lookup_path, "r", encoding="utf-8") as f:
            _gpu_lookup = json.load(f)
    else:
        _gpu_lookup = {}

    if tiers_path.exists():
        with open(tiers_path, "r", encoding="utf-8") as f:
            _gpu_tiers = json.load(f)
    else:
        _gpu_tiers = {}

    # Build normalised key → original name index for fuzzy matching
    _normalised_keys = {}
    for name in _gpu_lookup:
        key = _normalize_for_search(name)
        _normalised_keys[key] = name


# ─────────────────────────────────────────────────────────────────────────────
# NAME NORMALISATION
# ─────────────────────────────────────────────────────────────────────────────

_STRIP_PREFIXES = [
    r"^nvidia\s+",
    r"^amd\s+",
    r"^intel\s+",
    r"^geforce\s+",
    r"^radeon\s+",
    r"\s+graphics\s*$",
    r"\s+gpu\s*$",
]


def _normalize_for_search(raw: str) -> str:
    """Normalize a GPU name for search/matching."""
    if not isinstance(raw, str):
        return ""
    name = raw.strip()
    for pat in _STRIP_PREFIXES:
        name = re.sub(pat, "", name, flags=re.IGNORECASE).strip()
    name = re.sub(r"[-_]", " ", name)
    name = re.sub(r"\s{2,}", " ", name).strip()
    return name.lower()


def _fuzzy_match(query: str) -> Optional[str]:
    """
    Try to match a user-provided GPU name against the lookup database.
    Returns the original (un-normalised) key from gpu_lookup, or None.
    """
    if not _normalised_keys:
        _load_data()

    normalised_query = _normalize_for_search(query)

    # 1. Exact match
    if normalised_query in _normalised_keys:
        return _normalised_keys[normalised_query]

    # 2. Substring match — check if query is contained in any key or vice versa with word boundaries
    for key, original in _normalised_keys.items():
        if len(key) <= 3 and key in ["gpu", "pro", "vii", "ion", "uhd"]:
            continue
        try:
            if (re.search(r'\b' + re.escape(normalised_query) + r'\b', key) or 
                    re.search(r'\b' + re.escape(key) + r'\b', normalised_query)):
                return original
        except Exception:
            pass

    # 3. difflib fuzzy match
    candidates = list(_normalised_keys.keys())
    matches = difflib.get_close_matches(normalised_query, candidates, n=1, cutoff=0.6)
    if matches:
        return _normalised_keys[matches[0]]

    return None


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def getGpuTier(gpu_name: str) -> Optional[str]:
    """
    Return the tier (S/A/B/C/D) for a given GPU name.
    Returns None if the GPU is not found.
    """
    if not _gpu_lookup:
        _load_data()

    matched = _fuzzy_match(gpu_name)
    if matched and matched in _gpu_lookup:
        return _gpu_lookup[matched]["tier"]
    return None


def getGpuScore(gpu_name: str) -> Optional[int]:
    """
    Return the benchmark score for a given GPU name.
    Returns None if the GPU is not found.
    """
    if not _gpu_lookup:
        _load_data()

    matched = _fuzzy_match(gpu_name)
    if matched and matched in _gpu_lookup:
        return _gpu_lookup[matched]["benchmark_score"]
    return None


def validateGpu(gpu_name: str) -> dict:
    """
    Full validation result for a given GPU name.

    Returns a dict with:
        matched_name     : str | None  — the canonical name found
        tier             : str | None  — S/A/B/C/D
        benchmark_score  : int | None
        manufacturer     : str | None
        error            : str | None  — set if GPU not found
    """
    if not _gpu_lookup:
        _load_data()

    matched = _fuzzy_match(gpu_name)
    if matched is None or matched not in _gpu_lookup:
        return {
            "matched_name": None,
            "tier": None,
            "benchmark_score": None,
            "manufacturer": None,
            "error": f"GPU model not recognized. Please check the spelling and try again.",
        }

    entry = _gpu_lookup[matched]
    return {
        "matched_name": matched,
        "tier": entry.get("tier"),
        "benchmark_score": entry.get("benchmark_score"),
        "manufacturer": entry.get("manufacturer"),
        "error": None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# MODULE INIT — Eagerly load data on import
# ─────────────────────────────────────────────────────────────────────────────

_load_data()
