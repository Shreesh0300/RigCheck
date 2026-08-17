import os, sys, json, time, requests
from expand_database import parse_game_from_steam

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')

CURATED = [
    "God of War", "Horizon Zero Dawn", "Horizon Forbidden West", "Marvel's Spider-Man Remastered", 
    "Marvel's Spider-Man: Miles Morales", "UNCHARTED: Legacy of Thieves Collection", "The Last of Us Part I", 
    "Tomb Raider", "Rise of the Tomb Raider", "Shadow of the Tomb Raider", "Control", "Alan Wake", 
    "Batman: Arkham Asylum", "Batman: Arkham City", "Batman: Arkham Knight", "Middle-earth: Shadow of Mordor", 
    "Middle-earth: Shadow of War", "Assassin's Creed Origins", "Assassin's Creed Odyssey", 
    "Assassin's Creed Valhalla", "Devil May Cry 5", "NieR:Automata", "Bayonetta", "The Witcher 3: Wild Hunt", 
    "Cyberpunk 2077", "The Elder Scrolls V: Skyrim Special Edition", "Fallout 4", "Fallout: New Vegas", 
    "Red Dead Redemption 2", "Grand Theft Auto V", "Baldur's Gate 3", "Divinity: Original Sin 2", 
    "Mass Effect Legendary Edition", "Dragon Age: Origins", "Persona 5 Royal", "Yakuza 0", 
    "Like a Dragon: Infinite Wealth", "Monster Hunter: World", "Monster Hunter Rise", 
    "Final Fantasy VII Remake Intergrade", "Kingdom Come: Deliverance", "DOOM", "DOOM Eternal", "Half-Life 2", 
    "Portal 2", "Left 4 Dead 2", "Team Fortress 2", "Counter-Strike 2", "Apex Legends", "PUBG: BATTLEGROUNDS", 
    "Destiny 2", "Rainbow Six Siege", "Overwatch 2", "Call of Duty: Modern Warfare II", "Borderlands 2", 
    "Borderlands 3", "Bioshock Infinite", "Titanfall 2", "Halo: The Master Chief Collection", "Hunt: Showdown", 
    "Metro Exodus", "Far Cry 5", "Resident Evil 2", "Resident Evil 4", "Resident Evil 7 Biohazard", 
    "Resident Evil Village", "Dead Space", "Outlast", "Amnesia: The Dark Descent", "Alien: Isolation", 
    "Phasmophobia", "Lethal Company", "Dead by Daylight", "Subnautica", "Rust", "ARK: Survival Evolved", 
    "The Forest", "Sons Of The Forest", "Terraria", "Don't Starve Together", "Valheim", "V Rising", 
    "Sid Meier's Civilization VI", "Crusader Kings III", "Stellaris", "Hearts of Iron IV", 
    "Age of Empires II: Definitive Edition", "XCOM 2", "Total War: WARHAMMER III", "Cities: Skylines", 
    "Planet Coaster", "Stardew Valley", "The Sims 4", "Microsoft Flight Simulator", "Euro Truck Simulator 2", 
    "Forza Horizon 4", "Forza Horizon 5", "Assetto Corsa", "Rocket League", "EA SPORTS FC 24", "NBA 2K24", 
    "Hollow Knight", "Celeste", "Cuphead", "Ori and the Will of the Wisps", "Dead Cells", "Hades", 
    "The Binding of Isaac: Rebirth", "Slay the Spire", "Vampire Survivors", "Enter the Gungeon", "Spelunky 2", 
    "Risk of Rain 2", "DARK SOULS: REMASTERED", "DARK SOULS III", "Sekiro: Shadows Die Twice", "ELDEN RING", 
    "Lies of P", "ARMORED CORE VI FIRES OF RUBICON", "Undertale", "Factorio", "RimWorld", 
    "Disco Elysium - The Final Cut", "Outer Wilds", "Return of the Obra Dinn", "Subnautica: Below Zero", 
    "A Plague Tale: Innocence", "A Plague Tale: Requiem", "Star Wars Jedi: Fallen Order", "Star Wars Jedi: Survivor", 
    "Ghostrunner", "Ghostwire: Tokyo", "Sekiro: Shadows Die Twice - GOTY Edition", "Dying Light", "Dying Light 2 Stay Human",
    "Hitman 3", "Hitman World of Assassination", "Sniper Elite 4", "Sniper Elite 5", "Dishonored", "Dishonored 2", 
    "Prey", "Wolfenstein: The New Order", "Wolfenstein II: The New Colossus", "RAGE 2", "Just Cause 3", "Just Cause 4", 
    "Mad Max", "Days Gone", "Death Stranding", "Detroit: Become Human", "Heavy Rain", "Beyond: Two Souls", 
    "Life is Strange", "The Walking Dead", "The Wolf Among Us", "Tales from the Borderlands", "Grim Fandango Remastered", 
    "Psychonauts 2", "It Takes Two", "A Way Out", "Brothers - A Tale of Two Sons", "Unravel", "Unravel Two", 
    "Little Nightmares", "Little Nightmares II", "Limbo", "Inside", "Braid", "Fez", "Super Meat Boy", 
    "Bastion", "Transistor", "Pyre", "Hades II", "Gris", "Journey", "Flower", "Abzu", "Slime Rancher", 
    "Slime Rancher 2", "My Time at Portia", "My Time at Sandrock", "Story of Seasons: Friends of Mineral Town", 
    "Rune Factory 4 Special", "Core Keeper", "Starbound", "No Man's Sky", "Elite Dangerous", "EVE Online", 
    "Star Citizen", "Kerbal Space Program", "Space Engineers", "Astroneer", "Dyson Sphere Program", "Satisfactory", 
    "Oxygen Not Included", "Don't Starve", "Kenshi", "Mount & Blade: Warband", "Mount & Blade II: Bannerlord", 
    "Chivalry 2", "Mordhau", "For Honor", "Mount & Blade", "Garry's Mod", "Tabletop Simulator", "VRChat", 
    "Jackbox Party Pack", "Keep Talking and Nobody Explodes", "Among Us", "Fall Guys", "Gang Beasts", "Human: Fall Flat", 
    "Party Animals", "Golf With Your Friends", "Pummel Party", "Ultimate Chicken Horse", "Duck Game", "TowerFall Ascension", 
    "Nidhogg", "SpeedRunners", "Lethal League Blaze", "Brawlhalla", "MultiVersus", "Street Fighter 6", 
    "Mortal Kombat 11", "Tekken 8", "Guilty Gear -Strive-", "Dragon Ball FighterZ", "Injustice 2", 
    "Soulcalibur VI", "Dead or Alive 6", "King of Fighters XV", "Melty Blood: Type Lumina", "BlazBlue: Cross Tag Battle", 
    "Under Night In-Birth Exe:Late[cl-r]", "Persona 4 Arena Ultimax", "Granblue Fantasy: Versus", "DNF Duel", 
    "Rivals of Aether", "Skullgirls 2nd Encore", "Thems Fightin Herds", "Nickelodeon All-Star Brawl", 
    "Super Smash Bros. Melee", "Sifu", "Sleeping Dogs: Definitive Edition", "Yakuza: Like a Dragon", "Judgment", 
    "Lost Judgment", "Shenmue I & II", "Shenmue III", "Bully: Scholarship Edition", "L.A. Noire", 
    "Mafia: Definitive Edition", "Mafia II: Definitive Edition", "Mafia III: Definitive Edition", "Saints Row: The Third", 
    "Saints Row IV", "Watch Dogs", "Watch Dogs 2", "Watch Dogs: Legion", "Far Cry 3", "Far Cry 4", "Far Cry 6", 
    "Crysis Remastered", "Crysis 2 Remastered", "Crysis 3 Remastered", "Half-Life: Alyx", "Boneworks", "BoneLab", 
    "Beat Saber", "Superhot VR", "Pistol Whip", "Blade & Sorcery", "The Walking Dead: Saints & Sinners", "Pavlov VR", 
    "VTOL VR", "Hot Dogs, Horseshoes & Hand Grenades", "Vail VR", "Ghost of Tsushima DIRECTOR'S CUT", "Helldivers 2", 
    "Palworld", "Enshrouded", "Nightingale", "Sons of the Forest", "Pacific Drive", "Dragon's Dogma 2", 
    "Manor Lords", "Senua's Saga: Hellblade II", "Elden Ring Shadow of the Erdtree", 
    "Black Myth: Wukong", "Star Wars Outlaws", "Frostpunk 2", "Space Marine 2", "STALKER 2: Heart of Chornobyl", 
    "Avowed", "Path of Exile 2", "Dwarf Fortress", "RimWorld", "Brotato", "Peglin", "Banners of Ruin",
    "Across the Obelisk", "Monster Train", "Gord", "Mortal Shell", "Thymesia", "Lords of the Fallen",
    "Nioh", "Nioh 2 - The Complete Edition", "Wo Long: Fallen Dynasty", "The Surge", "The Surge 2"
]

