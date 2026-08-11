"""Diagnostic script to investigate Bug 1 (trailers) and Bug 2 (game count)."""
import json
import os

DB_FILE = os.path.join(os.path.dirname(__file__), "data", "games_database_final.json")
FILTERED_FILE = os.path.join(os.path.dirname(__file__), "data", "filtered_games.json")

print("=" * 60)
print("RIGCHECK DIAGNOSTIC REPORT")
print("=" * 60)

# 1. Check games_database_final.json
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r", encoding="utf-8") as f:
        db_games = json.load(f)
    print(f"\n[DATABASE] games_database_final.json: {len(db_games)} games")
else:
    print(f"\n[DATABASE] games_database_final.json: NOT FOUND")
    db_games = []

# 2. Check filtered_games.json
if os.path.exists(FILTERED_FILE):
    fsize = os.path.getsize(FILTERED_FILE)
    print(f"[FILTERED] filtered_games.json: {fsize} bytes")
    if fsize > 2:
        with open(FILTERED_FILE, "r", encoding="utf-8") as f:
            filtered_games = json.load(f)
        print(f"[FILTERED] filtered_games.json: {len(filtered_games)} games")
    else:
        print(f"[FILTERED] filtered_games.json: EMPTY FILE")
        filtered_games = []
else:
    print(f"[FILTERED] filtered_games.json: NOT FOUND")
    filtered_games = []

# 3. Trailer analysis
print("\n" + "=" * 60)
print("TRAILER ANALYSIS")
print("=" * 60)

with_trailers = [g for g in db_games if g.get("trailers")]
with_movies = [g for g in db_games if g.get("movies")]
print(f"Games with 'trailers' field: {len(with_trailers)}")
print(f"Games with 'movies' field: {len(with_movies)}")

# Check what trailer data looks like
if with_trailers:
    sample = with_trailers[0]
    print(f"\nSample game WITH trailers: {sample.get('name')}")
    print(f"  trailers data: {json.dumps(sample.get('trailers'), indent=2)[:500]}")

if with_movies:
    sample = with_movies[0]
    print(f"\nSample game WITH movies: {sample.get('name')}")
    print(f"  movies data: {json.dumps(sample.get('movies'), indent=2)[:500]}")

# If NO games have trailers or movies, check what keys the games actually have
if not with_trailers and not with_movies:
    print("\nNO games have 'trailers' or 'movies' fields!")
    if db_games:
        print(f"Keys in first game: {sorted(db_games[0].keys())}")

# 4. Search for Uncharted
print("\n" + "=" * 60)
print("UNCHARTED INVESTIGATION")
print("=" * 60)

found_uncharted = False
for g in db_games:
    if "uncharted" in g.get("name", "").lower():
        found_uncharted = True
        print(f"Found: {g.get('name')} (appid={g.get('appid')})")
        print(f"  has 'trailers': {bool(g.get('trailers'))}")
        print(f"  has 'movies': {bool(g.get('movies'))}")
        if g.get("trailers"):
            print(f"  trailers value: {json.dumps(g['trailers'], indent=2)[:500]}")
        if g.get("movies"):
            print(f"  movies value: {json.dumps(g['movies'], indent=2)[:500]}")
        # Check all keys that might relate to video/trailer
        video_keys = [k for k in g.keys() if any(v in k.lower() for v in ["movie", "trailer", "video", "dash", "hls", "mp4", "webm"])]
        print(f"  video-related keys: {video_keys}")
        break

if not found_uncharted:
    print("Uncharted NOT found in database!")

# 5. Check raw_games folder
RAW_DIR = os.path.join(os.path.dirname(__file__), "raw_games")
if os.path.exists(RAW_DIR):
    raw_files = [f for f in os.listdir(RAW_DIR) if f.endswith(".json")]
    raw_count = len(raw_files)
    print(f"\n[RAW_GAMES] raw_games folder: {raw_count} raw game files")
    
    # Check for Uncharted (appid 1659420)
    uncharted_raw = os.path.join(RAW_DIR, "1659420.json")
    if os.path.exists(uncharted_raw):
        with open(uncharted_raw, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        app_data = raw_data.get("1659420", {}).get("data", {})
        print(f"\n[RAW] Uncharted raw Steam data:")
        print(f"  has 'movies': {bool(app_data.get('movies'))}")
        if app_data.get("movies"):
            for i, movie in enumerate(app_data["movies"]):
                print(f"\n  Movie {i}:")
                print(f"    id: {movie.get('id')}")
                print(f"    name: {movie.get('name')}")
                print(f"    thumbnail: {movie.get('thumbnail')}")
                print(f"    all keys: {sorted(movie.keys())}")
                # Show the actual URLs
                for key in sorted(movie.keys()):
                    if key not in ["id", "name", "thumbnail", "highlight"]:
                        val = movie.get(key)
                        print(f"    {key}: {json.dumps(val)[:200]}")
    else:
        print(f"  Raw file for Uncharted (1659420.json) NOT found")
    
    # Check a few other raw games for movie/trailer structure
    print(f"\n[RAW] Checking first 5 raw games for movies/trailers...")
    checked = 0
    for fname in raw_files[:20]:
        appid = fname.replace(".json", "")
        fpath = os.path.join(RAW_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            raw = json.load(f)
        app_data = raw.get(appid, {}).get("data", {})
        if app_data.get("movies"):
            movies = app_data["movies"]
            name = app_data.get("name", "Unknown")
            print(f"  {name} ({appid}): {len(movies)} movies, keys={sorted(movies[0].keys())}")
            checked += 1
            if checked >= 5:
                break
else:
    print(f"\n[RAW_GAMES] raw_games folder: NOT FOUND")

# 6. Check the pipeline: 02_parse_requirements -> filtered_games -> 03_build_database
print("\n" + "=" * 60)
print("PIPELINE FILE SIZES")
print("=" * 60)
data_files = [
    "data/games_appid.json",
    "data/filtered_games.json",
    "data/games_database_final.json",
    "data/fetch_progress.json",
    "data/failed_games.json",
]
for fpath in data_files:
    full = os.path.join(os.path.dirname(__file__), fpath)
    if os.path.exists(full):
        size = os.path.getsize(full)
        print(f"  {fpath}: {size:,} bytes")
    else:
        print(f"  {fpath}: NOT FOUND")

# 7. Check the /games API endpoint limit
print("\n" + "=" * 60)
print("API ENDPOINT ANALYSIS")
print("=" * 60)
print("  GET /games has default limit=20, max le=100")
print("  Frontend fetchGames() calls with limit=100, offset=0")
print("  This means frontend can only show max 100 games per page")
print("  But the database only has 76 games anyway")

print("\n" + "=" * 60)
print("END OF DIAGNOSTIC REPORT")
print("=" * 60)
