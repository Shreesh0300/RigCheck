import os
import time
import requests
from utils import load_json, save_json

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_FILE = os.path.join(DATA_DIR, 'games_database_final.json')

def fix_prices():
    games = load_json(DB_FILE)
    if not games:
        print("No games found in games_database_final.json")
        return

    print(f"Fixing prices for {len(games)} games...")
    
    updated = 0
    for i, game in enumerate(games):
        appid = game.get('appid') or game.get('steam_appid')
        name = game.get('name', f"App {appid}")
        
        # Check if the currency is already INR to avoid re-fetching
        price_overview = game.get("price_overview", {})
        if isinstance(price_overview, dict) and price_overview.get("currency") == "INR":
            print(f"[{i+1}/{len(games)}] Skipping {name} - already INR")
            continue
            
        print(f"[{i+1}/{len(games)}] Fetching INR price for {name} ({appid})")
        
        url = f"https://store.steampowered.com/api/appdetails?appids={appid}&cc=in"
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            if str(appid) in data and data[str(appid)].get('success'):
                app_data = data[str(appid)]['data']
                
                # Free games might not have price_overview
                if 'price_overview' in app_data:
                    game['price_overview'] = app_data['price_overview']
                elif app_data.get('is_free'):
                    # Clear any incorrect price overview
                    game['price_overview'] = {}
                
                updated += 1
                save_json(DB_FILE, games)  # Save incrementally
            else:
                print(f"  -> Failed to fetch app details for {appid}.")
        except Exception as e:
            print(f"  -> Request error: {e}")
            
        time.sleep(1.0) # rate limit

    print(f"\nDone! Fixed prices for {updated} games out of {len(games)}.")

if __name__ == "__main__":
    fix_prices()
