import json
import os

ALIASES = {
    # Red Dead
    "rdr2": "Red Dead Redemption 2",
    "rdr 2": "Red Dead Redemption 2",
    "rdr": "Red Dead Redemption 2",
    
    # GTA
    "gta": "Grand Theft Auto V Legacy",
    "gta v": "Grand Theft Auto V Legacy",
    "gta 5": "Grand Theft Auto V Legacy",
    "gta5": "Grand Theft Auto V Legacy",
    
    # Left 4 Dead
    "l4d2": "Left 4 Dead 2",
    "l4d 2": "Left 4 Dead 2",
    "l4d": "Left 4 Dead",
    
    # Counter-Strike
    "cs2": "Counter-Strike 2",
    "cs 2": "Counter-Strike 2",
    "csgo": "Counter-Strike 2", # CSGO was replaced by CS2
    "cs": "Counter-Strike",
    "css": "Counter-Strike: Source",
    
    # The Last of Us
    "tlou": "The Last of Us™ Part I",
    "tlou 1": "The Last of Us™ Part I",
    "tlou p1": "The Last of Us™ Part I",
    
    # God of War
    "gow": "God of War",
    "god of war 4": "God of War",
    
    # Call of Duty
    "cod": "Call of Duty®",
    "cod mw": "Call of Duty® 4: Modern Warfare® (2007)",
    "cod mw2": "Call of Duty®: Modern Warfare® 2 (2009)",
    "cod bo": "Call of Duty®: Black Ops Cold War",
    "cod bocw": "Call of Duty®: Black Ops Cold War",
    
    # Other common aliases in dataset
    "skyrim": "The Elder Scrolls V: Skyrim",
    "tesv": "The Elder Scrolls V: Skyrim",
    "tes v": "The Elder Scrolls V: Skyrim",
    "ff14": "FINAL FANTASY XIV Online",
    "ffxiv": "FINAL FANTASY XIV Online",
    "pubg": "PUBG: BATTLEGROUNDS",
    "r6s": "Tom Clancy's Rainbow Six® Siege",
    "r6 siege": "Tom Clancy's Rainbow Six® Siege",
    "siege": "Tom Clancy's Rainbow Six® Siege",
    "witcher 3": "The Witcher® 3: Wild Hunt",
    "tw3": "The Witcher® 3: Wild Hunt"
}

def generate_aliases():
    db_path = "data/games_database_final.json"
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    with open(db_path, "r", encoding="utf-8") as f:
        games = json.load(f)

    valid_titles = {g.get("name") for g in games if g.get("name")}
    
    validated_aliases = {}
    
    for alias, canonical in ALIASES.items():
        if canonical in valid_titles:
            validated_aliases[alias] = canonical
        else:
            print(f"WARNING: Canonical title '{canonical}' for alias '{alias}' not found in database. Skipping.")

    # Sort aliases by length descending so that "gta v" matches before "gta"
    sorted_aliases = {k: v for k, v in sorted(validated_aliases.items(), key=lambda item: len(item[0]), reverse=True)}

    out_path = "data/game_aliases.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(sorted_aliases, f, indent=4)
        
    print(f"Generated search aliases for {len(sorted_aliases)} acronyms.")
    print(f"Saved to {out_path}")

if __name__ == "__main__":
    generate_aliases()
