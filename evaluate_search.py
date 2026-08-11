import time
import json
from model.rigcheck_engine import run_rigcheck, clean_and_expand_input, run_vibe_check

QUERIES = {
    # ---------------------------------------------
    # PHASE 1 & 2 EXISTING SUITE (30 Queries)
    # ---------------------------------------------
    "RDR2_Long": "I’m looking for a realistic open world western adventure set in the late 1800s. I want to play as a cowboy, ride horses across towns and wilderness, rob trains, hunt wildlife, complete story-driven missions, and experience an immersive frontier with gunslinging, outlaws, sheriffs, and a rich cinematic narrative.",
    "RDR2_Short": "western cowboy open world",
    "Submarine_WW2": "WWII submarine simulator",
    "Zombies_Coop": "co-op zombie survival",
    "Zombies_Horror": "survival horror game with zombies",
    "Racing_Realistic": "open world realistic racing game",
    "Stealth_Ninja": "stealth game set in feudal Japan",
    "Space_Trading": "space exploration game with trading",
    "Survival_Crafting": "open world survival game with crafting",
    "RPG_Fantasy": "story driven fantasy RPG",
    "Combat_Sword": "open world game with sword combat",
    "City_Builder": "strategy game about building a city",
    "Heist_Coop": "co-op bank heist shooter",
    "Rogue_Deckbuilder": "roguelike deckbuilder with cards",
    "Factory_Automation": "first person factory building automation",
    "Short_Western_Cowboy": "western cowboy",
    "Short_Open_World_Western": "open world western",
    "Short_Zombie_Coop": "zombie co op",
    "Short_WW2_Submarine": "WW2 submarine",
    "Short_Samurai_Stealth": "samurai stealth",
    "Short_Pirate_Game": "pirate game",
    "Short_Space_Trading": "space trading",
    "Short_Medieval_RPG": "medieval RPG",
    "Short_Open_World_Racing": "open world racing",
    "Short_Survival_Crafting": "survival crafting",
    "Short_Detective_Game": "detective game",
    "Short_Superhero_Open_World": "superhero open world",
    "Short_Post_Apocalyptic": "post apocalyptic survival",
    "Short_Horror_Coop": "horror co op",
    "Short_Horseback": "horseback adventure",

    # ---------------------------------------------
    # PHASE 3 EXPANDED REAL-WORLD SUITE (50+ Queries)
    # ---------------------------------------------
    # A. SIMPLE QUERIES
    "Simple_Western": "western",
    "Simple_Samurai": "samurai",
    "Simple_Zombies": "zombies",
    "Simple_Racing": "racing",
    "Simple_Space": "space",
    "Simple_Pirates": "pirates",
    "Simple_Cowboy": "cowboy",
    "Simple_Horror": "horror",
    "Simple_Survival": "survival",
    "Simple_Detective": "detective",
    
    # B. NATURAL QUERIES
    "Natural_Cowboy": "i want a cowboy game",
    "Natural_ZombieCoop": "good zombie coop",
    "Natural_Samurai": "game where you play as a samurai",
    "Natural_Driving": "open world driving game",
    "Natural_HorrorFriends": "something scary to play with friends",
    "Natural_Submarine": "ww2 submarine game",
    "Natural_RPG": "rpg with swords and magic",
    "Natural_Pirate": "game where i sail as a pirate",
    "Natural_Detective": "mystery game where i play as a detective",
    "Natural_Space": "explore space in a ship",
    
    # C. CASUAL / MESSY QUERIES
    "Messy_Cowboy": "bro give me a cowboy game",
    "Messy_RDR2": "something like rdr2",
    "Messy_Detective": "i wanna play as a detective",
    "Messy_ZombieBase": "game where i can build a base and survive zombies",
    "Messy_Chill": "something chill where i can explore",
    "Messy_Scary": "scary game plz",
    "Messy_Racing": "driving fast cars open world",
    "Messy_Space": "spaceship game",
    "Messy_Submarine": "game where u drive a submarine",
    "Messy_Samurai": "ninja or samurai stealth stuff",
    
    # D. MULTI-CONSTRAINT QUERIES
    "Multi_ZombieBase": "open world zombie survival with base building",
    "Multi_WesternHorses": "western cowboy game with horses",
    "Multi_CoopHorror": "co-op horror game with zombies",
    "Multi_OpenRacing": "open world racing game",
    "Multi_StealthSamurai": "stealth samurai game",
    "Multi_SpaceTrade": "space exploration with trading",
    "Multi_PirateShip": "open world pirate ship game",
    "Multi_DetectiveNoir": "noir detective mystery",
    "Multi_MedievalSword": "medieval sword fighting rpg",
    "Multi_PostApocSurv": "post apocalyptic survival crafting",
    
    # E. VAGUE QUERIES
    "Vague_Scary": "something scary",
    "Vague_Friends": "something fun with friends",
    "Vague_Story": "good story game",
    "Vague_OpenWorld": "open world game",
    "Vague_Survival": "survival game",
    "Vague_Action": "action game",
    "Vague_Strategy": "strategy game",
    "Vague_Shooter": "good shooter",
    "Vague_Relaxing": "relaxing game",
    "Vague_Coop": "coop game",

    # ---------------------------------------------
    # PHASE 4 ALIAS TESTS
    # ---------------------------------------------
    "Alias_rdr2_1": "rdr2",
    "Alias_RDR2_2": "RDR2",
    "Alias_rdr_2": "rdr 2",
    "Alias_gta": "gta",
    "Alias_gta_5": "gta 5",
    "Alias_gta_v": "gta v",
    "Alias_l4d2": "l4d2",
    "Alias_cs2": "cs2",
    "Alias_tlou": "tlou",
    
    # Context Tests
    "Context_gta_5": "games similar to gta 5",
    "Context_rdr2_1": "open world games like rdr2",
    "Context_rdr2_2": "rdr2 style western game",
    "Context_l4d2": "games like l4d2",
    "Context_cs2": "something like cs2 but tactical"
}

