import json

def analyze():
    with open("eval_phase4.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        
    metrics = data.pop("_metrics")
    
    total = len(data)
    retrieved = 0
    top_1 = 0
    top_3 = 0
    top_5 = 0
    
    # We only compute success rates for queries that have a TARGET defined
    queries_with_targets = 0
    failures = []
    
    for name, result in data.items():
        if result.get("target"):
            queries_with_targets += 1
            if result.get("target_retrieved"):
                retrieved += 1
            
            final_rank = result.get("target_final_rank")
            if final_rank:
                if final_rank == 1:
                    top_1 += 1
                if final_rank <= 3:
                    top_3 += 1
                if final_rank <= 5:
                    top_5 += 1
            
            if not final_rank or final_rank > 3:
                failures.append({
                    "name": name,
                    "query": result["query"],
                    "target": result["target"],
                    "retrieved": result.get("target_retrieved"),
                    "rank": final_rank,
                    "top_10": result["top_10"]
                })
                
    print(f"Total Queries Tested: {total}")
    print(f"Queries with explicit targets: {queries_with_targets}")
    print(f"Retrieval Success: {retrieved}/{queries_with_targets} ({(retrieved/queries_with_targets)*100:.1f}%)")
    print(f"Top 1 Success: {top_1}/{queries_with_targets} ({(top_1/queries_with_targets)*100:.1f}%)")
    print(f"Top 3 Success: {top_3}/{queries_with_targets} ({(top_3/queries_with_targets)*100:.1f}%)")
    print(f"Top 5 Success: {top_5}/{queries_with_targets} ({(top_5/queries_with_targets)*100:.1f}%)")
    print(f"Average Latency: {metrics['avg_latency']*1000:.1f}ms")
    print(f"P95 Latency: {metrics['p95_latency']*1000:.1f}ms")
    
    print("\n--- FAILURES / TAXONOMY ---")
    for f in failures:
        print(f"[{f['name']}] '{f['query']}'")
        print(f"  Target: {f['target']} (Retrieved: {f['retrieved']}) -> Rank: {f['rank']}")
        print(f"  Top 5: {f['top_10'][:5]}")

if __name__ == "__main__":
    analyze()
