"""
RigCheck Compatibility Workflow Engine
=======================================
Evaluates hardware compatibility for every candidate game.

Pipeline per game:
  Step 1: GPU Evaluation   (PASS / BELOW_RECOMMENDED / BELOW_MINIMUM)
  Step 2: CPU Evaluation   (PASS / BELOW_RECOMMENDED / BELOW_MINIMUM)
  Step 3: RAM Evaluation   (PASS / FAIL with deficiency details)
  Step 4: Storage Evaluation (PASS / FAIL via Storage Availability Engine)
  Step 5: Compatibility Score  (weighted 0-100%)
  Step 6: Game Ranking (compatibility → vibe → budget)

Does NOT modify frontend, APIs, or existing engine logic.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# IMPORTS — sibling modules
# ─────────────────────────────────────────────────────────────────────────────

# Add project root to path so we can import from cpu/ and model/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from model.storage_engine import check_storage

# GPU lookup (lazy-loaded)
_gpu_lookup: dict = {}
_gpu_tiers: dict = {}

# CPU lookup (lazy-loaded)
_cpu_lookup: dict = {}
_cpu_tiers: dict = {}


def _load_gpu_data():
    global _gpu_lookup, _gpu_tiers
    gpu_dir = _PROJECT_ROOT / "gpu"
    lookup_path = gpu_dir / "gpu_lookup.json"
    tiers_path = gpu_dir / "gpu_tiers.json"
    if lookup_path.exists():
        with open(lookup_path, "r", encoding="utf-8") as f:
            _gpu_lookup = json.load(f)
    if tiers_path.exists():
        with open(tiers_path, "r", encoding="utf-8") as f:
            _gpu_tiers = json.load(f)


def _load_cpu_data():
    global _cpu_lookup, _cpu_tiers
    cpu_dir = _PROJECT_ROOT / "cpu"
    lookup_path = cpu_dir / "cpu_lookup.json"
    tiers_path = cpu_dir / "cpu_tiers.json"
    if lookup_path.exists():
        with open(lookup_path, "r", encoding="utf-8") as f:
            _cpu_lookup = json.load(f)
    if tiers_path.exists():
        with open(tiers_path, "r", encoding="utf-8") as f:
            _cpu_tiers = json.load(f)


def _ensure_data():
    if not _gpu_lookup:
        _load_gpu_data()
    if not _cpu_lookup:
        _load_cpu_data()


# ─────────────────────────────────────────────────────────────────────────────
# TIER ↔ SCORE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

# Integer tier (1-5 from games_dataset.csv) → letter tier
_INT_TO_LETTER = {1: "D", 2: "C", 3: "B", 4: "A", 5: "S"}


def _get_tier_representative_score(tiers_data: dict, tier_int: int) -> int:
    """
    Get a representative benchmark score for a given integer tier.
    Returns the median score of the corresponding letter tier.
    """
    letter = _INT_TO_LETTER.get(tier_int, "D")
    entries = tiers_data.get(letter, [])
    if not entries:
        # Fallback scores
        fallbacks = {1: 5000, 2: 12000, 3: 20000, 4: 35000, 5: 55000}
        return fallbacks.get(tier_int, 5000)
    scores = sorted([e.get("benchmark_score", 0) for e in entries])
    return scores[len(scores) // 2]


def _get_user_gpu_score(user_gpu_tier: int) -> int:
    """Convert user's GPU tier integer to a representative benchmark score."""
    _ensure_data()
    return _get_tier_representative_score(_gpu_tiers, user_gpu_tier)


def _get_user_cpu_score(user_cpu_name: Optional[str]) -> Optional[int]:
    """Look up user's CPU benchmark score from name (fuzzy matching via cpu_tier_engine)."""
    if not user_cpu_name:
        return None
    try:
        from cpu.cpu_tier_engine import getCpuScore
        return getCpuScore(user_cpu_name)
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# COMPONENT WEIGHTS
# ─────────────────────────────────────────────────────────────────────────────

