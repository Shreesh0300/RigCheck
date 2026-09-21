import json
import os
from model.rigcheck_engine import (
    extract_hardware_intent,
    extract_query_concepts,
    detect_query_vagueness,
    clean_and_expand_input,
    run_vibe_check,
    rerank_candidates,
    recommend_game,
    get_explicit_references
)

queries = [
    "games like gta 5",
    "games like rdr2",
    "games like skyrim",
    "games like fallout",
    "games like cybeprunk 2077",
    "gta 5",
    "payday 2",
    "open world games",
    "co-op zombie games",
    "good story games",
    "cheap open world games for a potato pc",
    "games like minecraft",
]

for q in queries:
    print(f"\n{'='*50}\nQUERY: {q}\n{'='*50}")
    
    # 1. Pipeline extraction
    hw_intent = extract_hardware_intent(q)
    query_concepts = extract_query_concepts(q)
    vague_score, vague_class = detect_query_vagueness(q, query_concepts)
    cleaned = clean_and_expand_input(q)
    
    explicit_refs = get_explicit_references(q)
    
    print(f"Cleaned Intent: {cleaned}")
    print(f"Explicit Refs: {explicit_refs}")
    print(f"Detected concepts: {query_concepts}")
    print(f"Detected HW Intent: {hw_intent}")
    print(f"Vagueness: {vague_class} ({vague_score})")
    
    # 2. Final Output from Engine
    try:
        res = recommend_game(q, budget=10000, gpu_name="GTX 1050 Ti", ram=8, cpu_name="i5-4460", storage_gb=100)
        
        print(f"\nWINNER: {res.get('recommended_game')} (Conf: {res.get('confidence')}%)")
        print("Alternatives:")
        for alt in res.get("alternative_games", [])[:2]:
            print(f"  - {alt['title']} (Conf: {alt['confidence']}%)")
    except Exception as e:
        print(f"Engine Error: {e}")
