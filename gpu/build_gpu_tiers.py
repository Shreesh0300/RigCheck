"""
RigCheck GPU Tier Engine
========================
Pipeline: Dataset Audit → Cleaning → Master Dataset → Tier Assignment → Lookup Files

Designed to be reusable for CPU / RAM / Storage tier rankings.
"""

import json
import re
import os
import pandas as pd
import numpy as np
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

GPU_DIR = Path(__file__).parent
OUT_DIR = GPU_DIR  # outputs land in /gpu/

TIER_THRESHOLDS = {          # percentile boundaries (top-down)
    "S": 0.90,               # top 10%
    "A": 0.70,               # 70–90 %
    "B": 0.40,               # 40–70 %
    "C": 0.15,               # 15–40 %
    "D": 0.00,               # bottom 15%
}

# ─────────────────────────────────────────────────────────────────────────────
# TASK 1 — DATASET AUDIT
# ─────────────────────────────────────────────────────────────────────────────

def audit_dataset(filepath: Path, name_col: str) -> dict:
    """Read a CSV and return an audit summary dict."""
    try:
        df = pd.read_csv(filepath, on_bad_lines="skip", low_memory=False)
    except Exception as e:
        return {"error": str(e)}

    rows, cols = df.shape
    missing = df.isnull().sum().to_dict()
    duplicates = int(df.duplicated().sum())
    unique_gpus = int(df[name_col].nunique()) if name_col in df.columns else "N/A"

    return {
        "file": filepath.name,
        "rows": rows,
        "columns": cols,
        "column_names": list(df.columns),
        "missing_values": {k: int(v) for k, v in missing.items() if v > 0},
        "duplicate_rows": duplicates,
        "unique_gpu_count": unique_gpus,
    }


def run_audit():
    files_meta = [
        (GPU_DIR / "All_GPUs.csv",                  "Name"),
        (GPU_DIR / "All_GPUs (1).csv",              "Name"),
        (GPU_DIR / "GPU_benchmarks_v7.csv",         "gpuName"),
        (GPU_DIR / "GPU_scores_graphicsAPIs.csv",   "Device"),
    ]

    print("\n" + "═" * 70)
    print("  TASK 1 — DATASET AUDIT")
    print("═" * 70)

    audits = {}
    for fpath, ncol in files_meta:
        result = audit_dataset(fpath, ncol)
        audits[fpath.name] = result
        print(f"\n📁 {result['file']}")
        print(f"   Rows         : {result.get('rows', '?')}")
        print(f"   Columns      : {result.get('columns', '?')}")
        print(f"   Column names : {result.get('column_names', [])}")
        print(f"   Duplicates   : {result.get('duplicate_rows', '?')}")
        print(f"   Unique GPUs  : {result.get('unique_gpu_count', '?')}")
        mv = result.get("missing_values", {})
        if mv:
            top_missing = dict(list(mv.items())[:5])
            print(f"   Missing vals  : {top_missing} ...")
        else:
            print(f"   Missing vals  : None")

    return audits


# ─────────────────────────────────────────────────────────────────────────────
# TASK 2 — IDENTIFY DATA SOURCES
# ─────────────────────────────────────────────────────────────────────────────

def identify_sources():
    print("\n" + "═" * 70)
    print("  TASK 2 — DATA SOURCE ROLES")
    print("═" * 70)

    roles = {
        "GPU Catalog (names, manufacturer, VRAM, release)": "All_GPUs.csv",
        "Benchmark Data (G3D performance scores)"          : "GPU_benchmarks_v7.csv",
        "Graphics API Scores (CUDA, OpenCL, Vulkan, Metal)": "GPU_scores_graphicsAPIs.csv",
        "Source of Truth for GPU identity"                 : "GPU_benchmarks_v7.csv  (most complete + cleaned names)",
        "Source of Truth for performance ranking"          : "GPU_benchmarks_v7.csv  (G3Dmark — industry standard)",
        "Source of Truth for API capability"               : "GPU_scores_graphicsAPIs.csv",
    }
    for role, source in roles.items():
        print(f"  {role:<55} → {source}")

    return roles


