import os
import time
import requests
import html
import re
from utils import load_json, save_json

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_FILE = os.path.join(DATA_DIR, 'games_database_final.json')

def strip_html(html_str):
    if not html_str:
        return ""
    text = re.sub(r'<br\s*/?>', '\n', html_str, flags=re.IGNORECASE)
    text = re.sub(r'</li>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<li>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = re.sub(r'\n+', '\n', text)
    return text.strip()

def enrich_database():
    games = load_json(DB_FILE)
    if not games:
        print("No games found in games_database_final.json")
        return

    print(f"Enriching {len(games)} games...")
    
    updated = 0
    for i, game in enumerate(games):
        appid = game.get('appid') or game.get('steam_appid')
        name = game.get('name', f"App {appid}")
        
        if 'about_the_game' in game and 'detailed_description' in game:
            # Skip already enriched games
            print(f"[{i+1}/{len(games)}] Skipping {name} ({appid}) - already enriched")
            continue
            
        print(f"[{i+1}/{len(games)}] Fetching data for {name} ({appid})")
        
        url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            if str(appid) in data and data[str(appid)].get('success'):
                app_data = data[str(appid)]['data']
                
                about = app_data.get('about_the_game', '')
                if about:
                    game['about_the_game'] = strip_html(about)
                
                desc = app_data.get('detailed_description', '')
                if desc:
                    game['detailed_description'] = strip_html(desc)
                    
                if 'categories' in app_data:
                    game['categories'] = app_data['categories']
                    
                if 'developers' in app_data:
                    game['developers'] = app_data['developers']
                    
                updated += 1
            else:
                print(f"  -> Failed to fetch app details for {appid}.")
        except Exception as e:
            print(f"  -> Request error: {e}")
            
        time.sleep(1.0) # rate limit

    save_json(DB_FILE, games)
    print(f"\nDone! Enriched {updated} games out of {len(games)}.")

if __name__ == "__main__":
    enrich_database()
