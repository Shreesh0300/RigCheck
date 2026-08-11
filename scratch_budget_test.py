from model.rigcheck_engine import run_rigcheck

def run_test(name, query, budget, expected_result_type="success"):
    print(f"\n=============================================")
    print(f"TEST: {name} (Budget: {budget})")
    print(f"QUERY: {query}")
    print(f"EXPECTED: {expected_result_type}")
    print(f"=============================================")
    
    res = run_rigcheck(
        user_input=query,
        budget=budget,
        user_gpu="GTX 1050",
        user_ram=8,
        user_cpu="AMD Ryzen 9 9950X3D",
        user_storage_gb=498
    )
    
    if res.get("recommended_game"):
        print(f"RESULT: SUCCESS -> {res['recommended_game']} (Price: {res.get('price_inr')})")
    else:
        print(f"RESULT: FAILED -> {res.get('description')}")
        
def main():
    # 1. PAYDAY 2
    run_test(
        name="PAYDAY 2",
        query="An action-packed co-op shooter where my friends and I plan and execute bank heists.",
        budget=500
    )
    
    # 2. Slay the Spire
    run_test(
        name="Slay the Spire",
        query="A roguelike deckbuilder where I climb a spire, collect cards, and battle monsters.",
        budget=1000
    )
    
    # 3. 5 existing correctly-working games
    run_test("RDR2", "I'm looking for a realistic open world western adventure set in the late 1800s.", 4000)
    run_test("Stardew", "A relaxing farming game where I can grow crops, raise animals, and fish.", 1000)
    run_test("Elden Ring", "A challenging soulslike action RPG set in the Lands Between.", 3000)
    run_test("Factorio", "A game about building and automating factories to launch a rocket.", 2000)
    run_test("Hades", "A fast-paced roguelike dungeon crawler based on Greek mythology.", 1500)
    
    # 4. 3 genuinely over-budget games
    run_test("Elden Ring (Too Cheap)", "A challenging soulslike action RPG set in the Lands Between.", 500, expected_result_type="fail")
    run_test("RDR2 (Too Cheap)", "I'm looking for a realistic open world western adventure set in the late 1800s.", 500, expected_result_type="fail")
    run_test("Factorio (Too Cheap)", "A game about building and automating factories to launch a rocket.", 500, expected_result_type="fail")
    
    # 5. 1 Free game
    run_test("CS2 (Free)", "A competitive 5v5 tactical shooter where terrorists and counter-terrorists fight.", 0)
    
    # 6. 1 game with missing price data
    run_test("Rainbow Six Siege (Missing Price)", "Tom Clancy's Rainbow Six Siege is an elite, tactical team-based shooter.", 500, expected_result_type="fail (since missing price = 99999)")
    
if __name__ == "__main__":
    main()
