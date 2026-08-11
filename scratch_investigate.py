import json

# Load the final database
with open('data/games_database_final.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"DATABASE GAME COUNT: {len(data)}")

# Check for Uncharted
uncharted = [g for g in data if 'uncharted' in g.get('name', '').lower()]
print(f"\nUNCHARTED GAMES IN DB: {len(uncharted)}")
for g in uncharted:
    print(f"  Name: {g['name']}")
    print(f"  AppID: {g.get('appid')}")
    print(f"  Trailers: {json.dumps(g.get('trailers', []), indent=2)}")

# Count games with trailers
with_trailers = [g for g in data if g.get('trailers') and len(g['trailers']) > 0]
print(f"\nGAMES WITH TRAILERS: {len(with_trailers)}")

# Show a few trailer examples
print("\nSAMPLE TRAILERS (first 3 games with trailers):")
for g in with_trailers[:3]:
    print(f"  {g['name']}: {json.dumps(g['trailers'][0], indent=4)}")

# Check if any trailer has webm/mp4 fields
print("\nTRAILER FIELD ANALYSIS:")
all_trailer_keys = set()
for g in data:
    for t in g.get('trailers', []):
        all_trailer_keys.update(t.keys())
print(f"  All trailer keys used: {all_trailer_keys}")

# Also check filtered_games.json count
try:
    with open('data/filtered_games.json', 'r', encoding='utf-8') as f:
        filtered = json.load(f)
    print(f"\nFILTERED_GAMES.JSON COUNT: {len(filtered)}")
except FileNotFoundError:
    print("\nFILTERED_GAMES.JSON NOT FOUND")

# Check games_database.json (intermediate)
try:
    with open('data/games_database.json', 'r', encoding='utf-8') as f:
        intermediate = json.load(f)
    print(f"GAMES_DATABASE.JSON (intermediate) COUNT: {len(intermediate)}")
except FileNotFoundError:
    print("GAMES_DATABASE.JSON NOT FOUND")

# Check gameData.js game count
import re
with open('src/gameData.js', 'r', encoding='utf-8') as f:
    content = f.read()
game_count = len(re.findall(r'steamAppId:', content))
print(f"\nGAMEDATA.JS STATIC GAME COUNT: {game_count}")