# ─────────────────────────────────────────────────────────────────────────────
# TASK 3 — CLEANING & NORMALISATION
# ─────────────────────────────────────────────────────────────────────────────

MANUFACTURER_MAP = {
    "nvidia": "NVIDIA",
    "geforce": "NVIDIA",
    "rtx": "NVIDIA",
    "gtx": "NVIDIA",
    "quadro": "NVIDIA",
    "tesla": "NVIDIA",
    "titan": "NVIDIA",
    "amd": "AMD",
    "radeon": "AMD",
    "firepro": "AMD",
    "rx ": "AMD",
    "intel": "Intel",
    "iris": "Intel",
    "apple": "Apple",
    "arm": "ARM",
    "qualcomm": "Qualcomm",
}

# Prefixes/strings to strip from GPU names
STRIP_PREFIXES = [
    r"^nvidia\s+",
    r"^amd\s+",
    r"^geforce\s+",
    r"^radeon\s+",
    r"^intel\s+",
    r"\s+graphics\s*$",
]


def infer_manufacturer(name: str) -> str:
    name_lower = name.lower()
    for key, mfr in MANUFACTURER_MAP.items():
        if key in name_lower:
            return mfr
    return "Unknown"


def normalize_gpu_name(raw: str) -> str:
    """
    Attempt to strip vendor-prefix words so:
      'GeForce RTX 4070'  →  'RTX 4070'
      'Radeon RX 6800 XT' →  'RX 6800 XT'
      'NVIDIA TITAN X'    →  'TITAN X'
    """
    if not isinstance(raw, str):
        return "Unknown"
    name = raw.strip()
    for pat in STRIP_PREFIXES:
        name = re.sub(pat, "", name, flags=re.IGNORECASE).strip()
    # normalise hyphens/underscores in model IDs
    name = re.sub(r"[-_]", " ", name)
    name = re.sub(r"\s{2,}", " ", name).strip()
    return name


def parse_vram_mb(raw_memory: str) -> float:
    """Parse strings like '8192 MB', '16 GB' → float GB."""
    if not isinstance(raw_memory, str):
        return float("nan")
    raw_memory = raw_memory.strip()
    m = re.search(r"([\d,]+)\s*(MB|GB)", raw_memory, re.IGNORECASE)
    if not m:
        return float("nan")
    value = float(m.group(1).replace(",", ""))
    unit = m.group(2).upper()
    return round(value / 1024 if unit == "MB" else value, 2)


def parse_release_year(raw: str) -> float:
    if not isinstance(raw, str):
        return float("nan")
    m = re.search(r"(20\d{2}|19\d{2})", raw)
    return float(m.group(1)) if m else float("nan")


def clean_benchmarks() -> pd.DataFrame:
    df = pd.read_csv(GPU_DIR / "GPU_benchmarks_v7.csv", on_bad_lines="skip")
    df = df.rename(columns={"gpuName": "raw_name", "G3Dmark": "benchmark_score"})
    df = df[["raw_name", "benchmark_score", "testDate", "category"]].copy()
    df["benchmark_score"] = pd.to_numeric(df["benchmark_score"], errors="coerce")
    df = df.dropna(subset=["benchmark_score"])
    df["raw_name"] = df["raw_name"].astype(str).str.strip()
    # Drop obvious non-GPU entries
    noise = df["raw_name"].str.contains(
        r"(llvmpipe|display port driver|virtual|TENSOR|MuMu|GRID [A-Z]\d+C\s|GRID [A-Z]\d+-\d+[A-Z]$)",
        case=False, na=False
    )
    df = df[~noise].copy()
    # Normalise
    df["gpu_name"] = df["raw_name"].apply(normalize_gpu_name)
    df["release_year"] = pd.to_numeric(df["testDate"], errors="coerce")
    df["manufacturer"] = df["raw_name"].apply(infer_manufacturer)
    return df


