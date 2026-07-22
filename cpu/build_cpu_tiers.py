import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
"""
RigCheck CPU Tier Engine — Build Pipeline
==========================================
Pipeline: Dataset Audit → Cleaning → Master Dataset → Tier Assignment → Lookup Files & Aliases

Processes the full CPU_benchmark_v4.csv dataset.
"""

import json
import re
import pandas as pd
import numpy as np
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CPU_DIR = PROJECT_ROOT / "cpu"
OUT_DIR = CPU_DIR

TIER_THRESHOLDS = {          # percentile boundaries (top-down)
    "S": 0.90,               # top 10 %
    "A": 0.70,               # 70–90 %
    "B": 0.40,               # 40–70 %
    "C": 0.15,               # 15–40 %
    "D": 0.00,               # bottom 15 %
}

MANUFACTURER_MAP = {
    "intel": "Intel",
    "core": "Intel",
    "xeon": "Intel",
    "celeron": "Intel",
    "pentium": "Intel",
    "amd": "AMD",
    "ryzen": "AMD",
    "threadripper": "AMD",
    "athlon": "AMD",
    "fx-": "AMD",
    "apple": "Apple",
}

STRIP_PREFIXES = [
    r"^intel\s+",
    r"^amd\s+",
    r"^apple\s+",
    r"^core\s+",
    r"\s+processor\s*$",
    r"\s+cpu\s*$",
]

# ─────────────────────────────────────────────────────────────────────────────
# TASK 1 — DATASET AUDIT
# ─────────────────────────────────────────────────────────────────────────────

def audit_dataset(filepath: Path, name_col: str) -> dict:
    try:
        df = pd.read_csv(filepath, on_bad_lines="skip", low_memory=False)
    except Exception as e:
        return {"error": str(e)}

    rows, cols = df.shape
    missing = df.isnull().sum().to_dict()
    duplicates = int(df.duplicated().sum())
    unique_cpus = int(df[name_col].nunique()) if name_col in df.columns else "N/A"

    return {
        "file": filepath.name,
        "rows": rows,
        "columns": cols,
        "column_names": list(df.columns),
        "missing_values": {k: int(v) for k, v in missing.items() if v > 0},
        "duplicate_rows": duplicates,
        "unique_cpu_count": unique_cpus,
    }


def run_audit():
    src_path = PROJECT_ROOT / "CPU_benchmark_v4.csv"
    print("\n" + "═" * 70)
    print("  TASK 1 — DATASET AUDIT")
    print("═" * 70)

    result = audit_dataset(src_path, "cpuName")
    print(f"\n📁 {result['file']}")
    print(f"   Rows         : {result.get('rows', '?')}")
    print(f"   Columns      : {result.get('columns', '?')}")
    print(f"   Column names : {result.get('column_names', [])}")
    print(f"   Duplicates   : {result.get('duplicate_rows', '?')}")
    print(f"   Unique CPUs  : {result.get('unique_cpu_count', '?')}")
    mv = result.get("missing_values", {})
    if mv:
        top_missing = dict(list(mv.items())[:5])
        print(f"   Missing vals  : {top_missing} ...")
    else:
        print(f"   Missing vals  : None")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# TASK 2 — CLEANING & NORMALISATION
# ─────────────────────────────────────────────────────────────────────────────

def infer_manufacturer(name: str) -> str:
    name_lower = name.lower()
    for key, mfr in MANUFACTURER_MAP.items():
        if key in name_lower:
            return mfr
    return "Unknown"


def strip_clock_suffix(name: str) -> str:
    """Strips clock suffixes like ' @ 2.60GHz' from CPU names."""
    if not isinstance(name, str):
        return ""
    return re.sub(r"\s*@\s*[\d\.]+\s*[Gg][Hh][Zz].*$", "", name).strip()


def normalize_cpu_name(raw: str) -> str:
    """Normalize CPU name for consistent matching and alias generation."""
    if not isinstance(raw, str):
        return "Unknown"
    name = strip_clock_suffix(raw)
    for pat in STRIP_PREFIXES:
        name = re.sub(pat, "", name, flags=re.IGNORECASE).strip()
    name = re.sub(r"[-_]", " ", name)
    name = re.sub(r"\s{2,}", " ", name).strip()
    return name


# ─────────────────────────────────────────────────────────────────────────────
# TASK 3 — BUILD MASTER DATASET
# ─────────────────────────────────────────────────────────────────────────────

