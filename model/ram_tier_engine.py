"""
RigCheck RAM Tier Engine
========================
Rule-based RAM scoring and tier assignment.
Completely independent — no datasets, no external dependencies.

Functions:
    parse_ram(raw_input)          -> RAMSpec | None
    calculate_ram_score(spec)     -> float (0-100)
    get_ram_tier(score)           -> str  (S/A/B/C/D)
    evaluate_ram(raw_input)       -> dict

Future integration hook:
    The returned dict contains a normalised "score" (0-100)
    that can be combined with gpu_score, cpu_score, storage_score
    into an overall rig score without any changes to this module.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RAMSpec:
    capacity_gb: int
    generation: str          # "DDR5" | "DDR4" | "DDR3" | "DDR2"
    speed_mhz: Optional[int] # None if not supplied
    ram_type: str = ""       # e.g. "LPDDR5", "DDR5"


@dataclass
class RAMResult:
    capacity_gb: int
    generation: str
    speed_mhz: Optional[int]
    capacity_score: float
    generation_score: float
    speed_score: float
    score: float              # weighted final 0-100
    tier: str                 # S / A / B / C / D
    ram_type: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — PARSER
# ─────────────────────────────────────────────────────────────────────────────

# Regex patterns (order-independent, case-insensitive)
_RE_CAPACITY = re.compile(r"(?<!\w)(-?\d+)\s*gb", re.IGNORECASE)
_RE_GEN      = re.compile(r"\b(lpddr[45]x?|ddr[2-5])\b", re.IGNORECASE)
_RE_SPEED_EXPLICIT   = re.compile(r"\b(\d{3,5})\s*(?:mhz|mt/?s|mts)\b", re.IGNORECASE)
_RE_SPEED_STANDALONE = re.compile(r"(?<!\w)(\d{3,5})(?!\w)")


def parse_ram(raw_input: str) -> Optional[RAMSpec]:
    """
    Parse a free-form RAM string into a RAMSpec.

    Accepts any order, case-insensitive, with or without spaces/MHz:
        "32GB DDR5 6000"
        "ddr4 16 gb 3200mhz"
        "64GB LPDDR5X 6400"
        "DDR5 32GB 5600MHz"

    Returns None if capacity or generation cannot be parsed.
    """
    text = raw_input.strip()

    # Capacity
    cap_match = _RE_CAPACITY.search(text)
    if not cap_match:
        return None
    capacity = int(cap_match.group(1))
    if capacity <= 0 or capacity > 1024:
        return None

    # Generation & Type
    gen_match = _RE_GEN.search(text)
    if not gen_match:
        return None
    raw_type = gen_match.group(1).upper()
    if "LPDDR5" in raw_type:
        generation = "DDR5"
    elif "LPDDR4" in raw_type:
        generation = "DDR4"
    else:
        generation = raw_type

    # Speed — contextual parsing
    speed: Optional[int] = None
    # 1. Search explicit units first
    for m in _RE_SPEED_EXPLICIT.finditer(text):
        candidate = int(m.group(1))
        if 200 <= candidate <= 15000 and candidate != capacity:
            speed = candidate
            break

    # 2. Search standalone numbers with contextual frequency step validation
    if speed is None:
        for m in _RE_SPEED_STANDALONE.finditer(text):
            candidate = int(m.group(1))
            if 200 <= candidate <= 15000 and candidate != capacity:
                if candidate % 100 in (0, 33, 66, 67):
                    speed = candidate
                    break

    return RAMSpec(
        capacity_gb=capacity,
        generation=generation,
        speed_mhz=speed,
        ram_type=raw_type,
    )


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — CAPACITY SCORE (lookup table)
# ─────────────────────────────────────────────────────────────────────────────

# Breakpoints: (minimum_gb, score)
_CAPACITY_TABLE: list[tuple[int, float]] = [
    (64, 100),
    (48,  95),
    (32,  90),
    (24,  80),
    (16,  70),
    (12,  55),
    ( 8,  40),
    ( 4,  20),
    ( 0,  10),   # anything < 4GB
]


def _capacity_score(capacity_gb: int) -> float:
    for threshold, score in _CAPACITY_TABLE:
        if capacity_gb >= threshold:
            return float(score)
    return 10.0


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — GENERATION SCORE
# ─────────────────────────────────────────────────────────────────────────────

_GEN_SCORES: dict[str, float] = {
    "DDR5": 100.0,
    "DDR4":  80.0,
    "DDR3":  50.0,
    "DDR2":  20.0,
    "DDR":   10.0,   # very old / generic
}


def _generation_score(generation: str) -> float:
    return _GEN_SCORES.get(generation.upper(), 10.0)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — SPEED SCORE (per-generation lookup with linear interpolation)
# ─────────────────────────────────────────────────────────────────────────────

# Each generation maps speed (MHz) -> score.
# Speeds between breakpoints are linearly interpolated.
# Speeds above the max cap at 100; below the min floor at the lowest score.

_SPEED_TABLES: dict[str, list[tuple[int, float]]] = {
    "DDR5": [
        (8000, 100),
        (7200,  95),
        (6400,  90),
        (6000,  85),
        (5600,  80),
        (5200,  75),
        (4800,  70),
        (4400,  65),
        (4000,  58),
        (3600,  50),
    ],
    "DDR4": [
        (3600, 100),
        (3200,  90),
        (3000,  85),
        (2666,  70),
        (2400,  60),
        (2133,  50),
        (1866,  40),
        (1600,  30),
    ],
    "DDR3": [
        (2133, 100),
        (1866,  90),
        (1600,  75),
        (1333,  60),
        (1066,  45),
        ( 800,  30),
    ],
    "DDR2": [
        (1066, 100),
        ( 800,  80),
        ( 667,  60),
        ( 533,  40),
        ( 400,  25),
    ],
}

# Default speed per generation when speed is not supplied
_DEFAULT_SPEED: dict[str, int] = {
    "DDR5": 4800,
    "DDR4": 2133,
    "DDR3": 1333,
    "DDR2":  667,
    "DDR":   333,
}


def _lerp(x: float, x0: float, x1: float, y0: float, y1: float) -> float:
    """Linear interpolation."""
    if x1 == x0:
        return y0
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def _speed_score(generation: str, speed_mhz: Optional[int]) -> float:
    gen = generation.upper()
    table = _SPEED_TABLES.get(gen)

    if table is None:
        # Unknown generation — return neutral score
        return 50.0

    # Use default speed if not provided
    if speed_mhz is None:
        speed_mhz = _DEFAULT_SPEED.get(gen, table[-1][0])

    # Table is sorted descending by speed
    # Above max → cap at 100
    if speed_mhz >= table[0][0]:
        return 100.0
    # Below min → floor at lowest defined score
    if speed_mhz <= table[-1][0]:
        return float(table[-1][1])

    # Find bracketing interval and interpolate
    for i in range(len(table) - 1):
        hi_speed, hi_score = table[i]
        lo_speed, lo_score = table[i + 1]
        if lo_speed <= speed_mhz <= hi_speed:
            return round(_lerp(speed_mhz, lo_speed, hi_speed, lo_score, hi_score), 2)

    return float(table[-1][1])


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — WEIGHTED FINAL SCORE
# ─────────────────────────────────────────────────────────────────────────────

# Weights must sum to 1.0
WEIGHT_CAPACITY   = 0.50
WEIGHT_GENERATION = 0.20
WEIGHT_SPEED      = 0.30


def calculate_ram_score(spec: RAMSpec) -> tuple[float, float, float, float]:
    """
    Returns (capacity_score, generation_score, speed_score, final_score).
    All values are 0-100.
    """
    cap_s  = _capacity_score(spec.capacity_gb)
    gen_s  = _generation_score(spec.generation)
    spd_s  = _speed_score(spec.generation, spec.speed_mhz)

    final = (
        cap_s  * WEIGHT_CAPACITY   +
        gen_s  * WEIGHT_GENERATION +
        spd_s  * WEIGHT_SPEED
    )
    return cap_s, gen_s, spd_s, round(final, 2)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — TIER ASSIGNMENT
# ─────────────────────────────────────────────────────────────────────────────

_TIER_THRESHOLDS: list[tuple[float, str]] = [
    (95, "S"),
    (85, "A"),
    (70, "B"),
    (55, "C"),
    ( 0, "D"),
]


def get_ram_tier(score: float) -> str:
    """Return S/A/B/C/D tier for a given 0-100 score."""
    for threshold, tier in _TIER_THRESHOLDS:
        if score >= threshold:
            return tier
    return "D"


# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 — MAIN PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_ram(raw_input: str) -> dict:
    """
    Full pipeline: parse -> score -> tier -> structured output.
    """
    text = raw_input.strip()

    # Pre-check invalid capacity for exact error message required by Task 1
    cap_match = _RE_CAPACITY.search(text)
    if cap_match:
        c_val = int(cap_match.group(1))
        if c_val <= 0 or c_val > 1024:
            gen_match = _RE_GEN.search(text)
            raw_type = gen_match.group(1).upper() if gen_match else None
            gen = None
            if raw_type:
                gen = "DDR5" if "LPDDR5" in raw_type else ("DDR4" if "LPDDR4" in raw_type else raw_type)
            return {
                "capacity":          c_val,
                "generation":        gen,
                "type":              raw_type,
                "speed":             None,
                "capacity_score":    None,
                "generation_score":  None,
                "speed_score":       None,
                "score":             None,
                "tier":              None,
                "error":             "Invalid RAM Capacity"
            }

    spec = parse_ram(raw_input)

    if spec is None:
        return {
            "capacity":          None,
            "generation":        None,
            "type":              None,
            "speed":             None,
            "capacity_score":    None,
            "generation_score":  None,
            "speed_score":       None,
            "score":             None,
            "tier":              None,
            "error":             f"Could not parse RAM spec from: '{raw_input}'"
        }

    cap_s, gen_s, spd_s, final = calculate_ram_score(spec)
    tier = get_ram_tier(final)

    return {
        "capacity":          spec.capacity_gb,
        "generation":        spec.generation,
        "type":              spec.ram_type,
        "speed":             spec.speed_mhz,
        "capacity_score":    cap_s,
        "generation_score":  gen_s,
        "speed_score":       spd_s,
        "score":             final,
        "tier":              tier,
        "error":             None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 8 — VALIDATION (run as __main__)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_cases = [
        # Required validation cases
        "64GB DDR5 6400",
        "32GB DDR5 6000",
        "16GB DDR4 3200",
        "8GB DDR4 2400",
        "4GB DDR3 1600",
        # Flexible input formats
        "32 GB DDR5 6000MHz",
        "DDR5 32GB 5600",
        "16 gb ddr4 3200mhz",
        "64GB DDR5",             # no speed
        "8GB DDR4",              # no speed
        "128GB DDR5 8000",       # extreme high end
        "2GB DDR3 1066",         # very low end
        # LPDDR & Contextual fixes
        "32GB LPDDR5X 6400",
        "16GB LPDDR4X 4266",
        "32GB DDR4 2024",        # contextual speed test (2024 ignored)
        "0GB DDR5",              # invalid capacity
        "-8GB DDR5",             # negative capacity
        # Edge cases
        "32gb ddr5 7200",        # lowercase
        "DDR4 16GB",             # reversed, no speed
    ]

    header = f"{'Input':<30} {'Cap':>4} {'Gen':<5} {'Type':<8} {'Spd':>5}  {'Cap%':>5} {'Gen%':>5} {'Spd%':>5}  {'Score':>6}  {'Tier'}"
    print(header)
    print("-" * len(header))

    for tc in test_cases:
        r = evaluate_ram(tc)
        if r["error"]:
            print(f"{tc:<30}  ERROR: {r['error']}")
        else:
            print(
                f"{tc:<30}"
                f" {r['capacity']:>4}GB"
                f" {r['generation']:<5}"
                f" {str(r['type']):<8}"
                f" {str(r['speed'] or 'N/A'):>5}"
                f"  {r['capacity_score']:>5.1f}"
                f" {r['generation_score']:>5.1f}"
                f" {r['speed_score']:>5.1f}"
                f"  {r['score']:>6.2f}"
                f"  [{r['tier']}]"
            )
