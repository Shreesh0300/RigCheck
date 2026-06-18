"""
RigCheck GPU Tier Engine V2 — Validation & Quality Audit
=========================================================
READ-ONLY pass over:
    gpu_master.csv
    gpu_tiers.csv
    gpu_lookup.json
    gpu_tiers.json

Produces:
    gpu_non_gaming_report.csv
    gpu_missing_vram.csv
    gpu_missing_release_year.csv
    gpu_validation_report.md
"""

import json
import re
import sys
from pathlib import Path

import pandas as pd

# Force UTF-8 so emoji / box-drawing chars don't crash on Windows cp1252
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

GPU_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def pct(n: int, total: int) -> str:
    return f"{n}/{total} ({n / total * 100:.1f}%)" if total else "0/0 (0.0%)"


def load_master() -> pd.DataFrame:
    return pd.read_csv(GPU_DIR / "gpu_master.csv", low_memory=False)


def load_tiers() -> pd.DataFrame:
    return pd.read_csv(GPU_DIR / "gpu_tiers.csv", low_memory=False)


# ---------------------------------------------------------------------------
# Patterns that flag a GPU as non-gaming / professional / virtual
# ---------------------------------------------------------------------------

NON_GAMING_PATTERNS = [
    # Datacenter / Tesla
    r"\bTesla\b",
    r"\bV100\b", r"\bA100\b", r"\bP100\b", r"\bT4\b",
    # GRID / Virtual
    r"\bGRID\b", r"\bVirtual\b", r"display.*adapter",
    r"\bMxGPU\b", r"\bvGPU\b",
    # Quadro / RTX professional workstation lines
    r"\bQuadro\b", r"\bFirePro\b", r"\bFireStream\b",
    r"\bWorkstation\b",
    # Explicitly named professional SKUs
    r"\bRTX\s+A\d{4}\b",   # RTX A4000, A5000, A6000 — workstation
    r"\bRTX\s+A\d{3}\b",   # RTX A2000 etc.
    # Mining / Compute cards
    r"\bP106\b", r"\bP104\b", r"\bP102\b",
    r"\bCMP\b",
    # Cloud / Virtual display
    r"\bCitrix\b", r"\bmatrox\b", r"\bBarco\b", r"\bEIZO\b",
    r"\bNVS\b", r"\bK\d+[Mm]\b",   # Quadro K-series mobile
    # Old ISV / embedded
    r"\bFireMV\b", r"\bFireGL\b",
    # TITAN workstation-tier  (keep TITAN RTX since it's consumer/gaming)
    r"\bTITAN\s+V\b", r"\bTITAN\s+X\b(?!\s*Pascal)",  # Titan V is compute
    # Intel compute / server
    r"\bArc\s+Pro\b",
    # ARM mobile SoC cores (not desktop GPU)
    r"\bMali\b", r"\bAdreno\b", r"\bPowerVR\b",
    # Apple GPU (not a PC GPU)
    r"\bApple\b", r"\bM1\b", r"\bM2\b",
    # Misc junk
    r"\bllvmpipe\b", r"\bparavirtual\b", r"\bMuMu\b",
    r"^15FF$", r"^A\d{2}$",           # weird encoded entries
    r"\bIntel\s+G\d{2}\b",            # ancient Intel integrated
    r"\bController\b",
    r"\bChipset\b", r"\bChipsatz\b",
    r"\bExpress\b.*\bchip",
    r"\bIGP\b", r"\bExpress\s+Chip",
    r"\bMobile\s+Intel\b",
    r"VIA\s+Chrome",
    r"\bS3\s+", r"\bRage\s+\d",
    r"Quadro2",
    r"\bFireMV\b",
    r"^Dell\s+\d",
]

NON_GAMING_RE = re.compile("|".join(NON_GAMING_PATTERNS), re.IGNORECASE)


def is_non_gaming(name: str) -> bool:
    return bool(NON_GAMING_RE.search(str(name)))


