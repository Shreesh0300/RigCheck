import json
import os
from model.rigcheck_engine import (
    extract_hardware_intent,
    extract_query_concepts,
    detect_query_vagueness,
    clean_and_expand_input,
    recommend_game,
    get_explicit_references
)

categories = {
    "A. Exact game searches": [
        ("payday 2", 10000, "RTX 4070", 16),
        ("left 4 dead 2", 10000, "RTX 4070", 16),
        ("portal 2", 10000, "RTX 4070", 16),
        ("gta 5", 10000, "RTX 4070", 16)
    ],
    "B. Typo correction": [
        ("paydya 2", 10000, "RTX 4070", 16),
        ("left 4 ded 2", 10000, "RTX 4070", 16),
        ("cybeprunk 2077", 10000, "RTX 4070", 16),
        ("red dead redemtion 2", 10000, "RTX 4070", 16)
    ],
    "C. Games-like/reference searches": [
        ("games like gta 5", 10000, "RTX 4070", 16),
        ("games like rdr2", 10000, "RTX 4070", 16),
        ("games like skyrim", 10000, "RTX 4070", 16),
        ("games like fallout", 10000, "RTX 4070", 16),
        ("games like cyberpunk 2077", 10000, "RTX 4070", 16),
        ("games like minecraft", 10000, "RTX 4070", 16)
    ],
    "D. Genre/concept searches": [
        ("open world games", 10000, "RTX 4070", 16),
        ("co-op zombie games", 10000, "RTX 4070", 16),
        ("fun games to play with friends", 10000, "RTX 4070", 16),
        ("good story games", 10000, "RTX 4070", 16),
        ("difficult fantasy games", 10000, "RTX 4070", 16),
        ("multiplayer games", 10000, "RTX 4070", 16)
    ],
    "E. Budget tests": [
        ("good games under 500", 500, "RTX 4070", 16),
        ("cheap games", 500, "RTX 4070", 16),
        ("good game under 300", 300, "RTX 4070", 16)
    ],
    "F. Hardware tests": [
        ("something I can run on my old PC", 10000, "GTX 1050", 8),
        ("a demanding game for my powerful PC", 10000, "RTX 4070", 16),
        ("games for a potato PC", 10000, "GTX 1050", 8),
        ("open world games for my low end PC", 10000, "GTX 1050", 8)
    ],
    "G. Combined constraints": [
        ("cheap open world games for a potato pc", 500, "GTX 1050", 8),
        ("co-op games under 500 for my old PC", 500, "GTX 1050", 8),
        ("good story game under 500 that runs on my PC", 500, "GTX 1050", 8)
    ],
    "H. Vague queries": [
        ("I want something fun", 10000, "RTX 4070", 16),
        ("recommend a good game", 10000, "RTX 4070", 16),
        ("something to play", 10000, "RTX 4070", 16),
        ("I want a fun game with friends", 10000, "RTX 4070", 16)
    ],
    "I. Natural/messy queries": [
        ("i wanna play something chill with my friends", 10000, "RTX 4070", 16),
        ("give me something addictive under 500", 500, "RTX 4070", 16),
        ("i want a game with a really good story", 10000, "RTX 4070", 16),
        ("something like gta but my pc sucks", 10000, "GTX 1050", 8),
        ("me and 3 friends need a game", 10000, "RTX 4070", 16),
        ("i have a 1050 what can i actually run", 10000, "GTX 1050", 8)
    ]
}

with open("benchmark_results.txt", "w", encoding="utf-8") as f:
    for cat_name, queries in categories.items():
        f.write(f"\n{'#'*80}\n# {cat_name}\n{'#'*80}\n")
        for q, budget, gpu, ram in queries:
            f.write(f"\n{'-'*50}\nQUERY: {q} | BUDGET: {budget} | GPU: {gpu} | RAM: {ram}\n{'-'*50}\n")
            
            hw_intent = extract_hardware_intent(q)
            query_concepts = extract_query_concepts(q)
            vague_score, vague_class = detect_query_vagueness(q, query_concepts)
            cleaned = clean_and_expand_input(q)
            explicit_refs = get_explicit_references(q)
            
            f.write(f"Cleaned Intent: {cleaned}\n")
            f.write(f"Explicit Refs: {explicit_refs}\n")
            f.write(f"Detected concepts: {query_concepts}\n")
            f.write(f"Detected HW Intent: {hw_intent}\n")
            f.write(f"Vagueness: {vague_class} ({vague_score})\n")
            
            try:
                res = recommend_game(q, budget=budget, gpu_name=gpu, ram=ram, cpu_name="i5-4460", storage_gb=100)
                winner = res.get('recommended_game')
                conf = res.get('confidence')
                winner_price = res.get('price_inr', 'Unknown')
                
                f.write(f"\nWINNER: {winner} (Conf: {conf}% | Price: {winner_price})\n")
                f.write("Alternatives:\n")
                for alt in res.get("alternative_games", [])[:2]:
                    f.write(f"  - {alt['title']} (Conf: {alt['confidence']}% | Price: {alt.get('price_inr', 'Unknown')})\n")
            except Exception as e:
                f.write(f"Engine Error: {e}\n")

print("Benchmark complete! Wrote to benchmark_results.txt")
