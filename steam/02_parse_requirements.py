import os
from utils import ensure_directory, load_json, save_json

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
RAW_GAMES_DIR = os.path.join(BASE_DIR, 'raw_games')
FILTERED_FILE = os.path.join(DATA_DIR, 'filtered_games.json')

def main():
    ensure_directory(DATA_DIR)
    
    if not os.path.exists(RAW_GAMES_DIR):
        print(f"Directory {RAW_GAMES_DIR} does not exist. Run Stage 1 first.")
        return

    files = [f for f in os.listdir(RAW_GAMES_DIR) if f.endswith('.json')]
    total_files = len(files)
    
    filtered_data = []

    for i, filename in enumerate(files):
        filepath = os.path.join(RAW_GAMES_DIR, filename)
        raw_data = load_json(filepath)
        
        if not raw_data:
            continue
            
        # Steam API response root key is usually the appid (as string)
        app_keys = list(raw_data.keys())
        if not app_keys:
            continue
            
        app_key = app_keys[0]
        app_response = raw_data[app_key]
        
        # We only process successfully fetched entries
        if not app_response.get('success'):
            continue
            
        data = app_response.get('data')
        if not data:
            continue
            
        # Safeguard: we only want games
        if data.get('type') != 'game':
            continue

        name = data.get('name', 'Unknown')
        
        print(f"[{i + 1} / {total_files}]")
        print(f"Parsing\n{name}")

        # Construct clean object
        game = {
            "appid": data.get("steam_appid", int(app_key) if app_key.isdigit() else None),
            "name": name,
            "steam_appid": data.get("steam_appid"),
            "required_age": data.get("required_age"),
            "is_free": data.get("is_free"),
            "developers": data.get("developers", []),
            "publishers": data.get("publishers", []),
            
            "genres": [g.get("description") for g in data.get("genres", []) if "description" in g],
            "categories": [c.get("description") for c in data.get("categories", []) if "description" in c],
            
            "release_date": data.get("release_date", {}).get("date"),
            "header_image": data.get("header_image"),
            
            "screenshots": [s.get("path_full") for s in data.get("screenshots", []) if "path_full" in s],
            
            "trailers": [],
            
            "supported_languages": data.get("supported_languages"),
            "website": data.get("website"),
            
            "minimum": data.get("pc_requirements", {}).get("minimum"),
            "recommended": data.get("pc_requirements", {}).get("recommended"),
            
            "price_overview": None,
            
            "recommendations": data.get("recommendations", {}).get("total"),
            "metacritic": data.get("metacritic", {}).get("score"),
            
            "platforms": {
                "windows": data.get("platforms", {}).get("windows", False),
                "mac": data.get("platforms", {}).get("mac", False),
                "linux": data.get("platforms", {}).get("linux", False)
            }
        }

        # Trailers extraction — supports both new adaptive streaming and legacy formats
        for movie in data.get("movies", []):
            mp4_data = movie.get("mp4")
            webm_data = movie.get("webm")
            trailer = {
                "movie_id": movie.get("id"),
                "name": movie.get("name"),
                "thumbnail": movie.get("thumbnail"),
                "highlight": movie.get("highlight", False),
                # New adaptive streaming formats (priority order)
                "dash_h264": movie.get("dash_h264"),
                "hls_h264": movie.get("hls_h264"),
                "dash_av1": movie.get("dash_av1"),
                # Legacy fallback formats
                "mp4_max": mp4_data.get("max") if isinstance(mp4_data, dict) else None,
                "mp4_480": mp4_data.get("480") if isinstance(mp4_data, dict) else None,
                "webm_max": webm_data.get("max") if isinstance(webm_data, dict) else None,
                "webm_480": webm_data.get("480") if isinstance(webm_data, dict) else None,
            }
            game["trailers"].append(trailer)
            
        # Price overview extraction
        price_data = data.get("price_overview")
        if price_data:
            game["price_overview"] = {
                "currency": price_data.get("currency"),
                "initial": price_data.get("initial"),
                "final": price_data.get("final"),
                "discount_percent": price_data.get("discount_percent")
            }
            
        filtered_data.append(game)

    # Save cleanly parsed intermediate dataset
    save_json(FILTERED_FILE, filtered_data)
    
    print("\n====================================")
    print("PARSING COMPLETE")
    print(f"Total Games Parsed: {len(filtered_data)}")
    print(f"Saved to: {FILTERED_FILE}")
    print("====================================")

if __name__ == "__main__":
    main()