def clean_all_gpus() -> pd.DataFrame:
    try:
        df = pd.read_csv(GPU_DIR / "All_GPUs.csv", on_bad_lines="skip")
    except Exception:
        return pd.DataFrame()

    if "Name" not in df.columns:
        return pd.DataFrame()

    df = df[["Name", "Manufacturer", "Memory", "Release_Date"]].copy()
    df = df.rename(columns={"Name": "raw_name", "Manufacturer": "raw_manufacturer",
                              "Memory": "raw_memory", "Release_Date": "raw_release"})
    df["vram_gb"] = df["raw_memory"].apply(parse_vram_mb)
    df["release_year"] = df["raw_release"].apply(parse_release_year)
    df["gpu_name"] = df["raw_name"].apply(normalize_gpu_name)
    df["manufacturer"] = df["raw_manufacturer"].astype(str).str.strip().apply(
        lambda x: "NVIDIA" if x.lower() == "nvidia" else
                  "AMD"    if x.lower() == "amd"    else
                  "Intel"  if x.lower() == "intel"  else x
    )
    df = df[["gpu_name", "manufacturer", "vram_gb", "release_year"]].drop_duplicates()
    return df


def clean_api_scores() -> pd.DataFrame:
    df = pd.read_csv(GPU_DIR / "GPU_scores_graphicsAPIs.csv", on_bad_lines="skip")
    df = df.rename(columns={"Device": "raw_name", "Manufacturer": "raw_manufacturer"})

    # Compute a composite API score: mean of available numeric API columns
    api_cols = [c for c in ["CUDA", "Metal", "OpenCL", "Vulkan"] if c in df.columns]
    df[api_cols] = df[api_cols].apply(pd.to_numeric, errors="coerce")
    df["graphics_api_score"] = df[api_cols].mean(axis=1, skipna=True).round(0)

    # Keep only rows that have at least one API score
    df = df.dropna(subset=["graphics_api_score"])
    df["gpu_name"] = df["raw_name"].apply(normalize_gpu_name)
    df = df[["gpu_name", "graphics_api_score"]].drop_duplicates(subset=["gpu_name"])
    return df


# ─────────────────────────────────────────────────────────────────────────────
# TASK 4 — BUILD MASTER DATASET
# ─────────────────────────────────────────────────────────────────────────────

def build_master() -> pd.DataFrame:
    print("\n" + "═" * 70)
    print("  TASK 3 & 4 — CLEANING, NORMALISATION & MASTER DATASET")
    print("═" * 70)

    benchmarks = clean_benchmarks()
    all_gpus   = clean_all_gpus()
    api_scores = clean_api_scores()

    print(f"  Benchmark rows  (after clean) : {len(benchmarks)}")
    print(f"  All_GPUs rows   (after clean) : {len(all_gpus)}")
    print(f"  API score rows  (after clean) : {len(api_scores)}")

    # --- deduplicate benchmarks: keep highest score per gpu_name ---
    benchmarks = (
        benchmarks.sort_values("benchmark_score", ascending=False)
                  .drop_duplicates(subset=["gpu_name"], keep="first")
    )

    # --- merge: benchmarks as spine ---
    master = benchmarks[["gpu_name", "manufacturer", "benchmark_score", "release_year"]].copy()

    # Augment with VRAM from All_GPUs (best-effort fuzzy: normalised name join)
    if not all_gpus.empty:
        master = master.merge(
            all_gpus[["gpu_name", "vram_gb"]].drop_duplicates("gpu_name"),
            on="gpu_name", how="left"
        )
    else:
        master["vram_gb"] = float("nan")

    # Augment with API score
    master = master.merge(api_scores, on="gpu_name", how="left")

    # Final column order & type cleanup
    master = master[[
        "gpu_name", "manufacturer", "benchmark_score",
        "graphics_api_score", "vram_gb", "release_year"
    ]].copy()
    master["benchmark_score"]    = master["benchmark_score"].astype(int)
    master["graphics_api_score"] = master["graphics_api_score"].round(0)
    master["release_year"]       = master["release_year"].astype("Int64", errors="ignore")

    # Remove any remaining garbage rows
    master = master[master["gpu_name"].str.len() > 2].reset_index(drop=True)

    out = OUT_DIR / "gpu_master.csv"
    master.to_csv(out, index=False)
    print(f"\n  ✅  gpu_master.csv saved → {out}")
    print(f"      Total GPUs in master : {len(master)}")

    return master