WEIGHT_GPU     = 0.35
WEIGHT_CPU     = 0.25
WEIGHT_RAM     = 0.25
WEIGHT_STORAGE = 0.15


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — GPU EVALUATION
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_gpu(user_gpu_tier: int, game_min_gpu: int,
                 game_rec_gpu: Optional[int] = None,
                 user_gpu_score: Optional[int] = None) -> dict:
    """
    Compare user GPU tier vs game requirements.
    Both are integers 1-5 (mapping to D/C/B/A/S).
    """
    _ensure_data()

    if user_gpu_score is not None:
        user_score = user_gpu_score
    else:
        user_score = _get_tier_representative_score(_gpu_tiers, user_gpu_tier)
    min_score = _get_tier_representative_score(_gpu_tiers, game_min_gpu)
    rec_score = _get_tier_representative_score(_gpu_tiers, game_rec_gpu) if game_rec_gpu else min_score

    if user_score >= rec_score:
        status = "PASS"
        label = "Excellent"
        sub_score = 100.0
    elif user_score >= min_score:
        status = "BELOW_RECOMMENDED"
        label = "Meets Minimum"
        # Scale linearly between min and rec
        range_val = max(rec_score - min_score, 1)
        ratio = (user_score - min_score) / range_val
        sub_score = 60.0 + ratio * 30.0  # 60-90 range
    else:
        status = "BELOW_MINIMUM"
        label = "Below Minimum"
        # Scale based on how far below minimum
        if min_score > 0:
            ratio = min(user_score / min_score, 1.0)
            sub_score = ratio * 50.0  # 0-50 range
        else:
            sub_score = 0.0

    return {
        "status": status,
        "label": label,
        "sub_score": round(sub_score, 1),
        "detail": f"GPU Tier {user_gpu_tier} vs required Tier {game_min_gpu}"
                  + (f" (recommended Tier {game_rec_gpu})" if game_rec_gpu else ""),
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — CPU EVALUATION
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_cpu(user_cpu_name: Optional[str], game_min_cpu: int,
                 game_rec_cpu: Optional[int] = None,
                 user_cpu_score: Optional[int] = None,
                 user_cpu_tier: Optional[int] = None) -> dict:
    """
    Compare user CPU (by name) vs game requirements (integer tier 1-5).
    If user_cpu_name is None, returns a neutral pass (assumes adequate).
    """
    _ensure_data()

    if not user_cpu_name and user_cpu_tier is None:
        return {
            "status": "PASS",
            "label": "Not Evaluated",
            "sub_score": 75.0,  # neutral — don't penalise, don't boost
            "detail": "CPU not specified; skipping evaluation.",
        }

    if user_cpu_score is not None:
        user_score = user_cpu_score
    else:
        user_score = _get_user_cpu_score(user_cpu_name)

    if user_score is None:
        if user_cpu_tier is not None:
            user_score = _get_tier_representative_score(_cpu_tiers, user_cpu_tier)
        else:
            return {
                "status": "PASS",
                "label": "Unknown CPU",
                "sub_score": 60.0,
                "detail": f"Could not find benchmark data for '{user_cpu_name}'.",
            }

    min_score = _get_tier_representative_score(_cpu_tiers, game_min_cpu)
    rec_score = _get_tier_representative_score(_cpu_tiers, game_rec_cpu) if game_rec_cpu else min_score

    if user_score >= rec_score:
        status = "PASS"
        label = "Excellent"
        sub_score = 100.0
    elif user_score >= min_score:
        status = "BELOW_RECOMMENDED"
        label = "Meets Minimum"
        range_val = max(rec_score - min_score, 1)
        ratio = (user_score - min_score) / range_val
        sub_score = 60.0 + ratio * 30.0
    else:
        status = "BELOW_MINIMUM"
        label = "Below Minimum"
        if min_score > 0:
            ratio = min(user_score / min_score, 1.0)
            sub_score = ratio * 50.0
        else:
            sub_score = 0.0

    return {
        "status": status,
        "label": label,
        "sub_score": round(sub_score, 1),
        "detail": f"CPU '{user_cpu_name}' (score: {user_score}) vs required Tier {game_min_cpu}"
                  + (f" (recommended Tier {game_rec_cpu})" if game_rec_cpu else ""),
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — RAM EVALUATION
# ─────────────────────────────────────────────────────────────────────────────

_RAM_ISSUE_DESCRIPTIONS = [
    "Stuttering",
    "Longer loading times",
    "Frame drops",
]


def evaluate_ram(user_ram_gb: int, game_min_ram_gb: int) -> dict:
    """
    Compare user RAM vs game minimum requirement.
    """
    if user_ram_gb >= game_min_ram_gb:
        # Determine how much headroom
        headroom = user_ram_gb - game_min_ram_gb
        if headroom >= 8:
            sub_score = 100.0
        elif headroom >= 4:
            sub_score = 90.0
        else:
            sub_score = 80.0

        return {
            "status": "PASS",
            "label": "Enough",
            "sub_score": sub_score,
            "detail": f"{user_ram_gb}GB available, {game_min_ram_gb}GB required.",
        }

    shortfall = game_min_ram_gb - user_ram_gb
    # Scale sub-score based on deficiency ratio
    ratio = user_ram_gb / max(game_min_ram_gb, 1)
    sub_score = max(ratio * 60.0, 10.0)  # floor at 10

    issues_str = "\n".join(f"  • {issue}" for issue in _RAM_ISSUE_DESCRIPTIONS)
    detail = (
        f"❌ {user_ram_gb}GB detected. This game requires at least "
        f"{game_min_ram_gb}GB RAM.\n"
        f"You are short by {shortfall}GB RAM.\n"
        f"Expected issues:\n{issues_str}"
    )

    return {
        "status": "FAIL",
        "label": f"❌ Need {shortfall}GB More RAM",
        "sub_score": round(sub_score, 1),
        "detail": detail,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — STORAGE EVALUATION
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_storage(user_storage_gb: Optional[float],
                     game_required_gb: float) -> dict:
    """
    Use the Storage Availability Engine (pure PASS/FAIL).
    If user_storage_gb is None, assume PASS (not specified).
    """
    if user_storage_gb is None:
        return {
            "status": "PASS",
            "label": "Not Evaluated",
            "sub_score": 75.0,
            "detail": "Storage not specified; skipping evaluation.",
        }

    result = check_storage(user_storage_gb, game_required_gb)
    if result["status"] == "PASS":
        return {
            "status": "PASS",
            "label": "Enough",
            "sub_score": 100.0,
            "detail": result["message"],
        }
    else:
        return {
            "status": "FAIL",
            "label": f"❌ Need {result['missing_gb']}GB More",
            "sub_score": 0.0,  # binary — can't install = 0
            "detail": result["message"],
        }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — COMPATIBILITY SCORE & PERFORMANCE ESTIMATE
# ─────────────────────────────────────────────────────────────────────────────

def _estimate_settings_and_fps(gpu_eval: dict, cpu_eval: dict,
                                ram_eval: dict) -> tuple[str, int]:
    """
    Estimate expected graphics settings and FPS based on component evaluations.
    Returns (settings_label, estimated_fps).
    """
    # Compute an aggregate performance score (storage excluded — not a perf metric)
    perf_score = (
        gpu_eval["sub_score"] * 0.45 +
        cpu_eval["sub_score"] * 0.30 +
        ram_eval["sub_score"] * 0.25
    )

    if perf_score >= 95:
        return "Ultra", 120
    elif perf_score >= 85:
        return "High", 90
    elif perf_score >= 70:
        return "High", 70
    elif perf_score >= 55:
        return "Medium", 55
    elif perf_score >= 40:
        return "Low", 40
    elif perf_score >= 25:
        return "Low", 30
    else:
        return "Very Low", 20


def compute_compatibility(gpu_eval: dict, cpu_eval: dict,
                          ram_eval: dict, storage_eval: dict) -> dict:
    """
    Compute overall compatibility percentage and performance estimates.
    """
    # Weighted compatibility score
    compat_score = (
        gpu_eval["sub_score"] * WEIGHT_GPU +
        cpu_eval["sub_score"] * WEIGHT_CPU +
        ram_eval["sub_score"] * WEIGHT_RAM +
        storage_eval["sub_score"] * WEIGHT_STORAGE
    )
    compat_pct = int(round(min(compat_score, 100)))

    # Collect reduction reasons
    reasons = []
    if gpu_eval["status"] != "PASS":
        reasons.append(f"GPU: {gpu_eval['label']} — {gpu_eval['detail']}")
    if cpu_eval["status"] != "PASS":
        reasons.append(f"CPU: {cpu_eval['label']} — {cpu_eval['detail']}")
    if ram_eval["status"] == "FAIL":
        reasons.append("System RAM is below the game's minimum requirement.")
    if storage_eval["status"] == "FAIL":
        reasons.append("Insufficient free storage to install the game.")

    # Estimate settings/FPS
    settings, fps = _estimate_settings_and_fps(gpu_eval, cpu_eval, ram_eval)

    return {
        "compatibility_pct": compat_pct,
        "estimated_fps": fps,
        "expected_settings": settings,
        "reduction_reasons": reasons,
    }


# ─────────────────────────────────────────────────────────────────────────────
# FULL GAME EVALUATION
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_game(game_row: dict,
                  user_gpu_tier: int,
                  user_ram_gb: int,
                  user_cpu_name: Optional[str] = None,
                  user_storage_gb: Optional[float] = None,
                  user_gpu_score: Optional[int] = None,
                  user_cpu_score: Optional[int] = None,
                  user_cpu_tier: Optional[int] = None) -> dict:
    """
    Run the full 4-step compatibility evaluation for a single game.

    Parameters
    ----------
    game_row : dict
        A row from games_dataset.csv (or equivalent dict) with keys:
        Title, Min_GPU_Tier, Min_CPU_Tier, Rec_GPU_Tier, Rec_CPU_Tier,
        Min_RAM_GB, Required_Storage_GB, etc.
    user_gpu_tier : int
        User's GPU tier (1-5).
    user_ram_gb : int
        User's RAM in GB.
    user_cpu_name : str, optional
        User's CPU name (e.g. "Intel Core i7-12700K").
    user_storage_gb : float, optional
        User's free storage in GB.
    user_gpu_score : int, optional
        User's precise GPU benchmark score.
    user_cpu_score : int, optional
        User's precise CPU benchmark score.
    user_cpu_tier : int, optional
        User's resolved CPU tier (1-5).

    Returns
    -------
    dict with full compatibility breakdown.
    """
    # Extract game requirements (with safe defaults)
    game_min_gpu = int(game_row.get("Min_GPU_Tier", 1))
    game_rec_gpu = int(game_row.get("Rec_GPU_Tier", game_min_gpu))
    game_min_cpu = int(game_row.get("Min_CPU_Tier", 1))
    game_rec_cpu = int(game_row.get("Rec_CPU_Tier", game_min_cpu))
    game_min_ram = int(game_row.get("Min_RAM_GB", 2))
    game_storage = float(game_row.get("Required_Storage_GB", 0))

    # Step 1: GPU
    gpu_eval = evaluate_gpu(user_gpu_tier, game_min_gpu, game_rec_gpu, user_gpu_score)

    # Step 2: CPU
    cpu_eval = evaluate_cpu(user_cpu_name, game_min_cpu, game_rec_cpu, user_cpu_score, user_cpu_tier)

    # Step 3: RAM
    ram_eval = evaluate_ram(user_ram_gb, game_min_ram)

    # Step 4: Storage
    storage_eval = evaluate_storage(user_storage_gb, game_storage)

    # Step 5: Compatibility Score
    compat = compute_compatibility(gpu_eval, cpu_eval, ram_eval, storage_eval)

    return {
        "title": str(game_row.get("Title", "")),
        "compatibility_pct": compat["compatibility_pct"],
        "gpu": gpu_eval,
        "cpu": cpu_eval,
        "ram": ram_eval,
        "storage": storage_eval,
        "estimated_fps": compat["estimated_fps"],
        "expected_settings": compat["expected_settings"],
        "reduction_reasons": compat["reduction_reasons"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — GAME RANKING
# ─────────────────────────────────────────────────────────────────────────────

def rank_games(evaluated_games: list[dict],
               vibe_scores: Optional[dict[str, float]] = None,
               budget_scores: Optional[dict[str, float]] = None) -> list[dict]:
    """
    Sort evaluated games by:
      1. Compatibility Score (highest first)
      2. Vibe Match (if provided)
      3. Budget Match (if provided)

    Never removes a game — partial compatibility games are still shown.

    Parameters
    ----------
    evaluated_games : list of dicts from evaluate_game()
    vibe_scores : dict mapping title -> vibe_score (0-1)
    budget_scores : dict mapping title -> budget_score (0-1)
    """
    if vibe_scores is None:
        vibe_scores = {}
    if budget_scores is None:
        budget_scores = {}

    for game in evaluated_games:
        title = game["title"]
        game["vibe_score"] = vibe_scores.get(title, 0.0)
        game["budget_score"] = budget_scores.get(title, 0.0)

    # Sort: compatibility first, then vibe, then budget (all descending)
    evaluated_games.sort(
        key=lambda g: (
            g["compatibility_pct"],
            g["vibe_score"],
            g["budget_score"],
        ),
        reverse=True,
    )

    return evaluated_games
