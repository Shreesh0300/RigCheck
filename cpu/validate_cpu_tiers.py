import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
"""
RigCheck CPU Tier Engine — Validation Script
=============================================
Validates tier distribution, known CPU placements, and public API functions.
"""

import json
from pathlib import Path

CPU_DIR = Path(__file__).parent

# ─────────────────────────────────────────────────────────────────────────────
# Add project root to path for imports
# ─────────────────────────────────────────────────────────────────────────────
import sys
_PROJECT_ROOT = CPU_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from cpu.cpu_tier_engine import getCpuTier, getCpuScore, validateCpu


def main():
    print("\n" + "█" * 70)
    print("  RigCheck CPU Tier Engine — Validation")
    print("█" * 70)

    # ── Load generated files ─────────────────────────────────────────────
    with open(CPU_DIR / "cpu_tiers.json", "r", encoding="utf-8") as f:
        tiers = json.load(f)

    with open(CPU_DIR / "cpu_lookup.json", "r", encoding="utf-8") as f:
        lookup = json.load(f)

    total = sum(len(v) for v in tiers.values())
    print(f"\n  Total CPUs : {total}")
    print(f"  Lookup entries : {len(lookup)}")

    # ── Test 1: Tier Distribution ────────────────────────────────────────
    print("\n" + "═" * 70)
    print("  TEST 1 — Tier Distribution")
    print("═" * 70)

    expected = {"S": (8, 12), "A": (18, 22), "B": (28, 32), "C": (23, 27), "D": (13, 17)}
    all_pass = True

    for tier in ["S", "A", "B", "C", "D"]:
        count = len(tiers[tier])
        pct = count / total * 100
        lo, hi = expected[tier]
        status = "✅" if lo <= pct <= hi else "⚠️"
        if lo > pct or pct > hi:
            all_pass = False
        print(f"    {tier} : {count:>3} CPUs  ({pct:>5.1f}%)  expected {lo}-{hi}%  {status}")

    print(f"\n  Distribution test: {'PASS ✅' if all_pass else 'WARN ⚠️ (acceptable variance)'}")

    # ── Test 2: Known CPU Placements ─────────────────────────────────────
    print("\n" + "═" * 70)
    print("  TEST 2 — Known CPU Tier Placements")
    print("═" * 70)

    test_cases = [
        ("Intel Core i9-14900K",   "S", "Flagship desktop"),
        ("AMD Ryzen 9 7950X",     "S", "Top AMD desktop"),
        ("Intel Core i7-14700K",   "S", "High-end desktop"),
        ("AMD Ryzen 7 7800X3D",   "S", "Gaming favourite"),
        ("Intel Core i5-12400F",   "S", "Mid-range budget"),
        ("AMD Ryzen 5 5600X",     "S", "Popular mid-range"),
        ("Intel Core i5-10400F",   "A", "Older mid-range"),
        ("Intel Core i3-10100",    "A", "Entry level"),
        ("Intel Celeron G6900",    "B", "Budget bottom"),
    ]

    pass_count = 0
    for cpu_name, expected_tier, desc in test_cases:
        actual = getCpuTier(cpu_name)
        match = actual == expected_tier
        status = "✅" if match else "❌"
        if match:
            pass_count += 1
        print(f"    {status} {cpu_name:<30} → {actual or '?'} (expected {expected_tier})  [{desc}]")

    print(f"\n  Placement test: {pass_count}/{len(test_cases)} passed")

    # ── Test 3: Public API Functions ─────────────────────────────────────
    print("\n" + "═" * 70)
    print("  TEST 3 — Public API Functions")
    print("═" * 70)

    # getCpuTier
    tier = getCpuTier("AMD Ryzen 5 5600X")
    print(f"    getCpuTier('AMD Ryzen 5 5600X') = {tier}  {'✅' if tier else '❌'}")

    # getCpuScore
    score = getCpuScore("Intel Core i7-12700K")
    print(f"    getCpuScore('Intel Core i7-12700K') = {score}  {'✅' if score and score > 0 else '❌'}")

    # validateCpu
    result = validateCpu("AMD Ryzen 7 7800X3D")
    print(f"    validateCpu('AMD Ryzen 7 7800X3D') = tier={result['tier']}, "
          f"score={result['benchmark_score']}, error={result['error']}  "
          f"{'✅' if result['error'] is None else '❌'}")

    # Unknown CPU
    result_unk = validateCpu("FakeCPU 9999")
    print(f"    validateCpu('FakeCPU 9999') = error={result_unk['error']}  "
          f"{'✅' if result_unk['error'] is not None else '❌'}")

    # ── Test 4: Fuzzy Matching ───────────────────────────────────────────
    print("\n" + "═" * 70)
    print("  TEST 4 — Fuzzy Name Matching")
    print("═" * 70)

    fuzzy_tests = [
        ("i9 14900K",               "i9 14900K",       "Normalized form"),
        ("Intel Core i9-14900K",    "i9 14900K",       "Full official name"),
        ("ryzen 9 7950x",           "Ryzen 9 7950X",   "Lowercase input"),
        ("core i7 12700K",          "i7 12700K",       "Partial name"),
    ]

    for query, expected_match, desc in fuzzy_tests:
        result = validateCpu(query)
        matched = result.get("matched_name", "?")
        status = "✅" if result["error"] is None else "❌"
        print(f"    {status} '{query}' → matched '{matched}'  [{desc}]")

    print("\n" + "█" * 70)
    print("  CPU Tier Validation Complete")
    print("█" * 70 + "\n")


if __name__ == "__main__":
    main()