def build_master() -> pd.DataFrame:
    print("\n" + "═" * 70)
    print("  TASK 2 & 3 — CLEANING, NORMALISATION & MASTER DATASET")
    print("═" * 70)

    src_path = PROJECT_ROOT / "CPU_benchmark_v4.csv"
    df = pd.read_csv(src_path, on_bad_lines="skip")

    df["cpuMark"] = pd.to_numeric(df["cpuMark"], errors="coerce")
    df = df.dropna(subset=["cpuMark"])
    df["cpuName"] = df["cpuName"].astype(str).str.strip()

    print(f"  Benchmark rows (after clean) : {len(df)}")

    # Deduplicate: keep highest score per CPU name (stripped of clock suffix)
    df["clean_canonical_name"] = df["cpuName"].apply(strip_clock_suffix)
    df = (
        df.sort_values("cpuMark", ascending=False)
          .drop_duplicates(subset=["clean_canonical_name"], keep="first")
    )

    # Normalize name
    df["cpu_name"] = df["clean_canonical_name"].apply(normalize_cpu_name)
    df["manufacturer"] = df["clean_canonical_name"].apply(infer_manufacturer)

    # Build master
    master = df[["clean_canonical_name", "cpu_name", "manufacturer", "cpuMark", "cores", "TDP", "socket", "category"]].copy()
    master.columns = ["canonical_name", "cpu_name_normal", "manufacturer", "benchmark_score", "cores", "tdp", "socket", "category"]
    
    master["benchmark_score"] = master["benchmark_score"].astype(int)
    master = master[master["canonical_name"].str.len() > 2].reset_index(drop=True)

    out = OUT_DIR / "cpu_master.csv"
    master.to_csv(out, index=False)
    print(f"\n  ✅  cpu_master.csv saved → {out}")
    print(f"      Total CPUs in master : {len(master)}")

    return master


# ─────────────────────────────────────────────────────────────────────────────
# TASK 4 — GENERATE CPU TIERS
# ─────────────────────────────────────────────────────────────────────────────

def assign_tier(percentile: float) -> str:
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
    print("  TASK 4 — CPU TIER ASSIGNMENT")
    print("═" * 70)

    tiers = master[["canonical_name", "benchmark_score"]].copy()
    tiers = tiers.sort_values("benchmark_score", ascending=False).reset_index(drop=True)

    # Percentile rank
    tiers["percentile"] = tiers["benchmark_score"].rank(pct=True, method="average")
    tiers["tier"] = tiers["percentile"].apply(assign_tier)
    tiers = tiers.drop(columns=["percentile"])

    out = OUT_DIR / "cpu_tiers.csv"
    tiers.to_csv(out, index=False)
    print(f"  ✅  cpu_tiers.csv saved → {out}")

    counts = tiers["tier"].value_counts().sort_index()
    for tier, count in counts.items():
        print(f"     Tier {tier} : {count:>4} CPUs")

    return tiers


# ─────────────────────────────────────────────────────────────────────────────
# TASK 5 — LOOKUP & ALIASES JSON FILES
# ─────────────────────────────────────────────────────────────────────────────