def non_gaming_reason(name: str) -> str:
    """Return a short label for why the GPU was flagged."""
    n = str(name)
    checks = {
        "Datacenter/Tesla": [r"\bTesla\b", r"\bV100\b", r"\bA100\b", r"\bP100\b", r"\bT4\b"],
        "GRID/Virtual":     [r"\bGRID\b", r"\bVirtual\b", r"\bMxGPU\b", r"\bCitrix\b"],
        "Professional/Quadro": [r"\bQuadro\b", r"\bFirePro\b", r"\bFireStream\b",
                                r"\bRTX\s+A\d{4}\b", r"\bRTX\s+A\d{3}\b"],
        "Mining/Compute":   [r"\bP106\b", r"\bP104\b", r"\bP102\b", r"\bCMP\b"],
        "Mobile SoC":       [r"\bMali\b", r"\bAdreno\b", r"\bPowerVR\b"],
        "Apple/ARM":        [r"\bApple\b", r"\bM1\b", r"\bM2\b", r"\bMali\b"],
        "Embedded/ISV":     [r"\bBarco\b", r"\bEIZO\b", r"\bMatrox\b",
                             r"\bFireMV\b", r"\bFireGL\b", r"\bNVS\b"],
        "Integrated/Legacy":[r"\bIGP\b", r"\bChipset\b", r"\bController\b",
                             r"VIA\s+Chrome", r"\bS3\s+", r"\bRage\s+\d",
                             r"\bMobile\s+Intel\b", r"\bExpress\b"],
        "TITAN Compute":    [r"\bTITAN\s+V\b"],
        "Junk/Unknown":     [r"\bllvmpipe\b", r"\bparavirtual\b", r"\bMuMu\b",
                             r"^15FF$", r"^A\d{2}$"],
    }
    for label, patterns in checks.items():
        for pat in patterns:
            if re.search(pat, n, re.IGNORECASE):
                return label
    return "Other-Professional"


# ---------------------------------------------------------------------------
# TASK 1 — Master Dataset Validation
# ---------------------------------------------------------------------------

def task1_master_validation(master: pd.DataFrame) -> dict:
    total = len(master)
    unique = master["gpu_name"].nunique()
    dupes  = total - unique

    missing_vram = master["vram_gb"].isna().sum()
    missing_year = master["release_year"].isna().sum()
    missing_api  = master["graphics_api_score"].isna().sum()
    missing_mfr  = (master["manufacturer"].isna() |
                    (master["manufacturer"].astype(str).str.strip() == "") |
                    (master["manufacturer"].astype(str).str.lower() == "unknown")).sum()

    stats = {
        "total": total,
        "unique": unique,
        "duplicates": dupes,
        "missing_vram": missing_vram,
        "missing_year": missing_year,
        "missing_api":  missing_api,
        "missing_mfr":  missing_mfr,
    }

    print("\n" + "=" * 66)
    print("  TASK 1 — MASTER DATASET VALIDATION")
    print("=" * 66)
    print(f"  Total GPU rows       : {total}")
    print(f"  Unique GPU names     : {unique}")
    print(f"  Duplicate rows       : {dupes}")
    print(f"  Missing VRAM         : {pct(missing_vram, total)}")
    print(f"  Missing Release Year : {pct(missing_year, total)}")
    print(f"  Missing API Score    : {pct(missing_api,  total)}")
    print(f"  Missing Manufacturer : {pct(missing_mfr,  total)}")

    return stats


# ---------------------------------------------------------------------------
# TASK 2 — Gaming GPU Filter
# ---------------------------------------------------------------------------

def task2_non_gaming_filter(master: pd.DataFrame):
    master["_is_non_gaming"] = master["gpu_name"].apply(is_non_gaming)
    master["_reason"]        = master["gpu_name"].apply(
        lambda x: non_gaming_reason(x) if is_non_gaming(x) else ""
    )

    non_gaming = master[master["_is_non_gaming"]].copy()
    non_gaming = non_gaming.rename(columns={"_reason": "non_gaming_reason"})
    non_gaming = non_gaming.drop(columns=["_is_non_gaming"])

    out_path = GPU_DIR / "gpu_non_gaming_report.csv"
    non_gaming[["gpu_name", "manufacturer", "benchmark_score",
                "non_gaming_reason"]].to_csv(out_path, index=False)

    total       = len(master)
    ng_count    = len(non_gaming)
    gaming_count = total - ng_count

    print("\n" + "=" * 66)
    print("  TASK 2 — NON-GAMING GPU FILTER")
    print("=" * 66)
    print(f"  Total GPUs           : {total}")
    print(f"  Gaming GPUs (est.)   : {pct(gaming_count, total)}")
    print(f"  Non-gaming GPUs      : {pct(ng_count, total)}")
    print()

    reason_counts = non_gaming["non_gaming_reason"].value_counts()
    for reason, count in reason_counts.items():
        print(f"    {reason:<30} {count:>4} GPUs")

    print(f"\n  Sample non-gaming entries:")
    sample = non_gaming.head(15)[["gpu_name", "non_gaming_reason", "benchmark_score"]]
    print(sample.to_string(index=False))

    print(f"\n  Saved: gpu_non_gaming_report.csv  ({ng_count} entries)")

    # Clean up temp cols from master
    master.drop(columns=["_is_non_gaming", "_reason"], inplace=True, errors="ignore")

    return non_gaming


