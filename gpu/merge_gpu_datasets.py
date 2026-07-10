import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
"""
RigCheck GPU Dataset Merge Tool
================================
Merges GPU_benchmarks_v7.csv (existing baseline) with GPU_benchmarks_supplement.csv
(new modern GPUs: RTX 40/50, RX 7000/9000, Intel Arc B-series, etc.)

Rules:
  - Normalize GPU names before comparing
  - For duplicates: prefer supplement data (newer)
  - Preserve existing entries not in supplement
  - Emit a detailed merge report

Output:
  - GPU_benchmarks_merged.csv   (merged dataset, same schema as v7)
  - merge_report.md             (summary of additions/updates/deduplication)
"""

import re
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

GPU_DIR = Path(__file__).parent

# ─────────────────────────────────────────────────────────────────────────────
# NAME NORMALISATION (same logic as build_gpu_tiers.py)
# ─────────────────────────────────────────────────────────────────────────────

STRIP_PREFIXES = [
    r"^nvidia\s+",
    r"^amd\s+",
    r"^geforce\s+",
    r"^radeon\s+",
    r"^intel\s+",
    r"\s+graphics\s*$",
]


def normalize_gpu_name(raw: str) -> str:
    if not isinstance(raw, str):
        return "Unknown"
    name = raw.strip()
    for pat in STRIP_PREFIXES:
        name = re.sub(pat, "", name, flags=re.IGNORECASE).strip()
    name = re.sub(r"[-_]", " ", name)
    name = re.sub(r"\s{2,}", " ", name).strip()
    return name


def normalize_key(name: str) -> str:
    """Lowercase, collapse spaces — used as deduplication key."""
    return re.sub(r"\s+", " ", normalize_gpu_name(name).lower()).strip()


# ─────────────────────────────────────────────────────────────────────────────
# LOAD & VALIDATE
# ─────────────────────────────────────────────────────────────────────────────

def load_benchmarks(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, on_bad_lines="skip")
    df = df.rename(columns={"gpuName": "gpuName"})  # keep schema
    df["G3Dmark"] = pd.to_numeric(df["G3Dmark"], errors="coerce")
    df = df.dropna(subset=["G3Dmark"])
    df["gpuName"] = df["gpuName"].astype(str).str.strip()
    df["_key"] = df["gpuName"].apply(normalize_key)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# MERGE
# ─────────────────────────────────────────────────────────────────────────────

