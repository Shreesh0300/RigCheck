import json

with open("data/games_database_final.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for game in data[:2]:
    print(f"Name: {game.get('name')}")
    print(f"  genres: {game.get('genres')}")
    print(f"  categories: {game.get('categories')}")
    print(f"  tags (if any): {game.get('tags', 'NOT FOUND')}")
    print("-" * 20)

for game in data:
    if "Hades" in game.get('name', ''):
        print(f"Name: {game.get('name')}")
        print(f"  genres: {game.get('genres')}")
        print(f"  categories: {game.get('categories')}")
        print("-" * 20)
        
    if "PUBG" in game.get('name', ''):
        print(f"Name: {game.get('name')}")
        print(f"  genres: {game.get('genres')}")
        print(f"  categories: {game.get('categories')}")
        print("-" * 20)
