import os
import re
import html
from utils import ensure_directory, load_json, save_json

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
FILTERED_FILE = os.path.join(DATA_DIR, 'filtered_games.json')
DB_FILE = os.path.join(DATA_DIR, 'games_database.json')

def strip_html(html_str):
    if not html_str:
        return ""
    # Replace line-breaking HTML tags with newlines to preserve structure
    text = re.sub(r'<br\s*/?>', '\n', html_str, flags=re.IGNORECASE)
    text = re.sub(r'</li>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<li>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
    
    # Strip remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Unescape HTML entities (e.g. &amp; -> &)
    text = html.unescape(text)
    
    # Clean up multiple newlines and spaces
    text = re.sub(r'\n+', '\n', text)
    return text.strip()

def parse_requirements(raw_html):
    if not raw_html:
        return None
        
    text = strip_html(raw_html)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    parsed = {
        "os": None,
        "cpu_raw": None,
        "ram_raw": None,
        "gpu_raw": None,
        "directx_raw": None,
        "storage_raw": None,
        "sound_raw": None,
        "network_raw": None,
        "controller_raw": None,
        "notes_raw": None
    }
    
    keyword_map = {
        "OS": "os",
        "PROCESSOR": "cpu_raw",
        "MEMORY": "ram_raw",
        "GRAPHICS": "gpu_raw",
        "VIDEO CARD": "gpu_raw",
        "DIRECTX": "directx_raw",
        "STORAGE": "storage_raw",
        "HARD DRIVE": "storage_raw",
        "HARD DISK SPACE": "storage_raw",
        "SOUND CARD": "sound_raw",
        "NETWORK": "network_raw",
        "ADDITIONAL NOTES": "notes_raw",
        "CONTROLLER": "controller_raw"
    }
    
    # Sort keys by length descending to match longest first (e.g., "HARD DISK SPACE" before "HARD DRIVE")
    sorted_keywords = sorted(keyword_map.keys(), key=len, reverse=True)
    
    current_key = None
    current_value = []
    
    for line in lines:
        matched_keyword = None
        for kw in sorted_keywords:
            # Match keyword optionally followed by asterisks and a colon at the start of the string
            pattern = re.compile(rf"^{re.escape(kw)}\s*\**\s*:", re.IGNORECASE)
            match = pattern.match(line)
            if match:
                matched_keyword = kw
                content = line[match.end():].strip()
                
                # Save the previously tracked key before switching
                if current_key and current_value:
                    parsed[current_key] = " ".join(current_value).strip()
                    
                current_key = keyword_map[kw]
                current_value = [content] if content else []
                break
                
        if matched_keyword:
            continue
            
        # If no new keyword was found, append this line to the active key
        if current_key:
            current_value.append(line)
            
    # Save the final tracked key
    if current_key and current_value:
        parsed[current_key] = " ".join(current_value).strip()
        
    return parsed

def main():
    ensure_directory(DATA_DIR)
    
    if not os.path.exists(FILTERED_FILE):
        print(f"File not found: {FILTERED_FILE}")
        return

    games = load_json(FILTERED_FILE)
    if not games:
        print("No games to process.")
        return

    total_games = len(games)
    db_games = []

    for i, game in enumerate(games):
        print(f"\n[{i + 1} / {total_games}]")
        print("Building Database")
        print(game.get('name', 'Unknown'))
        
        # Clone the game object to keep all metadata fields
        new_game = dict(game)
        
        # Parse and replace the raw HTML blocks with structured data
        new_game["minimum"] = parse_requirements(game.get("minimum"))
        new_game["recommended"] = parse_requirements(game.get("recommended"))
        
        db_games.append(new_game)
        
    save_json(DB_FILE, db_games)
    
    print("\n====================================")
    print("DATABASE BUILD COMPLETE")
    print(f"Total Games Processed: {len(db_games)}")
    print(f"Saved to: {DB_FILE}")
    print("====================================")

if __name__ == "__main__":
    main()