def generate_lookups(master: pd.DataFrame, tiers: pd.DataFrame):
    print("\n" + "═" * 70)
    print("  TASK 5 — GENERATING LOOKUP & ALIASES JSON FILES")
    print("═" * 70)

    merged = tiers.merge(
        master[["canonical_name", "cpu_name_normal", "manufacturer", "cores", "tdp", "socket", "category"]],
        on="canonical_name", how="left"
    )

    # Sort descending by score for ranking
    merged = merged.sort_values("benchmark_score", ascending=False).reset_index(drop=True)
    merged["rank"] = merged.index + 1

    # ── cpu_lookup.json ───────────────────────────────────────────────────
    lookup = {}
    aliases = {}

    for _, row in merged.iterrows():
        canonical = row["canonical_name"]
        entry = {
            "canonical_name": canonical,
            "benchmark_score": int(row["benchmark_score"]),
            "rank": int(row["rank"]),
            "tier": row["tier"],
        }
        if not pd.isna(row.get("manufacturer", None)):
            entry["manufacturer"] = row["manufacturer"]
        if not pd.isna(row.get("cores", None)):
            entry["cores"] = int(row["cores"])
        if not pd.isna(row.get("tdp", None)):
            entry["tdp"] = int(row["tdp"])
        if not pd.isna(row.get("socket", None)):
            entry["socket"] = row["socket"]
        if not pd.isna(row.get("category", None)):
            entry["category"] = row["category"]
        
        lookup[canonical] = entry

        # ── alias generation ────────────────────────────────────────────────
        # Resolve common variations to this canonical CPU name
        variations = []
        variations.append(canonical)
        variations.append(canonical.lower())
        variations.append(row["cpu_name_normal"])
        variations.append(row["cpu_name_normal"].lower())

        # For Intel CPUs
        if "intel" in canonical.lower():
            # i7-13650HX, Intel i7-13650HX, Intel Core i7-13650HX, Core i7-13650HX
            # Remove "Intel"
            no_intel = re.sub(r"^intel\s+", "", canonical, flags=re.IGNORECASE).strip()
            variations.extend([no_intel, no_intel.lower()])
            # Remove "Intel Core"
            no_intel_core = re.sub(r"^intel\s+core\s+", "", canonical, flags=re.IGNORECASE).strip()
            no_intel_core = re.sub(r"^core\s+", "", no_intel_core, flags=re.IGNORECASE).strip()
            variations.extend([no_intel_core, no_intel_core.lower()])

            # Hyphen variations
            if "-" in no_intel_core:
                sp = no_intel_core.replace("-", " ")
                variations.extend([sp, sp.lower()])
            else:
                match = re.match(r"^(i\d)\s+(\w+.*)$", no_intel_core, re.IGNORECASE)
                if match:
                    hyphenated = f"{match.group(1)}-{match.group(2)}"
                    variations.extend([hyphenated, hyphenated.lower()])

        # For AMD CPUs
        elif "amd" in canonical.lower():
            # Remove "AMD"
            no_amd = re.sub(r"^amd\s+", "", canonical, flags=re.IGNORECASE).strip()
            variations.extend([no_amd, no_amd.lower()])
            # Remove "AMD Ryzen"
            no_amd_ryzen = re.sub(r"^amd\s+ryzen\s+", "", canonical, flags=re.IGNORECASE).strip()
            no_amd_ryzen = re.sub(r"^ryzen\s+", "", no_amd_ryzen, flags=re.IGNORECASE).strip()
            variations.extend([no_amd_ryzen, no_amd_ryzen.lower()])

            if "-" in no_amd_ryzen:
                sp = no_amd_ryzen.replace("-", " ")
                variations.extend([sp, sp.lower()])
            else:
                match = re.match(r"^(\d)\s+(\w+.*)$", no_amd_ryzen, re.IGNORECASE)
                if match:
                    hyphenated = f"{match.group(1)}-{match.group(2)}"
                    variations.extend([hyphenated, hyphenated.lower()])

        # Store all normalized forms pointing to canonical name
        for v in set(variations):
            norm_v = re.sub(r"\s+", " ", re.sub(r"[-_]", " ", v.strip())).lower()
            aliases[norm_v] = canonical

    lookup_path = OUT_DIR / "cpu_lookup.json"
    with open(lookup_path, "w", encoding="utf-8") as f:
        json.dump(lookup, f, indent=2, ensure_ascii=False)
    print(f"  ✅  cpu_lookup.json saved  → {lookup_path}  ({len(lookup)} entries)")

    # ── cpu_aliases.json ────────────────────────────────────────────────
    aliases_path = OUT_DIR / "cpu_aliases.json"
    with open(aliases_path, "w", encoding="utf-8") as f:
        json.dump(aliases, f, indent=2, ensure_ascii=False)
    print(f"  ✅  cpu_aliases.json saved → {aliases_path}  ({len(aliases)} mappings)")

    # ── cpu_tiers.json (tier → list of CPUs) ─────────────────────────────
    tiers_json: dict[str, list] = {"S": [], "A": [], "B": [], "C": [], "D": []}
    for _, row in merged.iterrows():
        tiers_json[row["tier"]].append({
            "cpu_name": row["canonical_name"],
            "benchmark_score": int(row["benchmark_score"]),
        })

    tiers_json_path = OUT_DIR / "cpu_tiers.json"
    with open(tiers_json_path, "w", encoding="utf-8") as f:
        json.dump(tiers_json, f, indent=2, ensure_ascii=False)
    print(f"  ✅  cpu_tiers.json saved   → {tiers_json_path}")


# ─────────────────────────────────────────────────────────────────────────────
# TASK 6 — VALIDATION REPORT
# ─────────────────────────────────────────────────────────────────────────────

def validation_report(master: pd.DataFrame, tiers: pd.DataFrame):
    print("\n" + "═" * 70)
    print("  TASK 6 — VALIDATION REPORT")
    print("═" * 70)

    print(f"\n  Total CPUs processed : {len(tiers)}")
    print(f"\n  CPUs per tier:")
    for tier in ["S", "A", "B", "C", "D"]:
        subset = tiers[tiers["tier"] == tier]
        print(f"    {tier} : {len(subset)}")

    print(f"\n  ── Top 15 CPUs ──")
    top15 = tiers.head(15)[["canonical_name", "benchmark_score", "tier"]]
    print(top15.to_string(index=False))

    print(f"\n  ── Bottom 15 CPUs ──")
    bottom15 = tiers.tail(15)[["canonical_name", "benchmark_score", "tier"]]
    print(bottom15.to_string(index=False))

    print(f"\n  ── Example per tier ──")
    for tier in ["S", "A", "B", "C", "D"]:
        examples = tiers[tiers["tier"] == tier].head(3)[["canonical_name", "benchmark_score"]]
        examples_str = ", ".join(
            f"{row['canonical_name']} ({row['benchmark_score']})"
            for _, row in examples.iterrows()
        )
        print(f"    [{tier}] {examples_str}")

    print(f"\n  ── Dataset Quality ──")
    print(f"    Benchmark score range : {tiers['benchmark_score'].min()} – {tiers['benchmark_score'].max()}")
    print(f"    Total entries         : {len(master)}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "█" * 70)
    print("  RigCheck CPU Tier Engine — Pipeline Run")
    print("█" * 70)

    run_audit()
    master = build_master()
    tiers  = generate_tiers(master)
    generate_lookups(master, tiers)
    validation_report(master, tiers)

    print("\n" + "█" * 70)
    print("  Pipeline complete. Output files in /cpu/:")
    print("    cpu_master.csv")
    print("    cpu_tiers.csv")
    print("    cpu_lookup.json")
    print("    cpu_aliases.json")
    print("    cpu_tiers.json")
    print("█" * 70 + "\n")


if __name__ == "__main__":
    main()