def main():
    final_db_file = os.path.join(DATA_DIR, 'games_database_final.json')
    backup_file = os.path.join(DATA_DIR, 'games_database_final_BACKUP.json')
    raw_out_file = os.path.join(DATA_DIR, 'games_database.json')

    # Backup if not exists
    if not os.path.exists(backup_file):
        import shutil
        shutil.copy2(final_db_file, backup_file)
        print(f"Backed up to {backup_file}")

    db = json.load(open(backup_file, encoding='utf-8'))
    existing_appids = {int(g.get('appid') or g.get('steam_appid')) for g in db if g.get('appid') or g.get('steam_appid')}

    appids_file = os.path.join(DATA_DIR, 'games_appid.json')
    master = json.load(open(appids_file, encoding='utf-8'))
    
    # Clean match mapping
    name_to_id = {m['name'].strip().lower(): m['appid'] for m in master if m.get('name')}

    targets = []
    # 1. Add from CURATED
    for name in CURATED:
        name_lower = name.strip().lower()
        appid = name_to_id.get(name_lower)
        if appid and appid not in existing_appids and appid not in targets:
            targets.append(appid)

    # 2. Top up with chronologically earlier games (often classics) until we have 300 targets to try
    if len(targets) < 300:
        for m in master:
            appid = m['appid']
            if appid not in existing_appids and appid not in targets:
                targets.append(appid)
            if len(targets) >= 300:
                break

    new_games = []
    added = 0
    for appid in targets:
        if added >= 250:
            break
            
        url = f"https://store.steampowered.com/api/appdetails?appids={appid}&cc=in"
        try:
            res = requests.get(url, timeout=10)
            data = res.json()
            if data and str(appid) in data and data[str(appid)].get('success'):
                app_data = data[str(appid)]['data']
                if app_data.get('type') != 'game':
                    print(f"Skipping {appid}: Not a game")
                    continue
                
                game = parse_game_from_steam(appid, app_data)
                
                # Check if it actually parsed OK (has a name)
                if game.get("name") and game.get("name") != "Unknown":
                    new_games.append(game)
                    added += 1
                    print(f"Added [{added}/250]: {game['name']} ({appid})")
                else:
                    print(f"Skipping {appid}: Could not parse correctly")
            else:
                print(f"Skipping {appid}: Steam API success:false")
        except Exception as e:
            print(f"Error {appid}: {e}")
            
        time.sleep(1.0) # rate limit

    with open(raw_out_file, 'w', encoding='utf-8') as f:
        json.dump(new_games, f, indent=4, ensure_ascii=False)
        
    print(f"Successfully fetched {added} raw games to {raw_out_file}.")

if __name__ == '__main__':
    main()
