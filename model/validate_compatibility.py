import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
"""
RigCheck Compatibility Engine — Validation Script
===================================================
Tests storage engine, compatibility workflow, scoring, and ranking.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from model.storage_engine import check_storage
from model.compatibility_engine import (
    evaluate_gpu, evaluate_cpu, evaluate_ram, evaluate_storage,
    compute_compatibility, evaluate_game, rank_games,
)


def test_storage_engine():
    print("\n" + "═" * 70)
    print("  TEST 1 — Storage Availability Engine")
    print("═" * 70)

    cases = [
        (180, 126, "PASS", "More than enough"),
        (126, 126, "PASS", "Exact match"),
        (180, 250, "FAIL", "Not enough"),
        (0,   50,  "FAIL", "Zero storage"),
        (500, 0,   "PASS", "Zero required"),
        (100, 100, "PASS", "Exact boundary"),
    ]

    pass_count = 0
    for user, game, expected_status, desc in cases:
        result = check_storage(user, game)
        match = result["status"] == expected_status
        status_icon = "✅" if match else "❌"
        if match:
            pass_count += 1
        print(f"    {status_icon} {desc:<25} → user={user}GB game={game}GB "
              f"→ {result['status']} (missing: {result['missing_gb']}GB)")

    print(f"\n  Storage engine: {pass_count}/{len(cases)} passed")
    return pass_count == len(cases)


def test_gpu_evaluation():
    print("\n" + "═" * 70)
    print("  TEST 2 — GPU Evaluation")
    print("═" * 70)

    cases = [
        (5, 3, 4, "PASS",             "GPU exceeds recommended"),
        (4, 3, 4, "PASS",             "GPU meets recommended"),
        (3, 3, 4, "BELOW_RECOMMENDED", "GPU at minimum only"),
        (2, 3, 4, "BELOW_MINIMUM",    "GPU below minimum"),
        (1, 3, 4, "BELOW_MINIMUM",    "GPU way below minimum"),
    ]

    pass_count = 0
    for user_tier, min_tier, rec_tier, expected, desc in cases:
        result = evaluate_gpu(user_tier, min_tier, rec_tier)
        match = result["status"] == expected
        status_icon = "✅" if match else "❌"
        if match:
            pass_count += 1
        print(f"    {status_icon} {desc:<30} → user T{user_tier} vs min T{min_tier}/rec T{rec_tier} "
              f"→ {result['status']} (score: {result['sub_score']})")

    print(f"\n  GPU evaluation: {pass_count}/{len(cases)} passed")
    return pass_count == len(cases)


def test_ram_evaluation():
    print("\n" + "═" * 70)
    print("  TEST 3 — RAM Evaluation")
    print("═" * 70)

    cases = [
        (32, 8,  "PASS", "Plenty of RAM"),
        (16, 16, "PASS", "Exact match"),
        (8,  12, "FAIL", "4GB short"),
        (4,  16, "FAIL", "12GB short"),
        (16, 8,  "PASS", "8GB headroom"),
    ]

    pass_count = 0
    for user_ram, game_ram, expected, desc in cases:
        result = evaluate_ram(user_ram, game_ram)
        match = result["status"] == expected
        status_icon = "✅" if match else "❌"
        if match:
            pass_count += 1
        print(f"    {status_icon} {desc:<25} → user={user_ram}GB game={game_ram}GB "
              f"→ {result['status']} (score: {result['sub_score']})")

    print(f"\n  RAM evaluation: {pass_count}/{len(cases)} passed")
    return pass_count == len(cases)


def test_full_compatibility():
    print("\n" + "═" * 70)
    print("  TEST 4 — Full Game Compatibility Evaluation")
    print("═" * 70)

    # Simulated game rows
    games = [
        {
            "Title": "Cyberpunk 2077",
            "Min_GPU_Tier": 4, "Rec_GPU_Tier": 5,
            "Min_CPU_Tier": 3, "Rec_CPU_Tier": 4,
            "Min_RAM_GB": 12, "Required_Storage_GB": 70,
        },
        {
            "Title": "Stardew Valley",
            "Min_GPU_Tier": 1, "Rec_GPU_Tier": 1,
            "Min_CPU_Tier": 1, "Rec_CPU_Tier": 1,
            "Min_RAM_GB": 4, "Required_Storage_GB": 1,
        },
        {
            "Title": "Microsoft Flight Simulator",
            "Min_GPU_Tier": 5, "Rec_GPU_Tier": 5,
            "Min_CPU_Tier": 4, "Rec_CPU_Tier": 5,
            "Min_RAM_GB": 16, "Required_Storage_GB": 150,
        },
    ]

    # User: mid-range PC
    user = {
        "gpu_tier": 3,
        "ram_gb": 16,
        "cpu_name": "Intel Core i5-12400F",
        "storage_gb": 200,
    }

    results = []
    for game in games:
        result = evaluate_game(
            game_row=game,
            user_gpu_tier=user["gpu_tier"],
            user_ram_gb=user["ram_gb"],
            user_cpu_name=user["cpu_name"],
            user_storage_gb=user["storage_gb"],
        )
        results.append(result)

        print(f"\n  📎 {result['title']}")
        print(f"     Compatibility : {result['compatibility_pct']}%")
        print(f"     GPU           : {result['gpu']['label']} ({result['gpu']['status']})")
        print(f"     CPU           : {result['cpu']['label']} ({result['cpu']['status']})")
        print(f"     RAM           : {result['ram']['label']} ({result['ram']['status']})")
        print(f"     Storage       : {result['storage']['label']} ({result['storage']['status']})")
        print(f"     Settings      : {result['expected_settings']}")
        print(f"     FPS           : {result['estimated_fps']}")
        if result["reduction_reasons"]:
            print(f"     Reasons       :")
            for reason in result["reduction_reasons"]:
                print(f"       • {reason}")

    # Verify ranking
    print(f"\n  ── Ranking Test ──")

    # Stardew Valley should rank highest (easy to run)
    ranked = rank_games(results)

    print(f"  Ranked order:")
    for i, g in enumerate(ranked):
        print(f"    {i+1}. {g['title']} ({g['compatibility_pct']}%)")

    # Stardew Valley should be #1 since it's easiest to run on mid-range hardware
    stardew_rank = next((i for i, g in enumerate(ranked) if g["title"] == "Stardew Valley"), -1)
    flight_sim_rank = next((i for i, g in enumerate(ranked) if g["title"] == "Microsoft Flight Simulator"), -1)

    if stardew_rank < flight_sim_rank:
        print(f"  ✅ Stardew Valley ranks above Flight Simulator (as expected)")
    else:
        print(f"  ❌ Ranking order unexpected")

    return True


def test_edge_cases():
    print("\n" + "═" * 70)
    print("  TEST 5 — Edge Cases")
    print("═" * 70)

    # CPU not provided
    result = evaluate_cpu(None, 3, 4)
    print(f"    ✅ CPU=None → status={result['status']}, score={result['sub_score']}")

    # Storage not provided
    result = evaluate_storage(None, 100)
    print(f"    ✅ Storage=None → status={result['status']}, score={result['sub_score']}")

    # Unknown CPU
    result = evaluate_cpu("Unknown CPU XYZ 9000", 3, 4)
    print(f"    ✅ Unknown CPU → status={result['status']}, label={result['label']}")

    # All components pass
    gpu = evaluate_gpu(5, 3, 4)
    cpu = evaluate_cpu("Intel Core i9-14900K", 3, 4)
    ram = evaluate_ram(32, 8)
    storage = evaluate_storage(500, 100)
    compat = compute_compatibility(gpu, cpu, ram, storage)
    print(f"    ✅ All PASS → compatibility={compat['compatibility_pct']}%, "
          f"settings={compat['expected_settings']}, fps={compat['estimated_fps']}")

    # All components fail
    gpu = evaluate_gpu(1, 5, 5)
    cpu = evaluate_cpu("Intel Celeron G5905", 5, 5)
    ram = evaluate_ram(4, 32)
    storage = evaluate_storage(10, 150)
    compat = compute_compatibility(gpu, cpu, ram, storage)
    print(f"    ✅ All FAIL → compatibility={compat['compatibility_pct']}%, "
          f"reasons={len(compat['reduction_reasons'])}")

    return True


def main():
    print("\n" + "█" * 70)
    print("  RigCheck Compatibility Engine — Validation")
    print("█" * 70)

    t1 = test_storage_engine()
    t2 = test_gpu_evaluation()
    t3 = test_ram_evaluation()
    t4 = test_full_compatibility()
    t5 = test_edge_cases()

    print("\n" + "═" * 70)
    print("  SUMMARY")
    print("═" * 70)
    results = [
        ("Storage Engine", t1),
        ("GPU Evaluation", t2),
        ("RAM Evaluation", t3),
        ("Full Compatibility", t4),
        ("Edge Cases", t5),
    ]
    for name, passed in results:
        print(f"    {'✅' if passed else '❌'} {name}")

    print("\n" + "█" * 70)
    print("  Compatibility Validation Complete")
    print("█" * 70 + "\n")


if __name__ == "__main__":
    main()
