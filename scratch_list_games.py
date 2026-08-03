import json

try:
    with open("data/games_database_final.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    print("All games in dataset:")
    for game in data:
        print(f" - {game.get('name')}")
except Exception as e:
    print(f"Error: {e}")
