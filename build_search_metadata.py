import json
import os

# Deterministic mappings from keywords found in description -> Searchable concepts
KEYWORD_MAPPINGS = {
    # Themes / Settings
    "post-apocalyptic": ["post apocalyptic survival"],
    "mutant": ["mutants", "post apocalyptic"],
    "space": ["space exploration"],
    "ninja": ["samurai stealth", "feudal japan"],
    "samurai": ["samurai stealth", "feudal japan"],
    "pirate": ["pirate game", "naval"],
    "submarine": ["WW2 submarine", "naval"],
    "zombie": ["zombie survival", "horror"],
    "cowboy": ["western cowboy", "wild west"],
    "western": ["western cowboy", "wild west"],
    "medieval": ["medieval RPG"],
    
    # Gameplay
    "stealth": ["stealth"],
    "racing": ["racing"],
    "driving": ["racing", "driving"],
    "heist": ["heist", "crime"],
    "deckbuilder": ["deckbuilder"],
    "factory": ["factory automation", "building"]
}

# Manual overrides for games that completely lack keywords in their official text
MANUAL_OVERRIDES = {
    "Red Dead Redemption 2": [
        "western cowboy open world", 
        "wild west", 
        "horseback adventure",
        "late 1800s",
        "cowboy",
        "western"
    ],
    "UBOAT": [
        "WWII submarine simulator",
        "WW2 submarine",
        "naval combat"
    ],
    "Sekiro™: Shadows Die Twice - GOTY Edition": [
        "stealth ninja",
        "feudal japan",
        "samurai stealth"
    ],
    "Subnautica": [
        "survival crafting",
        "open world survival"
    ],
    "Factorio": [
        "factory automation",
        "base building"
    ],
    "Cities: Skylines": [
        "city builder",
        "strategy game about building a city"
    ],
    "Forza Horizon 5": [
        "open world racing",
        "realistic racing game"
    ],
    "Left 4 Dead 2": [
        "zombie co op survival",
        "survival horror game with zombies"
    ]
}

def generate_metadata():
    db_path = "data/games_database_final.json"
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    with open(db_path, "r", encoding="utf-8") as f:
        games = json.load(f)

    search_metadata = {}

    for game in games:
        title = game.get("name")
        if not title:
            continue
            
        about = str(game.get("about_the_game", "")).lower()
        metadata_concepts = set()
        
        # 1. Deterministic Extraction
        for kw, concepts in KEYWORD_MAPPINGS.items():
            if kw in about:
                metadata_concepts.update(concepts)
                
        # 2. Manual Overrides
        if title in MANUAL_OVERRIDES:
            metadata_concepts.update(MANUAL_OVERRIDES[title])
            
        if metadata_concepts:
            search_metadata[title] = list(metadata_concepts)

    out_path = "data/search_metadata.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(search_metadata, f, indent=4)
        
    print(f"Generated search metadata for {len(search_metadata)} games.")
    print(f"Saved to {out_path}")

if __name__ == "__main__":
    generate_metadata()
