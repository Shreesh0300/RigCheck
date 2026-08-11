import json

def diagnose():
    with open('data/games_database_final.json', 'r', encoding='utf-8') as f:
        games = json.load(f)
        
    print(f"Total Games Loaded: {len(games)}")
    
    payday2 = next((g for g in games if g.get("name") == "PAYDAY 2"), None)
    sts = next((g for g in games if g.get("name") == "Slay the Spire"), None)
    
    for label, game in [("PAYDAY 2", payday2), ("Slay the Spire", sts)]:
        if game:
            print(f"\n--- {label} ---")
            print(f"App ID: {game.get('steam_appid')}")
            print(f"Title: {game.get('name')}")
            print(f"Is Free: {game.get('is_free')}")
            print(f"Price_Overview: {game.get('price_overview')}")
        else:
            print(f"\n{label} NOT FOUND!")
            
    # Check all 500 games
    valid = 0
    missing = 0
    nan_count = 0
    free_count = 0
    suspicious = 0
    currencies = set()
    
    for g in games:
        if g.get("is_free"):
            free_count += 1
            continue
            
        po = g.get("price_overview")
        if not po:
            missing += 1
            continue
            
        curr = po.get("currency")
        final = po.get("final")
        
        currencies.add(curr)
        valid += 1
        
        if final is None or final != final: # NaN check (though json doesn't typically have nan)
            nan_count += 1
            continue
            
        if not isinstance(final, (int, float)):
            print(f"String price found: {g['name']} - {final}")
            
        if final < 0:
            suspicious += 1
            print(f"Negative price found: {g['name']} - {final}")
            
        if final == 0 and not g.get("is_free"):
            suspicious += 1
            
        if final > 5000000: # Over 50k INR is probably suspicious
            suspicious += 1
            
    print(f"\n--- ALL 500 GAMES ---")
    print(f"Total games: {len(games)}")
    print(f"Free games: {free_count}")
    print(f"Valid prices: {valid}")
    print(f"Missing prices: {missing}")
    print(f"NaN/Null: {nan_count}")
    print(f"Suspicious: {suspicious}")
    print(f"Currencies: {currencies}")

if __name__ == '__main__':
    diagnose()
