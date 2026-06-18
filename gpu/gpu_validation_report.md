# RigCheck GPU Tier Engine — Validation Report V2

*Generated automatically by `validate_gpu_tiers.py`*

---

## 1. Dataset Health Summary

| Metric | Value |
|---|---|
| Total GPU rows | 2270 |
| Unique GPU names | 2270 |
| Duplicate rows | 0 |
| Missing VRAM | 1712/2270 (75.4%) |
| Missing Release Year | 0/2270 (0.0%) |
| Missing API Score | 1635/2270 (72.0%) |
| Missing Manufacturer | 216/2270 (9.5%) |

> **Note:** `release_year` is sourced from `GPU_benchmarks_v7.csv testDate`
> which covers 100% of rows. Any missing values are entries where the
> test date field was blank in the source.

---

## 2. Missing Data Analysis

### VRAM
- **1712/2270 (75.4%)** GPUs are missing VRAM data.
- Root cause: `All_GPUs.csv` uses a multiline CSV format that is difficult
  to parse cleanly with `pd.read_csv`. Only rows that survived parsing and
  matched on `gpu_name` received VRAM values.
- **Recommended fix:** Regex-extract GB value from the `gpu_name` string
  itself (e.g. `"GTX 1080 11GB"`) and from `All_GPUs.csv` using a custom
  multiline parser.

### Release Year
- **0/2270 (0.0%)** GPUs are missing release year.
- Most zeros come from GRID/Virtual entries which have no commercial release.

### API Score
- **1635/2270 (72.0%)** GPUs are missing a composite API score.
- `GPU_scores_graphicsAPIs.csv` only covers 1,213 GPU variants.
  Most legacy and mobile GPUs are absent.

---

## 3. Gaming vs Non-Gaming GPU Analysis

| Category | Count | Percentage |
|---|---|---|
| Estimated gaming GPUs | 1796 | 79.1% |
| Non-gaming / professional / datacenter | 474 | 20.9% |

### Non-Gaming Breakdown

| Category | Count |
|---|---|
| Professional/Quadro | 264 |
| Embedded/ISV | 81 |
| Integrated/Legacy | 70 |
| GRID/Virtual | 23 |
| Datacenter/Tesla | 17 |
| Other-Professional | 6 |
| Mobile SoC | 6 |
| Mining/Compute | 3 |
| TITAN Compute | 2 |
| Junk/Unknown | 2 |

> **Action required:** Before V2 release, apply the gaming-GPU filter
> (see `gpu_non_gaming_report.csv`) to strip non-gaming entries from
> the tier files. This will make tier percentiles more meaningful for
> RigCheck's target audience.

---

## 4. Tier Quality Assessment

### Tier Distribution

| Tier | GPU Count | % of Total |
|---|---|---|
| S | 228 | 10.0% |
| A | 454 | 20.0% |
| B | 681 | 30.0% |
| C | 568 | 25.0% |
| D | 339 | 14.9% |

### Top 10 per Tier

#### Tier S

| GPU Name | Benchmark Score | Manufacturer |
|---|---|---|
| RTX 3090 Ti | 29094 | NVIDIA |
| RTX 3080 Ti | 26887 | NVIDIA |
| RTX 3090 | 26395 | NVIDIA |
| RX 6900 XT | 25458 | AMD |
| RTX 3080 | 24853 | NVIDIA |
| RTX 3070 Ti | 23367 | NVIDIA |
| RX 6800 XT | 23364 | AMD |
| RTX A5000 | 22867 | NVIDIA |
| RTX A6000 | 22122 | NVIDIA |
| RTX 3070 | 22093 | NVIDIA |

#### Tier A

| GPU Name | Benchmark Score | Manufacturer |
|---|---|---|
| A16 | 5797 | Unknown |
| Quadro K5200 | 5780 | NVIDIA |
| GTX 970M | 5761 | NVIDIA |
| Pro WX 7130 | 5722 | AMD |
| Quadro M3000M | 5678 | NVIDIA |
| Tesla K20m | 5675 | NVIDIA |
| R9 280 | 5668 | AMD |
| GTX 690 | 5654 | NVIDIA |
| A40 12Q | 5573 | Unknown |
| HD 7990 | 5566 | AMD |

#### Tier B

| GPU Name | Benchmark Score | Manufacturer |
|---|---|---|
| Ryzen 3 5300G | 1406 | AMD |
| GTX 275 | 1401 | NVIDIA |
| 540X | 1398 | AMD |
| HD 4870 | 1391 | AMD |
| HD 7560D + HD 7670 Dual | 1380 | AMD |
| R7 PRO A12 8870 | 1376 | AMD |
| R9 M370X | 1374 | AMD |
| HD 7850M | 1373 | AMD |
| FirePro M40003 | 1364 | AMD |
| HD 8670D + 6670 Dual | 1361 | AMD |

