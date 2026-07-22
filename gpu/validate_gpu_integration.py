import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
"""
RigCheck GPU Integration Validation Script
===========================================
Tests the new gpu_name request flow, fuzzy lookup, validation error handling,
and legacy backward compatibility.
"""

from pathlib import Path

# Add project root to path for imports
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from model.rigcheck_engine import recommend_game


def main():
    print("\n" + "█" * 70)
    print("  RigCheck GPU Name Integration — Validation")
    print("█" * 70)

    # ── Test 1: Validate Required GPUs ──────────────────────────────────
    print("\n" + "═" * 70)
    print("  TEST 1 — Required GPU Models")
    print("═" * 70)

    test_gpus = [
        "RTX 4050",
        "RTX 4070",
        "RTX 5090",
        "RX 9070 XT",
        "RX 7700 XT",
        "Arc B580"
    ]

    for gpu in test_gpus:
        try:
            result = recommend_game(
                user_input="open world adventure",
                budget=4000,
                gpu_name=gpu,
                ram=16,
                cpu_name="Intel Core i5-12400F",
                storage_gb=200
            )
            compat = result["compatibility"]
            print(f"    ✅ {gpu:<15} → resolved successfully. Compat score: {compat['compatibility_pct']}% | GPU status: {compat['gpu']['label']} (score: {compat['gpu']['sub_score']})")
        except Exception as e:
            print(f"    ❌ {gpu:<15} → failed: {e}")

    # ── Test 2: Unrecognized GPU model ─────────────────────────────────
    print("\n" + "═" * 70)
    print("  TEST 2 — Unrecognized GPU Model Handling")
    print("═" * 70)

    try:
        recommend_game(
            user_input="open world adventure",
            budget=4000,
            gpu_name="Geforce RTX 9999 SUPER DUPER",
            ram=16
        )
        print("    ❌ Failed to catch unrecognized GPU model")
    except ValueError as e:
        expected = "GPU model not recognized. Please check the spelling and try again."
        if str(e) == expected:
            print(f"    ✅ Unrecognized GPU raised ValueError as expected: '{e}'")
        else:
            print(f"    ⚠️ Raised unexpected ValueError: '{e}' (expected: '{expected}')")

    # ── Test 3: Backward Compatibility ──────────────────────────────────
    print("\n" + "═" * 70)
    print("  TEST 3 — Backward Compatibility (Legacy Tiers)")
    print("═" * 70)

    # Passing integer tier
    try:
        result_int = recommend_game(
            user_input="open world adventure",
            budget=4000,
            gpu_name=3,  # integer tier
            ram=16
        )
        print(f"    ✅ Passed integer tier (3) → resolved. Winner: {result_int['recommended_game']}")
    except Exception as e:
        print(f"    ❌ Failed on integer tier (3): {e}")

    # Passing string digit tier
    try:
        result_str = recommend_game(
            user_input="open world adventure",
            budget=4000,
            gpu_name="4",  # string digit tier
            ram=16
        )
        print(f"    ✅ Passed string digit tier ('4') → resolved. Winner: {result_str['recommended_game']}")
    except Exception as e:
        print(f"    ❌ Failed on string digit tier ('4'): {e}")

    print("\n" + "█" * 70)
    print("  Validation Complete")
    print("█" * 70 + "\n")


if __name__ == "__main__":
    main()
