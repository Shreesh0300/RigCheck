import json
import sys

with open("data/games_database_final.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for game in data:
    name = game.get('name', '')
    if name in ["Dota 2", "Counter-Strike 2", "Hades", "PUBG: BATTLEGROUNDS"]:
        print(f"Name: {name}")
        print(f"  is_free: {game.get('is_free')}")
        po = game.get('price_overview')
        print(f"  price_overview keys: {list(po.keys()) if po else 'None'}")
        if po and 'final' in po:
            print(f"  price_overview final: {po['final']}")
        print(f"  movies: {True if game.get('movies') else False} (count: {len(game.get('movies', []))})")
        if game.get('movies'):
            print(f"    first movie mp4/webm: {game['movies'][0].get('mp4', {}).get('max')} / {game['movies'][0].get('webm', {}).get('max')}")
        print(f"  platforms: {game.get('platforms')}")
        print(f"  appid: {game.get('appid')}")
        print("-" * 30)