# ─────────────────────────────────────────────────────────────────────────────
# TASK 5 — GENERATE GPU TIERS
# ─────────────────────────────────────────────────────────────────────────────

def assign_tier(percentile: float) -> str:
    """
    Assign tier based on percentile rank (0 = lowest, 1 = highest).
    Thresholds (top-down):
      S  ≥ 90th   →  top 10%
      A  70-90th
      B  40-70th
      C  15-40th
      D  < 15th   →  bottom 15%
    """
    if percentile >= 0.90:
        return "S"
    elif percentile >= 0.70:
        return "A"
    elif percentile >= 0.40:
        return "B"
    elif percentile >= 0.15:
        return "C"
    else:
        return "D"


def generate_tiers(master: pd.DataFrame) -> pd.DataFrame:
    print("\n" + "═" * 70)
    print("  TASK 5 — GPU TIER ASSIGNMENT")
    print("═" * 70)

    tiers = master[["gpu_name", "benchmark_score"]].copy()
    tiers = tiers.sort_values("benchmark_score", ascending=False).reset_index(drop=True)

    # Percentile rank (higher score = higher percentile)
    tiers["percentile"] = tiers["benchmark_score"].rank(pct=True, method="average")
    tiers["tier"] = tiers["percentile"].apply(assign_tier)
    tiers = tiers.drop(columns=["percentile"])

    out = OUT_DIR / "gpu_tiers.csv"
    tiers.to_csv(out, index=False)
    print(f"  ✅  gpu_tiers.csv saved → {out}")

    counts = tiers["tier"].value_counts().sort_index()
    for tier, count in counts.items():
        print(f"     Tier {tier} : {count:>4} GPUs")

    return tiers


# ─────────────────────────────────────────────────────────────────────────────
# TASK 6 — LOOKUP JSON FILES
# ─────────────────────────────────────────────────────────────────────────────

def generate_lookups(master: pd.DataFrame, tiers: pd.DataFrame):
    print("\n" + "═" * 70)
    print("  TASK 6 — GENERATING LOOKUP JSON FILES")
    print("═" * 70)

    merged = tiers.merge(
        master[["gpu_name", "manufacturer", "graphics_api_score", "vram_gb", "release_year"]],
        on="gpu_name", how="left"
    )

    # ── gpu_lookup.json ───────────────────────────────────────────────────
    lookup = {}
    for _, row in merged.iterrows():
        entry = {
            "tier": row["tier"],
            "benchmark_score": int(row["benchmark_score"]),
        }
        if not pd.isna(row.get("manufacturer", None)):
            entry["manufacturer"] = row["manufacturer"]
        if not pd.isna(row.get("graphics_api_score", None)):
            entry["graphics_api_score"] = int(row["graphics_api_score"])
        if not pd.isna(row.get("vram_gb", None)):
            entry["vram_gb"] = float(row["vram_gb"])
        if not pd.isna(row.get("release_year", None)):
            entry["release_year"] = int(row["release_year"])
        lookup[row["gpu_name"]] = entry

    lookup_path = OUT_DIR / "gpu_lookup.json"
    with open(lookup_path, "w", encoding="utf-8") as f:
        json.dump(lookup, f, indent=2, ensure_ascii=False)
    print(f"  ✅  gpu_lookup.json saved  → {lookup_path}  ({len(lookup)} entries)")

    # ── gpu_tiers.json (tier → list of GPUs) ─────────────────────────────
    tiers_json: dict[str, list] = {"S": [], "A": [], "B": [], "C": [], "D": []}
    for _, row in merged.sort_values("benchmark_score", ascending=False).iterrows():
        tiers_json[row["tier"]].append({
            "gpu_name": row["gpu_name"],
            "benchmark_score": int(row["benchmark_score"]),
        })

    tiers_json_path = OUT_DIR / "gpu_tiers.json"
    with open(tiers_json_path, "w", encoding="utf-8") as f:
        json.dump(tiers_json, f, indent=2, ensure_ascii=False)
    print(f"  ✅  gpu_tiers.json saved   → {tiers_json_path}")


