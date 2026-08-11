from model.rigcheck_engine import run_vibe_check, clean_and_expand_input, rerank_candidates
import pandas as pd

def test_vibe():
    cleaned = clean_and_expand_input('An action-packed co-op shooter where my friends and I plan and execute bank heists.')
    vibe_results = run_vibe_check(cleaned, top_n=50)
    
    # Run the reranker exactly as the engine does
    vibe_results = rerank_candidates(vibe_results, cleaned)
    
    top_score = vibe_results.iloc[0]["Vibe_Score"]
    dynamic_threshold = top_score * 0.45
    
    print("Top Score:", top_score)
    print("Dynamic Threshold:", dynamic_threshold)
    
    for _, row in vibe_results.head(10).iterrows():
        status = "PASS" if row["Vibe_Score"] >= dynamic_threshold else "FAIL"
        print(f"[{status}] {row['Title']}: {row['Vibe_Score']:.2f}")

    # For Slay the Spire
    print("\n--- SLAY THE SPIRE ---")
    c2 = clean_and_expand_input('A roguelike deckbuilder where I climb a spire, collect cards, and battle monsters.')
    vr2 = run_vibe_check(c2, top_n=50)
    vr2 = rerank_candidates(vr2, c2)
    ts2 = vr2.iloc[0]["Vibe_Score"]
    dt2 = ts2 * 0.45
    print("Top Score:", ts2, "Threshold:", dt2)
    for _, row in vr2.head(10).iterrows():
        status = "PASS" if row["Vibe_Score"] >= dt2 else "FAIL"
        print(f"[{status}] {row['Title']}: {row['Vibe_Score']:.2f}")

if __name__ == "__main__":
    test_vibe()
