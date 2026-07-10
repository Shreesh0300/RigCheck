import pandas as pd

df = pd.read_csv("gpu/gpu_master.csv").sort_values("benchmark_score", ascending=False).reset_index(drop=True)
total = len(df)

# Known PassMark G3Dmark scores for Intel Core Ultra 5 variants
candidates = {
    "Core Ultra 5 120U  (Arc iGPU, low power)": 3500,
    "Core Ultra 5 125H  (Arc iGPU, standard) ": 4800,
    "Core Ultra 5 135H  (Arc iGPU, high perf)": 5200,
    "Core Ultra 5 226V  (Arc 140V, Lunar Lake)": 7200,
    "Core Ultra 5 238V  (Arc 140V, top Lunar)": 7800,
}

def get_tier(pct):
    if pct >= 90: return "S"
    if pct >= 70: return "A"
    if pct >= 40: return "B"
    if pct >= 15: return "C"
    return "D"

# find nearest neighbours in dataset
def neighbours(score, n=3):
    above = df[df["benchmark_score"] > score].tail(n)
    below = df[df["benchmark_score"] <= score].head(n)
    return pd.concat([above, below])

print(f"Dataset: {total} GPUs\n")
print(f"{'Intel GPU Variant':<44} {'Score':>6}  {'Rank':>5}  {'%ile':>6}  {'Tier':>4}")
print("-" * 72)

for name, score in candidates.items():
    rank = int((df["benchmark_score"] > score).sum()) + 1
    pct  = (1 - rank / total) * 100
    tier = get_tier(pct)
    print(f"{name:<44} {score:>6,}  #{rank:<5}  {pct:>5.1f}%  {tier:>4}")

print()
print("-" * 72)
print("Nearest neighbours in dataset (for Core Ultra 5 125H @ 4,800):\n")
nb = neighbours(4800)
nb = nb.sort_values("benchmark_score", ascending=False)
for _, r in nb.iterrows():
    rank_n = int((df["benchmark_score"] > r["benchmark_score"]).sum()) + 1
    pct_n  = (1 - rank_n / total) * 100
    print(f"  #{rank_n:<5} {r['gpu_name']:<35} {int(r['benchmark_score']):>7,}  ({pct_n:.1f}%ile)")
