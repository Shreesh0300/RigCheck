import pandas as pd, json

df = pd.read_csv("gpu/gpu_master.csv")
with open("gpu/gpu_lookup.json") as f:
    lookup = json.load(f)

print(f"Total GPUs in gpu_master.csv: {len(df)}")
print(f"Total entries in gpu_lookup.json: {len(lookup)}")
print()

targets = [
    "RTX 4070", "RTX 4080", "RTX 4090",
    "RTX 5070", "RTX 5080", "RTX 5090",
    "RX 7900 XTX", "RX 7600",
    "RX 9070 XT", "RX 9060",
    "Arc B580", "Arc A770",
    "RTX 4060 Ti",
]

print(f"{'GPU':<30} {'Score':>8} {'Tier':>5} {'Year':>6}")
print("-" * 55)
for t in targets:
    rows = df[df["gpu_name"].str.contains(t, case=False, na=False)]
    if len(rows) > 0:
        r = rows.iloc[0]
        # find tier from lookup
        key = r["gpu_name"]
        tier = lookup.get(key, {}).get("tier", "?")
        year = int(r["release_year"]) if not pd.isna(r.get("release_year")) else "?"
        print(f"  OK  {t:<26} {int(r['benchmark_score']):>8,} {tier:>5} {year:>6}")
    else:
        print(f"  MISSING: {t}")
