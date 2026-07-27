import argparse
import os
import time
import datetime
from utils import ensure_directory, load_json, save_json, safe_request

# Paths setup
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
RAW_GAMES_DIR = os.path.join(BASE_DIR, 'raw_games')

APPID_FILE = os.path.join(DATA_DIR, 'games_appid.json')
PROGRESS_FILE = os.path.join(DATA_DIR, 'fetch_progress.json')
FAILED_FILE = os.path.join(DATA_DIR, 'failed_games.json')
STATS_FILE = os.path.join(DATA_DIR, 'fetch_stats.json')

def main():
    parser = argparse.ArgumentParser(description="Fetch raw game data from Steam API.")
    parser.add_argument('--limit', type=int, help='Maximum number of games to download.')
    parser.add_argument('--start', type=int, help='Index to start downloading from.')
    args = parser.parse_args()

    ensure_directory(DATA_DIR)
    ensure_directory(RAW_GAMES_DIR)

    games_data = load_json(APPID_FILE)
    if not games_data:
        print(f"Could not load {APPID_FILE}. Ensure it exists and is not empty.")
        return

    if not isinstance(games_data, list):
        print("Expected a list of games in games_appid.json")
        return

    failed_games = load_json(FAILED_FILE, [])
    # Convert to set for O(1) lookups and avoiding duplicates
    failed_games_set = set(failed_games)
    
    stats = load_json(STATS_FILE)
    if not stats:
        stats = {
            "total_processed": 0,
            "downloaded": 0,
            "skipped_existing": 0,
            "skipped_non_games": 0,
            "failed": 0,
            "last_index": 0,
            "last_appid": None,
            "last_game_name": "",
            "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "last_updated": "",
            "finished": False
        }
        
    session_start_time = time.time()
    session_downloads = 0

    # Load progress if start is not specified
    start_index = args.start
    if start_index is None:
        progress = load_json(PROGRESS_FILE, {"last_index": 0})
        start_index = progress.get("last_index", 0)

    end_index = len(games_data)
    if args.limit is not None:
        end_index = min(len(games_data), start_index + args.limit)

    for i in range(start_index, end_index):
        game = games_data[i]
        appid = game.get('appid')
        name = game.get('name', 'Unknown')
        
        if not appid:
            continue
            
        stats['total_processed'] += 1
        stats['last_index'] = i
        stats['last_appid'] = appid
        stats['last_game_name'] = name

        percentage = (i / len(games_data)) * 100 if len(games_data) > 0 else 0
        print(f"\n[{i} / {len(games_data)}] ({percentage:.2f}%)")
        print(f"Downloading:\n{name}")
        print(f"AppID:\n{appid}")

        out_file = os.path.join(RAW_GAMES_DIR, f"{appid}.json")
        
        if os.path.exists(out_file):
            print(f"Skipping. File already exists: raw_games/{appid}.json")
            stats['skipped_existing'] += 1
        else:
            url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
            response = safe_request(url, max_retries=3, delay_between_retries=1.0)
            
            success = False
            if response is not None:
                try:
                    data = response.json()
                    str_appid = str(appid)
                    # Check if Steam returned success: true
                    if str_appid in data and data[str_appid].get('success'):
                        app_data = data[str_appid].get('data', {})
                        app_type = app_data.get('type')
                        
                        if app_type == 'game':
                            success = True
                            save_json(out_file, data)
                            print(f"Downloaded:\nraw_games/{appid}.json")
                            stats['downloaded'] += 1
                            session_downloads += 1
                        else:
                            success = True
                            print(f"Skipping AppID {appid}")
                            print(f"Reason: type = {app_type}")
                            stats['skipped_non_games'] += 1
                    else:
                        print("Steam returned success:false")
                except ValueError:
                    print("Invalid JSON response from Steam")
                
            if not success:
                stats['failed'] += 1
                if appid not in failed_games_set:
                    failed_games_set.add(appid)
                    failed_games.append(appid)
                    save_json(FAILED_FILE, failed_games)
            
            # Rate limiting
            time.sleep(0.5)

        # Save progress and stats
        save_json(PROGRESS_FILE, {"last_index": i + 1})
        stats['last_updated'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_json(STATS_FILE, stats)

    if end_index >= len(games_data):
        stats['finished'] = True
        save_json(STATS_FILE, stats)

    print("\n====================================")
    print("DOWNLOAD COMPLETE")
    print(f"Processed: {stats['total_processed']}")
    print(f"Downloaded: {stats['downloaded']}")
    print(f"Skipped Existing: {stats['skipped_existing']}")
    print(f"Skipped Non-Games: {stats['skipped_non_games']}")
    print(f"Failed: {stats['failed']}")
    print("====================================")

    elapsed_seconds = time.time() - session_start_time
    minutes = elapsed_seconds / 60.0
    avg = session_downloads / minutes if minutes > 0 else 0
    
    hours, rem = divmod(elapsed_seconds, 3600)
    mins, secs = divmod(rem, 60)
    print(f"\nElapsed:\n{int(hours):02d}:{int(mins):02d}:{int(secs):02d}")
    print(f"\nAverage:\n{int(avg)} downloads/minute")

if __name__ == "__main__":
    main()