# ─────────────────────────────────────────────────────────────────────────────
# TASK 7 — VALIDATION REPORT
# ─────────────────────────────────────────────────────────────────────────────

def validation_report(master: pd.DataFrame, tiers: pd.DataFrame):
    print("\n" + "═" * 70)
    print("  TASK 7 — VALIDATION REPORT")
    print("═" * 70)

    merged = tiers.merge(master[["gpu_name", "manufacturer"]], on="gpu_name", how="left")

    print(f"\n  Total GPUs processed : {len(tiers)}")
    print(f"\n  GPUs per tier:")
    for tier in ["S", "A", "B", "C", "D"]:
        subset = tiers[tiers["tier"] == tier]
        print(f"    {tier} : {len(subset)}")

    print(f"\n  ── Top 20 GPUs ──")
    top20 = tiers.head(20)[["gpu_name", "benchmark_score", "tier"]]
    print(top20.to_string(index=False))

    print(f"\n  ── Bottom 20 GPUs ──")
    bottom20 = tiers.tail(20)[["gpu_name", "benchmark_score", "tier"]]
    print(bottom20.to_string(index=False))

    print(f"\n  ── Example per tier ──")
    for tier in ["S", "A", "B", "C", "D"]:
        examples = tiers[tiers["tier"] == tier].head(3)[["gpu_name", "benchmark_score"]]
        examples_str = ", ".join(
            f"{row['gpu_name']} ({row['benchmark_score']})"
            for _, row in examples.iterrows()
        )
        print(f"    [{tier}] {examples_str}")

    print(f"\n  ── Dataset Quality Concerns ──")
    missing_vram = master["vram_gb"].isna().sum()
    missing_api  = master["graphics_api_score"].isna().sum()
    missing_year = master["release_year"].isna().sum()
    total        = len(master)
    print(f"    Missing VRAM            : {missing_vram}/{total} ({missing_vram/total*100:.1f}%)")
    print(f"    Missing API score       : {missing_api}/{total}  ({missing_api/total*100:.1f}%)")
    print(f"    Missing release year    : {missing_year}/{total} ({missing_year/total*100:.1f}%)")
    print(f"    Benchmark score range   : {tiers['benchmark_score'].min()} – {tiers['benchmark_score'].max()}")
    print(f"    Note: All_GPUs.csv has multiline rows making VRAM join partial.")
    print(f"          GPU_benchmarks_v7 includes some non-consumer entries (GRID, Tesla)")
    print(f"          which have been partially filtered but may still be present.")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "█" * 70)
    print("  RigCheck GPU Tier Engine — Pipeline Run")
    print("█" * 70)

    run_audit()
    identify_sources()
    master = build_master()
    tiers  = generate_tiers(master)
    generate_lookups(master, tiers)
    validation_report(master, tiers)

    print("\n" + "█" * 70)
    print("  Pipeline complete. Output files in /gpu/:")
    print("    gpu_master.csv")
    print("    gpu_tiers.csv")
    print("    gpu_lookup.json")
    print("    gpu_tiers.json")
    print("█" * 70 + "\n")


if __name__ == "__main__":
    main()
