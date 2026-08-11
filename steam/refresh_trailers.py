"""
refresh_trailers.py
===================
Re-fetches trailer data from Steam API for all games in games_database_final.json.
Updates the trailer field with the new adaptive streaming format (dash_h264, hls_h264, dash_av1).

Usage:
    python steam/refresh_trailers.py
"""
import os
import sys
import time
import json
import requests

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_FILE = os.path.join(DATA_DIR, 'games_database_final.json')


def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def extract_trailers(movies):
    """Extract trailers from Steam movies data using the new format."""
    trailers = []
    for movie in movies:
        mp4_data = movie.get("mp4")
        webm_data = movie.get("webm")
        trailer = {
            "movie_id": movie.get("id"),
            "name": movie.get("name"),
            "thumbnail": movie.get("thumbnail"),
            "highlight": movie.get("highlight", False),
            # New adaptive streaming formats
            "dash_h264": movie.get("dash_h264"),
            "hls_h264": movie.get("hls_h264"),
            "dash_av1": movie.get("dash_av1"),
            # Legacy fallback formats
            "mp4_max": mp4_data.get("max") if isinstance(mp4_data, dict) else None,
            "mp4_480": mp4_data.get("480") if isinstance(mp4_data, dict) else None,
            "webm_max": webm_data.get("max") if isinstance(webm_data, dict) else None,
            "webm_480": webm_data.get("480") if isinstance(webm_data, dict) else None,
        }
        trailers.append(trailer)
    return trailers


def main():
    games = load_json(DB_FILE)
    if not games:
        print(f"Could not load {DB_FILE}")
        return

    print(f"Refreshing trailers for {len(games)} games...")
    
    updated = 0
    failed = 0
    already_ok = 0
    
    for i, game in enumerate(games):
        appid = game.get('appid') or game.get('steam_appid')
        name = game.get('name', f'App {appid}')
        
        # Skip games without valid appid
        if not appid:
            print(f"[{i+1}/{len(games)}] Skipping {name} — no appid")
            continue
        
        # Check if trailers already have the new format
        existing_trailers = game.get('trailers') or []
        has_new_format = any(
            t.get('hls_h264') or t.get('dash_h264') 
            for t in existing_trailers
        )
        if has_new_format:
            already_ok += 1
            print(f"[{i+1}/{len(games)}] Skipping {name} — trailers already up-to-date")
            continue
        
        print(f"[{i+1}/{len(games)}] Fetching trailers for {name} ({appid})")
        
        url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            str_appid = str(appid)
            
            if str_appid in data and data[str_appid].get('success'):
                app_data = data[str_appid]['data']
                movies = app_data.get('movies', [])
                
                if movies:
                    game['trailers'] = extract_trailers(movies)
                    updated += 1
                    print(f"  -> Found {len(movies)} trailer(s)")
                else:
                    game['trailers'] = []
                    print(f"  -> No trailers on Steam")
            else:
                failed += 1
                print(f"  -> Steam returned success:false")
        except Exception as e:
            failed += 1
            print(f"  -> Error: {e}")
        
        # Save incrementally every 10 games
        if (i + 1) % 10 == 0:
            save_json(DB_FILE, games)
        
        # Rate limiting
        time.sleep(1.0)
    
    # Final save
    save_json(DB_FILE, games)
    
    print("\n====================================")
    print("TRAILER REFRESH COMPLETE")
    print(f"Total Games: {len(games)}")
    print(f"Updated: {updated}")
    print(f"Already OK: {already_ok}")
    print(f"Failed: {failed}")
    print(f"No trailers: {len(games) - updated - already_ok - failed}")
    print("====================================")


if __name__ == "__main__":
    main()
