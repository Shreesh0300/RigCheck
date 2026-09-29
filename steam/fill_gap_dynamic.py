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

existing_ids = {int(g.get('appid') or g.get('steam_appid')) for g in db}

cpu_lookup = _build_lookup(CPU_LUT)
gpu_lookup = _build_lookup(GPU_LUT)

new_games = []

# Fetch popular games from SteamSpy API to get valid appids
print("Fetching top games from SteamSpy...")
resp = requests.get('https://steamspy.com/api.php?request=top100in2weeks', timeout=10)
top_games = resp.json()

for aid_str in top_games.keys():
    aid = int(aid_str)
    if aid in existing_ids:
        continue
        
    if len(new_games) >= gap:
        break
        
    print(f'Fetching {aid}...', end=' ', flush=True)
    url = f'https://store.steampowered.com/api/appdetails?appids={aid}&cc=in'
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
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

# If still need more, use top 100 forever
if len(new_games) < gap:
    print("Fetching more from top100forever...")
    resp = requests.get('https://steamspy.com/api.php?request=top100forever', timeout=10)
    top_games = resp.json()
    for aid_str in top_games.keys():
        aid = int(aid_str)
        if aid in existing_ids or any(int(g.get('appid') or g.get('steam_appid')) == aid for g in new_games):
            continue
            
        if len(new_games) >= gap:
            break
            
        print(f'Fetching {aid}...', end=' ', flush=True)
        url = f'https://store.steampowered.com/api/appdetails?appids={aid}&cc=in'
        try:
            r = requests.get(url, timeout=10)
            data = r.json()
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
