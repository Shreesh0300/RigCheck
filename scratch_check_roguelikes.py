import json

try:
    with open("data/games_database_final.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    roguelike_games = []
    
    for game in data:
        tags = []
        if isinstance(game.get('genres'), list):
            for g in game['genres']:
                if isinstance(g, dict):
                    tags.append(g.get('description', '').lower())
                elif isinstance(g, str):
                    tags.append(g.lower())
        
        if isinstance(game.get('categories'), list):
            for c in game['categories']:
                if isinstance(c, dict):
                    tags.append(c.get('description', '').lower())
                elif isinstance(c, str):
                    tags.append(c.lower())
        
        # also check short description and name just in case
        desc = game.get('short_description', '').lower()
        name = game.get('name', '').lower()
        
        is_rogue = False
        for tag in tags:
            if 'rogue' in tag or 'loop' in tag:
                is_rogue = True
                break
                
        if is_rogue or 'roguelike' in desc or 'rogue-lite' in desc or 'loop' in desc:
            roguelike_games.append(game.get('name'))
            
    print(f"Found {len(roguelike_games)} games matching 'Roguelike' or 'Loop' out of {len(data)} total games.")
    print("Examples:")
    for name in roguelike_games[:15]:
        print(f" - {name}")
except Exception as e:
    print(f"Error: {e}")