#### Tier C

| GPU Name | Benchmark Score | Manufacturer |
|---|---|---|
| 710M | 450 | NVIDIA |
| Qualcomm Adreno 680 GPU | 449 | Qualcomm |
| HD 7640G | 448 | AMD |
| HD 7520G + HD 7600M Dual | 447 | AMD |
| HD 7660G + 8600M Dual | 446 | AMD |
| PHDGD Ivy 5 | 445 | Unknown |
| HD 7570M | 445 | AMD |
| GT 320 | 444 | NVIDIA |
| GT 710M | 444 | NVIDIA |
| HD 7620G + HD 8600M Dual | 443 | AMD |

#### Tier D

| GPU Name | Benchmark Score | Manufacturer |
|---|---|---|
| Express Chipset G41 | 57 | Intel |
| G41 Express Chipsatz | 57 | Intel |
| Q45/Q43 Express Chipsatz | 57 | Intel |
| 9800 XT | 57 | AMD |
| X600 256MB HyperMemory | 57 | AMD |
| X550XT | 56 | AMD |
| 9700 PRO | 54 | AMD |
| FireGL V3100 | 53 | Unknown |
| 7100 GS | 52 | NVIDIA |
| Go 7300 | 52 | NVIDIA |

### Detected Issues

- **[ISSUE]** 49 workstation/datacenter GPUs in S-Tier:
Quadro RTX 6000 (score=19692)
Quadro RTX 8000 (score=19126)
Quadro GV100 (score=17675)
Quadro RTX 5000 (score=16260)
Tesla V100 SXM2 16GB (score=16235)
Quadro GP100 (score=16203)
Quadro P6000 (score=15811)
Quadro RTX 4000 (score=15515)
Quadro RTX 5000 (Mobile) (score=14832)
Quadro RTX 5000 with Max Q Design (score=13893)
Quadro RTX 4000 with Max Q Design (score=13622)
Tesla T10 (score=13264)
Quadro RTX 4000 (Mobile) (score=13008)
Quadro P5200 with Max Q Design (score=12323)
Quadro M6000 24GB (score=12264)
Quadro P5200 (score=12144)
Quadro P5000 (score=11976)
Quadro P4200 with Max Q Design (score=11869)
Tesla M40 24GB (score=11658)
Quadro P4000 (score=11422)
Quadro M6000 (score=11397)
Quadro RTX 3000 (score=11122)
Tesla T4 (score=11113)
Tesla M40 (score=10117)
Quadro P4200 (score=9827)
Quadro P2200 (score=9486)
Quadro M5000 (score=9262)
Quadro P3200 with Max Q Design (score=9242)
Quadro P4000 with Max Q Design (score=9083)
Quadro RTX 3000 with Max Q Design (score=8754)
Quadro P3200 (score=8663)
Quadro K6000 (score=8108)
Quadro M5500 (score=7915)
Tesla M60 (score=7771)
FirePro W9100 (score=7719)
Tesla M6 (score=7509)
FirePro W8100 (score=7327)
Tesla P100 PCIE 16GB (score=7225)
Quadro T2000 (score=7169)
Quadro P2000 (score=7096)
Quadro T2000 with Max Q Design (score=6871)
Quadro M5000M (score=6807)
Quadro M4000 (score=6644)
Quadro T1000 with Max Q Design (score=6589)
Quadro P3000 (score=6572)
Quadro M4000M (score=6530)
Quadro T1000 (score=6513)
FirePro S7150 (score=6276)
FirePro W9000 (score=6138)
- **[ISSUE]** 32 pre-2010 GPUs ranked B-tier or above:
GTX 285 (score=1550, year=2009, tier=A)
FirePro 3D V8750 (score=1272, year=2009, tier=B)
Quadro FX 5800 (score=1248, year=2009, tier=B)
GTX 295 (score=1171, year=2009, tier=B)
Quadro CX (score=947, year=2009, tier=B)
Mobility Radeon HD 4850 (score=866, year=2009, tier=B)
HD 3850 X2 (score=822, year=2009, tier=B)
9800 GX2 (score=798, year=2009, tier=B)
Quadro FX 3800 (score=780, year=2009, tier=B)
9800 GTX (score=769, year=2009, tier=B)
- **[ISSUE]** 77 integrated/mobile SoCs in S/A tier:
Ryzen 7 5800HS with Radeon (score=7391, tier=S)
Ryzen 7 4800HS with Radeon (score=6999, tier=S)
Ryzen 9 5900HS with Radeon (score=5049, tier=A)
Ryzen 9 5900HX with Radeon (score=2968, tier=A)
Ryzen 7 PRO 4700G with Radeon (score=2880, tier=A)

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
