import json
import os
import requests
import time
import sys

BASE_DIR = r'v:\Projects\RigCheck'
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_FILE = os.path.join(DATA_DIR, 'games_database_final.json')

sys.path.insert(0, os.path.join(BASE_DIR, 'steam'))
from expand_to_1000 import parse_game_from_steam, apply_tier_mapping, _build_lookup, CPU_LUT, GPU_LUT

db = json.load(open(DB_FILE, 'r', encoding='utf-8'))
gap = 1000 - len(db)
print(f'Current count: {len(db)}. Need {gap} more games.')

if gap <= 0:
    print('Done.')
    sys.exit(0)

# Provide plenty of popular candidates that might not be in the DB
MORE_CANDIDATES = {
    # Racing / Sports
    244210: 'Assetto Corsa',
    805550: 'Assetto Corsa Competizione',
    227300: 'Euro Truck Simulator 2',
    270880: 'American Truck Simulator',
    # Simulators
    289070: 'Sid Meier\'s Civilization VI',
    1086940: 'Baldur\'s Gate 3',
    294100: 'RimWorld',
    # Others
    250900: 'The Binding of Isaac: Rebirth',
    391540: 'Undertale',
    105600: 'Terraria',
    1057090: 'Ori and the Will of the Wisps',
    367520: 'Hollow Knight',
    281990: 'Stellaris',
    394360: 'Hearts of Iron IV',
    236850: 'Europa Universalis IV',
    1158310: 'Crusader Kings III',
    323190: 'Frostpunk',
    # Leftovers
    990080: 'Hogwarts Legacy',
    1593500: 'God of War',
    1888160: 'ARMORED CORE VI FIRES OF RUBICON',
    2050650: 'Resident Evil 4',
    418370: 'Rise of the Tomb Raider',
    2358720: 'Black Myth: Wukong',
    275470: 'Divinity: Original Sin 2',
    524220: 'NieR:Automata',
    # Action/Survival
    381210: 'Dead by Daylight',
    2104880: 'Lethal Company',
    1627720: 'Sons Of The Forest',
    252490: 'Rust',
    304930: 'Unturned',
    1096990: 'Raft',
    313120: 'Stranded Deep',
    1063730: 'New World',
    1172470: 'Apex Legends',
    578080: 'PUBG: BATTLEGROUNDS',
    218620: 'PAYDAY 2',
    1272080: 'PAYDAY 3',
    1203220: 'NARAKA: BLADEPOINT',
    760060: 'Deep Rock Galactic',
    1237970: 'Titanfall 2',
    1238060: 'It Takes Two',
    594650: 'Hunt: Showdown',
    49520: 'Borderlands 2',
    7670: 'BioShock',
    8850: 'BioShock 2',
    8870: 'BioShock Infinite',
    1517290: 'Battlefield 2042',
    1238810: 'Battlefield V',
    1238840: 'Battlefield 1',
    # More gap fillers
    284160: 'BeamNG.drive',
    400: 'Portal',
    620: 'Portal 2',
    10: 'Counter-Strike',
    240: 'Counter-Strike: Source',
    730: 'Counter-Strike 2',
    440: 'Team Fortress 2',
    4000: 'Garry\'s Mod',
    322330: 'Don\'t Starve Together',
    553420: 'TUNIC',
    1150690: 'OMORI',
    582010: 'Monster Hunter: World',
    1446780: 'Monster Hunter Rise',
}

existing_ids = {int(g.get('appid') or g.get('steam_appid')) for g in db}
targets = [aid for aid in MORE_CANDIDATES if aid not in existing_ids]

cpu_lookup = _build_lookup(CPU_LUT)
gpu_lookup = _build_lookup(GPU_LUT)

new_games = []

for aid in targets:
    if len(new_games) >= gap:
        break
    print(f'Fetching {aid}...', end=' ', flush=True)
    url = f'https://store.steampowered.com/api/appdetails?appids={aid}&cc=in'
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if str(aid) in data and data[str(aid)].get('success'):
            app_data = data[str(aid)]['data']
            if app_data.get('type') == 'game':
                game = parse_game_from_steam(aid, app_data)
                game = apply_tier_mapping(game, cpu_lookup, gpu_lookup)
                new_games.append(game)
                print(f"OK ({game.get('name')})")
            else:
                print(f"SKIP ({app_data.get('type')})")
        else:
            print('FAIL')
    except Exception as e:
        print(f'ERR {e}')
    time.sleep(1.2)
    
db.extend(new_games)
print(f'Final count: {len(db)}')
json.dump(db, open(DB_FILE, 'w', encoding='utf-8'), indent=4, ensure_ascii=False)
print('Done')
