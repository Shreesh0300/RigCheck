import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
"""
RigCheck CPU Integration Validation Script
===========================================
Tests the new cpu_name validation flow, alias lookup, and validation error handling.
"""

from pathlib import Path

# Add project root to path for imports
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from model.rigcheck_engine import recommend_game


def main():
    print("\n" + "█" * 70)
    print("  RigCheck CPU Name Integration — Validation")
    print("█" * 70)

    # ── Test 1: Validate Required CPUs ──────────────────────────────────
    print("\n" + "═" * 70)
    print("  TEST 1 — Canonical CPU Models")
    print("═" * 70)

    test_cpus = [
        "Intel Core i9-14900K",
        "AMD Ryzen 7 7800X3D",
        "Intel Core i5-12400F",
        "AMD Ryzen 5 5600X",
    ]

    for cpu in test_cpus:
        try:
            result = recommend_game(
                user_input="open world adventure",
                budget=4000,
                gpu_name="RTX 4050",
                ram=16,
                cpu_name=cpu,
                storage_gb=200
            )
            compat = result["compatibility"]
            print(f"    ✅ {cpu:<25} → resolved successfully. Compat score: {compat['compatibility_pct']}% | CPU status: {compat['cpu']['label']} (score: {compat['cpu']['sub_score']})")
        except Exception as e:
            print(f"    ❌ {cpu:<25} → failed: {e}")

    # ── Test 2: Alias Resolution ────────────────────────────────────────
    print("\n" + "═" * 70)
    print("  TEST 2 — Alias Variations")
    print("═" * 70)

    aliases = [
        "i7-12700K",
        "Intel i7-12700K",
        "Intel Core i7-12700K",
        "Core i7-12700K",
        "i7 12700K"
    ]

    for alias in aliases:
        try:
            result = recommend_game(
                user_input="open world adventure",
                budget=4000,
                gpu_name="RTX 4050",
                ram=16,
                cpu_name=alias,
                storage_gb=200
            )
            compat = result["compatibility"]
            print(f"    ✅ '{alias}' → resolved. Match CPU: '{compat['cpu']['detail']}'")
        except Exception as e:
            print(f"    ❌ '{alias}' → failed: {e}")

    # ── Test 3: Unrecognized CPU model ─────────────────────────────────
    print("\n" + "═" * 70)
    print("  TEST 3 — Unrecognized CPU Model Handling")
    print("═" * 70)

    try:
        recommend_game(
            user_input="open world adventure",
            budget=4000,
            gpu_name="RTX 4050",
            ram=16,
            cpu_name="FakeCPU 9999",
            storage_gb=200
        )
        print("    ❌ Failed to catch unrecognized CPU model")
    except ValueError as e:
        expected = "CPU model not recognized. Please check the spelling and try again."
        if str(e) == expected:
            print(f"    ✅ Unrecognized CPU raised ValueError as expected: '{e}'")
        else:
            print(f"    ⚠️ Raised unexpected ValueError: '{e}' (expected: '{expected}')")

    print("\n" + "█" * 70)
    print("  Validation Complete")
    print("█" * 70 + "\n")


if __name__ == "__main__":
    main()
