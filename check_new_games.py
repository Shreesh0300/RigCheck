import json

with open("data/games_database_final.json", "r", encoding="utf-8") as f:
    games = json.load(f)

print(f"Total games in final: {len(games)}")
old_games = games[:750]
new_games = games[750:]

# Check for duplicates
appids = [g.get("appid") or g.get("steam_appid") for g in games]
duplicates = set([x for x in appids if appids.count(x) > 1])
if duplicates:
    print(f"DUPLICATES FOUND: {duplicates}")
else:
    print("No duplicate App IDs found.")

print(f"Existing 750 games preserved: {len(old_games) == 750}")

# Check missing metadata in new games
missing = []
for g in new_games:
    missing_fields = []
    if not g.get("name"): missing_fields.append("name")
    if not g.get("short_description"): missing_fields.append("description")
    if not g.get("genres"): missing_fields.append("genres")
    if not g.get("categories"): missing_fields.append("categories")
    if not g.get("release_date"): missing_fields.append("release_date")
    if not g.get("developers"): missing_fields.append("developers")
    if not g.get("publishers"): missing_fields.append("publishers")
    if not g.get("minimum"): missing_fields.append("minimum (reqs)")
    if g.get("price_overview") is None and not g.get("is_free"):
        # Could be free or just unpriced
        missing_fields.append("price")
    
    if missing_fields:
        missing.append(f"{g.get('name')} missing: {', '.join(missing_fields)}")

print(f"New games with missing metadata: {len(missing)} out of {len(new_games)}")
if missing:
    with open("missing_metadata.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(missing))

with open("new_250_games.txt", "w", encoding="utf-8") as f:
    for g in new_games:
        f.write(f"{g.get('name')} (AppID: {g.get('appid') or g.get('steam_appid')})\n")

print("Generated new_250_games.txt")