# The expected targets we want to measure retrieval for
TARGETS = {
    # Phase 1 & 2 Targets
    "RDR2_Long": "Red Dead Redemption 2",
    "RDR2_Short": "Red Dead Redemption 2",
    "Short_Western_Cowboy": "Red Dead Redemption 2",
    "Short_Open_World_Western": "Red Dead Redemption 2",
    "Short_Samurai_Stealth": "Sekiro™: Shadows Die Twice - GOTY Edition",
    "Stealth_Ninja": "Sekiro™: Shadows Die Twice - GOTY Edition",
    "Submarine_WW2": "UBOAT",
    "Short_WW2_Submarine": "UBOAT",
    "Short_Horseback": "Red Dead Redemption 2",
    
    # Phase 3 Targets (Representative mappings to verify retrieval)
    "Simple_Western": "Red Dead Redemption 2",
    "Simple_Cowboy": "Red Dead Redemption 2",
    "Simple_Samurai": "Sekiro™: Shadows Die Twice - GOTY Edition",
    "Natural_Cowboy": "Red Dead Redemption 2",
    "Natural_Samurai": "Sekiro™: Shadows Die Twice - GOTY Edition",
    "Natural_Submarine": "UBOAT",
    "Messy_Cowboy": "Red Dead Redemption 2",
    "Messy_RDR2": "Red Dead Redemption 2",
    "Messy_Submarine": "UBOAT",
    "Messy_Samurai": "Sekiro™: Shadows Die Twice - GOTY Edition",
    "Multi_WesternHorses": "Red Dead Redemption 2",
    "Multi_StealthSamurai": "Sekiro™: Shadows Die Twice - GOTY Edition",
    
    "Alias_rdr2_1": "Red Dead Redemption 2",
    "Alias_RDR2_2": "Red Dead Redemption 2",
    "Alias_rdr_2": "Red Dead Redemption 2",
    "Alias_gta": "Grand Theft Auto V Legacy",
    "Alias_gta_5": "Grand Theft Auto V Legacy",
    "Alias_gta_v": "Grand Theft Auto V Legacy",
    "Alias_l4d2": "Left 4 Dead 2",
    "Alias_cs2": "Counter-Strike 2",
    "Alias_tlou": "The Last of Us™ Part I",
    
    "Context_gta_5": "Grand Theft Auto V Legacy",
    "Context_rdr2_1": "Red Dead Redemption 2",
    "Context_rdr2_2": "Red Dead Redemption 2",
    "Context_l4d2": "Left 4 Dead 2",
    "Context_cs2": "Counter-Strike 2"
}