# ---------------------------------------------------------------------------
# TASK 3 — VRAM Coverage Analysis
# ---------------------------------------------------------------------------

def task3_vram_coverage(master: pd.DataFrame):
    total       = len(master)
    with_vram   = master["vram_gb"].notna().sum()
    without_vram = master["vram_gb"].isna().sum()

    missing_df = master[master["vram_gb"].isna()][
        ["gpu_name", "manufacturer", "benchmark_score"]
    ].sort_values("benchmark_score", ascending=False)

    out_path = GPU_DIR / "gpu_missing_vram.csv"
    missing_df.to_csv(out_path, index=False)

    print("\n" + "=" * 66)
    print("  TASK 3 — VRAM COVERAGE ANALYSIS")
    print("=" * 66)
    print(f"  Total GPUs           : {total}")
    print(f"  GPUs WITH VRAM data  : {pct(with_vram,    total)}")
    print(f"  GPUs WITHOUT VRAM    : {pct(without_vram, total)}")
    print()

    # VRAM distribution for GPUs that do have it
    has_vram = master.dropna(subset=["vram_gb"])
    if not has_vram.empty:
        print("  VRAM distribution (GPUs with data):")
        bins = [0, 2, 4, 6, 8, 12, 16, 24, float("inf")]
        labels = ["<= 2 GB", "3-4 GB", "5-6 GB", "7-8 GB", "9-12 GB",
                  "13-16 GB", "17-24 GB", "> 24 GB"]
        has_vram = has_vram.copy()
        has_vram["vram_bin"] = pd.cut(has_vram["vram_gb"], bins=bins, labels=labels)
        dist = has_vram["vram_bin"].value_counts().sort_index()
        for label, count in dist.items():
            print(f"    {label:<12} : {count:>4}")

    print(f"\n  Top 10 high-score GPUs missing VRAM:")
    print(missing_df.head(10).to_string(index=False))
    print(f"\n  Saved: gpu_missing_vram.csv  ({without_vram} entries)")


# ---------------------------------------------------------------------------
# TASK 4 — Release Year Coverage
# ---------------------------------------------------------------------------