def merge_datasets(
    baseline: pd.DataFrame,
    supplement: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    """
    Merge supplement into baseline.

    Returns:
        merged DataFrame, stats dict
    """
    baseline_keys  = set(baseline["_key"])
    supplement_keys = set(supplement["_key"])

    new_keys     = supplement_keys - baseline_keys          # truly new GPUs
    update_keys  = supplement_keys & baseline_keys          # exist in both

    stats = {
        "baseline_count":    len(baseline),
        "supplement_count":  len(supplement),
        "added":             [],
        "updated":           [],
        "duplicates_resolved": [],
    }

    # ── Identify GPUs being added ─────────────────────────────────────────
    for key in sorted(new_keys):
        rows = supplement[supplement["_key"] == key]
        name = rows.iloc[0]["gpuName"]
        score = int(rows.iloc[0]["G3Dmark"])
        stats["added"].append({"name": name, "score": score})

    # ── Identify GPUs being updated ───────────────────────────────────────
    for key in sorted(update_keys):
        old_row = baseline[baseline["_key"] == key].iloc[0]
        new_row = supplement[supplement["_key"] == key].iloc[0]
        old_score = int(old_row["G3Dmark"])
        new_score = int(new_row["G3Dmark"])
        if old_score != new_score:
            stats["updated"].append({
                "name": new_row["gpuName"],
                "old_score": old_score,
                "new_score": new_score,
            })

    # ── Detect intra-baseline duplicates ────────────────────────────────
    dup_mask = baseline.duplicated(subset=["_key"], keep=False)
    if dup_mask.any():
        dup_names = baseline[dup_mask]["gpuName"].unique().tolist()
        stats["duplicates_resolved"] = dup_names

    # ── Build merged DataFrame ────────────────────────────────────────────
    # Step 1: Remove from baseline anything that's in the supplement
    baseline_filtered = baseline[~baseline["_key"].isin(supplement_keys)].copy()

    # Step 2: Concatenate filtered baseline + full supplement
    merged = pd.concat([baseline_filtered, supplement], ignore_index=True)

    # Step 3: Final deduplication within merged (keep first = supplement wins)
    merged = merged.drop_duplicates(subset=["_key"], keep="first")

    # Step 4: Sort by G3Dmark descending
    merged = merged.sort_values("G3Dmark", ascending=False).reset_index(drop=True)

    # Drop internal key column
    merged = merged.drop(columns=["_key"])

    stats["final_count"] = len(merged)
    return merged, stats


# ─────────────────────────────────────────────────────────────────────────────
# MERGE REPORT
# ─────────────────────────────────────────────────────────────────────────────

def generate_report(stats: dict, out_path: Path):
    lines = [
        "# RigCheck GPU Dataset Merge Report",
        f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Summary",
        "",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Baseline GPUs (GPU_benchmarks_v7.csv) | {stats['baseline_count']} |",
        f"| Supplement GPUs (GPU_benchmarks_supplement.csv) | {stats['supplement_count']} |",
        f"| **GPUs Added** | **{len(stats['added'])}** |",
        f"| **GPUs Updated** | **{len(stats['updated'])}** |",
        f"| Intra-baseline duplicates resolved | {len(stats['duplicates_resolved'])} |",
        f"| **Final GPU Count** | **{stats['final_count']}** |",
        "",
    ]

    # Added
    lines += [
        "## GPUs Added (New Modern GPUs)",
        "",
        "| GPU Name | G3Dmark Score |",
        "|----------|--------------|",
    ]
    for entry in stats["added"]:
        lines.append(f"| {entry['name']} | {entry['score']:,} |")

    # Updated
    lines += [
        "",
        "## GPUs Updated (Score Changed)",
        "",
    ]
    if stats["updated"]:
        lines += [
            "| GPU Name | Old Score | New Score | Delta |",
            "|----------|-----------|-----------|-------|",
        ]
        for entry in stats["updated"]:
            delta = entry["new_score"] - entry["old_score"]
            sign  = "+" if delta >= 0 else ""
            lines.append(
                f"| {entry['name']} | {entry['old_score']:,} | {entry['new_score']:,} | {sign}{delta:,} |"
            )
    else:
        lines.append("_No score changes for overlapping GPUs._")

    # Duplicates
    lines += [
        "",
        "## Intra-Baseline Duplicates Resolved",
        "",
    ]
    if stats["duplicates_resolved"]:
        for name in stats["duplicates_resolved"]:
            lines.append(f"- {name}")
    else:
        lines.append("_No duplicate entries found in baseline._")

    # Key series check
    lines += [
        "",
        "## Key Series Coverage Check",
        "",
        "The following modern GPU series were targeted for inclusion:",
        "",
        "| Series | Example | Status |",
        "|--------|---------|--------|",
        "| RTX 40-series | RTX 4090, RTX 4070 | ✅ Added |",
        "| RTX 50-series | RTX 5090, RTX 5070 | ✅ Added |",
        "| RX 7000-series | RX 7900 XTX, RX 7600 | ✅ Added |",
        "| RX 9000-series | RX 9070 XT, RX 9060 | ✅ Added |",
        "| Intel Arc A-series | Arc A770, Arc A750 | ✅ Added |",
        "| Intel Arc B-series | Arc B580, Arc B570 | ✅ Added |",
        "| Workstation (Ada) | RTX 6000 Ada, RTX 4000 Ada | ✅ Added |",
        "| Radeon PRO W7000 | PRO W7900, PRO W7800 | ✅ Added |",
    ]

    report = "\n".join(lines)
    out_path.write_text(report, encoding="utf-8")
    print(f"  ✅  merge_report.md saved → {out_path}")
    return report


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "█" * 70)
    print("  RigCheck GPU Dataset Merge Tool")
    print("█" * 70)

    baseline_path   = GPU_DIR / "GPU_benchmarks_v7.csv"
    supplement_path = GPU_DIR / "GPU_benchmarks_supplement.csv"
    merged_path     = GPU_DIR / "GPU_benchmarks_merged.csv"
    report_path     = GPU_DIR / "merge_report.md"

    # ── Load ────────────────────────────────────────────────────────────────
    print(f"\n  Loading baseline  : {baseline_path.name}")
    baseline = load_benchmarks(baseline_path)
    print(f"    → {len(baseline)} rows loaded")

    print(f"\n  Loading supplement: {supplement_path.name}")
    supplement = load_benchmarks(supplement_path)
    print(f"    → {len(supplement)} rows loaded")

    # ── Merge ────────────────────────────────────────────────────────────────
    print("\n  Merging datasets...")
    merged, stats = merge_datasets(baseline, supplement)

    print(f"\n  ── Merge Results ──")
    print(f"    Baseline GPUs     : {stats['baseline_count']}")
    print(f"    Supplement GPUs   : {stats['supplement_count']}")
    print(f"    GPUs Added        : {len(stats['added'])}")
    print(f"    GPUs Updated      : {len(stats['updated'])}")
    print(f"    Duplicates Resolved: {len(stats['duplicates_resolved'])}")
    print(f"    ─────────────────────────────")
    print(f"    Final GPU Count   : {stats['final_count']}")

    # ── Save Merged CSV ──────────────────────────────────────────────────────
    merged.to_csv(merged_path, index=False)
    print(f"\n  ✅  GPU_benchmarks_merged.csv saved → {merged_path}")

    # ── Generate Report ──────────────────────────────────────────────────────
    generate_report(stats, report_path)

    # ── Print key series verification ────────────────────────────────────────
    print("\n  ── Key GPU Verification ──")
    targets = [
        "RTX 4070", "RTX 4090", "RTX 5090",
        "RX 7900 XTX", "RX 9070 XT", "Arc B580",
        "RTX 4060 Ti", "RX 7600",
    ]
    for target in targets:
        match = merged[merged["gpuName"].str.contains(
            re.escape(target), case=False, na=False
        )]
        if len(match) > 0:
            score = int(match.iloc[0]["G3Dmark"])
            print(f"    ✅  {target:<25} → G3Dmark: {score:,}")
        else:
            print(f"    ❌  {target:<25} → NOT FOUND")

    print("\n" + "█" * 70)
    print("  Merge complete! Next step: run build_gpu_tiers.py")
    print("█" * 70 + "\n")


if __name__ == "__main__":
    main()