def evaluate(output_file: str):
    results = {}
    total_time = 0
    total_bm25_time = 0
    
    print(f"Running {len(QUERIES)} queries...")
    for name, query in QUERIES.items():
        start_time = time.time()
        
        # 1. Measure BM25 retrieval directly
        bm25_start = time.time()
        cleaned_vibe = clean_and_expand_input(query)
        vibe_results = run_vibe_check(cleaned_vibe, top_n=50)
        bm25_latency = time.time() - bm25_start
        total_bm25_time += bm25_latency
        
        retrieved_titles = vibe_results["Title"].tolist() if not vibe_results.empty else []
        
        target = TARGETS.get(name)
        target_retrieved = False
        target_candidate_rank = -1
        
        if target:
            target_retrieved = any(target.lower() in str(t).lower() for t in retrieved_titles)
            if target_retrieved:
                for i, t in enumerate(retrieved_titles):
                    if target.lower() in str(t).lower():
                        target_candidate_rank = i + 1
                        break
            
        # 2. Measure full pipeline
        try:
            res = run_rigcheck(
                user_input=query,
                budget=100000,
                user_gpu="RTX 4090",
                user_ram=128,
                user_cpu="Core i9",
                user_storage_gb=5000
            )
            
            top_10 = []
            if res.get("recommended_game"):
                top_10.append(res["recommended_game"])
            if res.get("alternative_games"):
                for alt in res["alternative_games"][:9]:
                    top_10.append(alt["title"])
                    
        except Exception as e:
            top_10 = [f"ERROR: {str(e)}"]
            
        latency = time.time() - start_time
        total_time += latency
        
        target_final_rank = -1
        if target and top_10:
            for i, t in enumerate(top_10):
                if target.lower() in str(t).lower():
                    target_final_rank = i + 1
                    break
        
        results[name] = {
            "query": query,
            "target": target,
            "target_retrieved": target_retrieved if target else None,
            "target_candidate_rank": target_candidate_rank if target_candidate_rank > 0 else None,
            "target_final_rank": target_final_rank if target_final_rank > 0 else None,
            "top_10": top_10,
            "latency": latency,
            "bm25_latency": bm25_latency
        }
        
    avg_latency = total_time / len(QUERIES)
    avg_bm25_latency = total_bm25_time / len(QUERIES)
    
    # Calculate Latencies
    all_latencies = sorted([v["latency"] for v in results.values() if isinstance(v, dict) and "latency" in v])
    p95_latency = all_latencies[int(len(all_latencies) * 0.95)] if all_latencies else 0
    
    results["_metrics"] = {
        "avg_latency": avg_latency,
        "avg_bm25_latency": avg_bm25_latency,
        "p95_latency": p95_latency,
        "total_time": total_time,
        "total_queries": len(QUERIES)
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)
        
    print(f"Evaluation complete. Avg latency: {avg_latency*1000:.1f}ms, P95 latency: {p95_latency*1000:.1f}ms")
    print(f"Results saved to {output_file}")

if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "eval_results.json"
    evaluate(out)