def task4_release_year(master: pd.DataFrame):
    total       = len(master)
    has_year    = master["release_year"].notna().sum()
    missing_year = master["release_year"].isna().sum()

    missing_df = master[master["release_year"].isna()][
        ["gpu_name", "manufacturer", "benchmark_score"]
    ].sort_values("benchmark_score", ascending=False)

    out_path = GPU_DIR / "gpu_missing_release_year.csv"
    missing_df.to_csv(out_path, index=False)

    print("\n" + "=" * 66)
    print("  TASK 4 — RELEASE YEAR COVERAGE")
    print("=" * 66)
    print(f"  Total GPUs           : {total}")
    print(f"  GPUs WITH year       : {pct(has_year,    total)}")
    print(f"  GPUs WITHOUT year    : {pct(missing_year, total)}")

    if has_year > 0:
        year_data = master.dropna(subset=["release_year"])
        yr_min = int(year_data["release_year"].min())
        yr_max = int(year_data["release_year"].max())
        print(f"  Year range           : {yr_min} – {yr_max}")
        yr_dist = year_data["release_year"].astype(int).value_counts().sort_index()
        print("\n  GPUs per release year:")
        for yr, cnt in yr_dist.items():
            bar = "#" * (cnt // 10)
            print(f"    {yr}: {cnt:>4}  {bar}")

    print(f"\n  Improvement suggestion:")
    print(f"    GPU_benchmarks_v7.csv 'testDate' already covers 100% of rows.")
    print(f"    All_GPUs.csv 'Release_Date' column has many more GPUs with dates.")
    print(f"    Parsing All_GPUs multiline format more carefully could close gaps.")
    print(f"\n  Saved: gpu_missing_release_year.csv  ({missing_year} entries)")


# ---------------------------------------------------------------------------
# TASK 5 — Tier Quality Check
# ---------------------------------------------------------------------------

def task5_tier_quality(master: pd.DataFrame, tiers: pd.DataFrame):
    print("\n" + "=" * 66)
    print("  TASK 5 — TIER QUALITY CHECK")
    print("=" * 66)

    merged = tiers.merge(
        master[["gpu_name", "manufacturer", "vram_gb", "release_year",
                "graphics_api_score"]],
        on="gpu_name", how="left"
    )

    issues = []

    for tier in ["S", "A", "B", "C", "D"]:
        subset = merged[merged["tier"] == tier].sort_values(
            "benchmark_score", ascending=False
        ).head(25)
        print(f"\n  --- Tier {tier} — Top 25 entries ---")
        print(subset[["gpu_name", "benchmark_score", "manufacturer",
                       "release_year"]].to_string(index=False))

    # --- Outlier / misplacement checks ---
    print("\n\n  --- Outlier & Misplacement Checks ---")

    # Check 1: Workstation GPUs that slipped through into S-tier
    s_tier = merged[merged["tier"] == "S"]
    workstation_in_s = s_tier[s_tier["gpu_name"].str.contains(
        r"\bQuadro\b|\bFirePro\b|\bTesla\b|\bGRID\b|\bRTX\s+A\b",
        case=False, na=False
    )]
    if not workstation_in_s.empty:
        issues.append(f"  [!] {len(workstation_in_s)} workstation/datacenter GPUs in S-Tier:")
        for _, r in workstation_in_s.iterrows():
            issues.append(f"       {r['gpu_name']} (score={r['benchmark_score']})")

    # Check 2: Ancient GPUs (pre-2010) in B-tier or above
    old_gpus_high = merged[
        (merged["release_year"] < 2010) & (merged["tier"].isin(["S", "A", "B"]))
    ]
    if not old_gpus_high.empty:
        issues.append(f"\n  [!] {len(old_gpus_high)} pre-2010 GPUs ranked B-tier or above:")
        for _, r in old_gpus_high.head(10).iterrows():
            issues.append(
                f"       {r['gpu_name']} (score={r['benchmark_score']}, year={r['release_year']}, tier={r['tier']})"
            )

    # Check 3: Duplicate model names
    dup_names = merged[merged.duplicated(subset=["gpu_name"], keep=False)]
    if not dup_names.empty:
        issues.append(f"\n  [!] {len(dup_names)} duplicate gpu_name rows found")

    # Check 4: Integrated/mobile SoCs in unexpected tiers
    soc_in_high = merged[
        (merged["tier"].isin(["S", "A"])) &
        (merged["gpu_name"].str.contains(
            r"Adreno|Mali|PowerVR|Apple|Ryzen.*Radeon|UHD|Iris",
            case=False, na=False
        ))
    ]
    if not soc_in_high.empty:
        issues.append(f"\n  [!] {len(soc_in_high)} integrated/mobile SoCs in S/A tier:")
        for _, r in soc_in_high.head(5).iterrows():
            issues.append(f"       {r['gpu_name']} (score={r['benchmark_score']}, tier={r['tier']})")

    if issues:
        for issue in issues:
            print(issue)
    else:
        print("  No major misplacements detected.")

    return issues, merged


# ---------------------------------------------------------------------------
# TASK 6 — V2 Scoring Formula Design
# ---------------------------------------------------------------------------

def task6_v2_formula():
    print("\n" + "=" * 66)
    print("  TASK 6 — V2 SCORING FORMULA DESIGN")
    print("=" * 66)

    analysis = """
  CURRENT (V1):
    Tier Score = G3Dmark benchmark score  (100%)

  PROPOSED (V2):
    Tier Score = (0.70 x normalised_benchmark)
               + (0.15 x normalised_vram)
               + (0.15 x normalised_recency)

  COMPONENT DEFINITIONS:
    normalised_benchmark  = GPU G3Dmark / max(G3Dmark)  in dataset
    normalised_vram       = GPU VRAM GB / 24 GB (cap)
    normalised_recency    = (release_year - 2000) / (current_year - 2000)

  ADVANTAGES:
    + Differentiates two GPUs with identical benchmark but different VRAM
      (e.g. RX 6800 XT 16 GB vs RX 6700 XT 12 GB)
    + Rewards newer cards in the same benchmark bracket
    + Better approximates real-world gaming utility

  DISADVANTAGES / RISKS:
    - 75% VRAM missing  -> 75% of cards use fallback (0) for VRAM term,
      biasing them DOWN relative to cards that have VRAM data
    - Penalises older but still-capable GPUs (GTX 1080 Ti still excellent
      at 1440p but year-penalised vs newer budget cards)
    - Introduces compound normalisation errors when combining dimensionally
      different metrics

  BIAS ANALYSIS:
    VRAM bias   : Cards without VRAM data receive 0 for that term (15% of
                  score). This systematically under-ranks unknown-VRAM GPUs.
                  Fix: impute VRAM from model name regex (e.g. "16GB" in name).
    Recency bias: RTX 3090 Ti (2022) vs GTX 1080 Ti (2017) — the recency
                  term adds ~0.015 points to the 3090 Ti, negligible when
                  benchmark gap is >10,000 points. Safe at these weights.
    Workstation : Professional GPUs (Quadro, Tesla) have high VRAM (24-80 GB)
                  which would inflate their VRAM component unfairly for gaming.
                  Fix: Apply gaming-only filter BEFORE scoring.

  RECOMMENDED V2 FORMULA (with mitigations):
    1. Pre-filter: remove non-gaming GPUs (Task 2 list)
    2. Impute VRAM: extract GB from gpu_name string where possible
    3. Cap VRAM at 16 GB for gaming relevance (not 24 GB)
    4. Formula:
         tier_score = 0.75 * norm_benchmark
                    + 0.15 * norm_vram      (0 if unavailable — acceptable
                                             since gaming benchmark already
                                             captures memory bandwidth)
                    + 0.10 * norm_recency
    5. Keep V1 benchmark as tiebreaker if tier_scores are equal
    6. Store both v1_tier and v2_tier in master for comparison before
       committing V2 to production.
"""

    print(analysis)
    return analysis


# ---------------------------------------------------------------------------
# TASK 7 — Validation Report Markdown
# ---------------------------------------------------------------------------

def task7_write_report(stats: dict, non_gaming: pd.DataFrame,
                       master: pd.DataFrame, tiers: pd.DataFrame,
                       issues: list, v2_analysis: str):

    total = stats["total"]

    ng_count     = len(non_gaming)
    gaming_count = total - ng_count

    # Per-tier counts
    tier_counts = tiers["tier"].value_counts().sort_index()

    # top GPU per tier
    merged = tiers.merge(master[["gpu_name", "manufacturer", "vram_gb",
                                  "release_year"]], on="gpu_name", how="left")

    def top_gpus_md(tier: str, n: int = 10) -> str:
        subset = merged[merged["tier"] == tier].sort_values(
            "benchmark_score", ascending=False
        ).head(n)
        rows = []
        for _, r in subset.iterrows():
            rows.append(
                f"| {r['gpu_name']} | {int(r['benchmark_score'])} | "
                f"{r.get('manufacturer', '')} |"
            )
        return "\n".join(rows)

    report = f"""# RigCheck GPU Tier Engine — Validation Report V2

*Generated automatically by `validate_gpu_tiers.py`*

---

## 1. Dataset Health Summary

| Metric | Value |
|---|---|
| Total GPU rows | {total} |
| Unique GPU names | {stats['unique']} |
| Duplicate rows | {stats['duplicates']} |
| Missing VRAM | {pct(stats['missing_vram'], total)} |
| Missing Release Year | {pct(stats['missing_year'], total)} |
| Missing API Score | {pct(stats['missing_api'], total)} |
| Missing Manufacturer | {pct(stats['missing_mfr'], total)} |

> **Note:** `release_year` is sourced from `GPU_benchmarks_v7.csv testDate`
> which covers 100% of rows. Any missing values are entries where the
> test date field was blank in the source.

---

## 2. Missing Data Analysis

### VRAM
- **{pct(stats['missing_vram'], total)}** GPUs are missing VRAM data.
- Root cause: `All_GPUs.csv` uses a multiline CSV format that is difficult
  to parse cleanly with `pd.read_csv`. Only rows that survived parsing and
  matched on `gpu_name` received VRAM values.
- **Recommended fix:** Regex-extract GB value from the `gpu_name` string
  itself (e.g. `"GTX 1080 11GB"`) and from `All_GPUs.csv` using a custom
  multiline parser.

### Release Year
- **{pct(stats['missing_year'], total)}** GPUs are missing release year.
- Most zeros come from GRID/Virtual entries which have no commercial release.

### API Score
- **{pct(stats['missing_api'], total)}** GPUs are missing a composite API score.
- `GPU_scores_graphicsAPIs.csv` only covers 1,213 GPU variants.
  Most legacy and mobile GPUs are absent.

---

## 3. Gaming vs Non-Gaming GPU Analysis

| Category | Count | Percentage |
|---|---|---|
| Estimated gaming GPUs | {gaming_count} | {gaming_count/total*100:.1f}% |
| Non-gaming / professional / datacenter | {ng_count} | {ng_count/total*100:.1f}% |

### Non-Gaming Breakdown
"""

    reason_counts = non_gaming["non_gaming_reason"].value_counts()
    report += "\n| Category | Count |\n|---|---|\n"
    for reason, count in reason_counts.items():
        report += f"| {reason} | {count} |\n"

    report += f"""
> **Action required:** Before V2 release, apply the gaming-GPU filter
> (see `gpu_non_gaming_report.csv`) to strip non-gaming entries from
> the tier files. This will make tier percentiles more meaningful for
> RigCheck's target audience.

---

## 4. Tier Quality Assessment

### Tier Distribution

| Tier | GPU Count | % of Total |
|---|---|---|
"""
    for t in ["S", "A", "B", "C", "D"]:
        cnt = tier_counts.get(t, 0)
        report += f"| {t} | {cnt} | {cnt/total*100:.1f}% |\n"

    report += "\n### Top 10 per Tier\n\n"
    for t in ["S", "A", "B", "C", "D"]:
        report += f"#### Tier {t}\n\n"
        report += "| GPU Name | Benchmark Score | Manufacturer |\n|---|---|---|\n"
        report += top_gpus_md(t, 10) + "\n\n"

    report += "### Detected Issues\n\n"
    if issues:
        for issue in issues:
            report += issue.strip().replace("[!]", "- **[ISSUE]**") + "\n"
    else:
        report += "- No major tier misplacements detected.\n"

    report += f"""
---

## 5. Recommendations for V2 Scoring

### Current Formula (V1)
```
Tier Score = G3Dmark Benchmark Score (100%)
```

### Proposed Formula (V2)
```
Tier Score = 0.75 x normalised_benchmark
           + 0.15 x normalised_vram       (capped at 16 GB)
           + 0.10 x normalised_recency    (year 2000 baseline)
```

### Pre-conditions for V2
1. Apply gaming-GPU filter (remove non-gaming entries)
2. Impute VRAM from GPU name string before scoring
3. Store `v1_tier` alongside `v2_tier` for A/B comparison
4. Only promote V2 to production after manual spot-check of 50+ GPUs

### Risk Table

| Risk | Severity | Mitigation |
|---|---|---|
| 75% VRAM missing zeros the VRAM term for most GPUs | High | Regex-impute from name |
| Year component penalises capable older GPUs | Medium | Lower recency weight (10%) |
| Workstation GPUs inflate VRAM component | High | Pre-filter before scoring |
| Compound normalisation errors | Low | Unit-test boundary cases |

---

## 6. Files Generated by This Audit

| File | Description |
|---|---|
| `gpu_non_gaming_report.csv` | All flagged non-gaming / professional GPUs |
| `gpu_missing_vram.csv` | GPUs without VRAM data, sorted by benchmark |
| `gpu_missing_release_year.csv` | GPUs without release year |
| `gpu_validation_report.md` | This report |

---

*RigCheck GPU Tier Engine V2 — Ready for gaming-filter cleanup before CPU
tier architecture clone.*
"""

    out_path = GPU_DIR / "gpu_validation_report.md"
    out_path.write_text(report, encoding="utf-8")
    print("\n" + "=" * 66)
    print("  TASK 7 — VALIDATION REPORT WRITTEN")
    print("=" * 66)
    print(f"  Saved: gpu_validation_report.md")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    print("\n" + "#" * 66)
    print("  RigCheck GPU Tier Engine V2 — Validation & Quality Audit")
    print("#" * 66)

    master = load_master()
    tiers  = load_tiers()

    stats      = task1_master_validation(master)
    non_gaming = task2_non_gaming_filter(master)
    task3_vram_coverage(master)
    task4_release_year(master)
    issues, _  = task5_tier_quality(master, tiers)
    v2_analysis = task6_v2_formula()
    task7_write_report(stats, non_gaming, master, tiers, issues, v2_analysis)

    print("\n" + "#" * 66)
    print("  Audit complete. Output files:")
    print("    gpu_non_gaming_report.csv")
    print("    gpu_missing_vram.csv")
    print("    gpu_missing_release_year.csv")
    print("    gpu_validation_report.md")
    print("#" * 66 + "\n")


if __name__ == "__main__":
    main()
