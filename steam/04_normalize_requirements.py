import os
import re
from utils import ensure_directory, load_json, save_json

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_FILE = os.path.join(DATA_DIR, 'games_database.json')
NORMALIZED_FILE = os.path.join(DATA_DIR, 'games_database_normalized.json')

def normalize_hardware_string(text):
    if not text:
        return []
    
    # Split on explicit separators: newline, forward slash, comma, semicolon, pipe.
    # Also match the words 'or', 'and', and the '+' character if surrounded by spaces.
    pattern = r'\n+|\s*(?:/|,|;|\|)\s*|\s+\b(?:or|and)\b\s+|\s+\+\s+'
    parts = re.split(pattern, text, flags=re.IGNORECASE)
    
    cleaned = []
    for p in parts:
        p_strip = p.strip()
        # Ensure we ignore empty strings and deduplicate
        if p_strip and p_strip not in cleaned:
            cleaned.append(p_strip)
    return cleaned

def extract_integer_field(text, check_mb=False):
    if not text:
        return None
        
    # Extract the first sequence of digits found
    match = re.search(r'(\d+)', text)
    if match:
        val = int(match.group(1))
        # Basic heuristic to handle old games that specify requirements in Megabytes
        if check_mb:
            is_mb = re.search(r'\bMB\b|\bM\b', text, re.IGNORECASE)
            is_gb = re.search(r'\bGB\b|\bG\b', text, re.IGNORECASE)
            if is_mb and not is_gb:
                # Convert MB to GB, ensuring minimum of 1 GB to avoid returning 0
                return max(1, round(val / 1024))
        return val
    return None

def main():
    ensure_directory(DATA_DIR)
    
    if not os.path.exists(DB_FILE):
        print(f"File not found: {DB_FILE}")
        return

    games = load_json(DB_FILE)
    if not games:
        print("No games to process.")
        return

    total_games = len(games)
    normalized_games = []
    
    # Track statistics across the dataset
    stats = {
        "cpu": 0,
        "gpu": 0,
        "ram": 0,
        "storage": 0,
        "directx": 0
    }

    for i, game in enumerate(games):
        print(f"\n[{i + 1} / {total_games}]")
        print("Normalizing")
        print(game.get('name', 'Unknown'))
        
        # Clone the existing object to preserve all existing data and *_raw fields
        new_game = dict(game)
        
        # Track whether this game successfully extracted any hardware (minimum or recommended)
        has_cpu = False
        has_gpu = False
        has_ram = False
        has_storage = False
        has_directx = False

        for req_type in ["minimum", "recommended"]:
            req_data = game.get(req_type)
            if not req_data:
                continue
                
            new_req = dict(req_data)
            
            # CPUs
            cpu_raw = new_req.get("cpu_raw")
            cpu_norm = normalize_hardware_string(cpu_raw)
            new_req["cpu"] = cpu_norm
            if cpu_norm:
                has_cpu = True
                
            # GPUs
            gpu_raw = new_req.get("gpu_raw")
            gpu_norm = normalize_hardware_string(gpu_raw)
            new_req["gpu"] = gpu_norm
            if gpu_norm:
                has_gpu = True
                
            # RAM
            ram_raw = new_req.get("ram_raw")
            ram_norm = extract_integer_field(ram_raw, check_mb=True)
            new_req["ram_gb"] = ram_norm
            if ram_norm is not None:
                has_ram = True
                
            # Storage
            storage_raw = new_req.get("storage_raw")
            storage_norm = extract_integer_field(storage_raw, check_mb=True)
            new_req["storage_gb"] = storage_norm
            if storage_norm is not None:
                has_storage = True
                
            # DirectX
            dx_raw = new_req.get("directx_raw")
            dx_norm = extract_integer_field(dx_raw, check_mb=False)
            new_req["directx"] = dx_norm
            if dx_norm is not None:
                has_directx = True
                
            # Overwrite the requirement object with our augmented version
            new_game[req_type] = new_req
            
        # Update validation counters
        if has_cpu: stats["cpu"] += 1
        if has_gpu: stats["gpu"] += 1
        if has_ram: stats["ram"] += 1
        if has_storage: stats["storage"] += 1
        if has_directx: stats["directx"] += 1
            
        normalized_games.append(new_game)
        
    save_json(NORMALIZED_FILE, normalized_games)
    
    print("\n====================================")
    print("NORMALIZATION COMPLETE")
    print(f"Total Games Processed: {total_games}")
    print(f"Games with CPUs extracted: {stats['cpu']}")
    print(f"Games with GPUs extracted: {stats['gpu']}")
    print(f"Games with RAM extracted: {stats['ram']}")
    print(f"Games with Storage extracted: {stats['storage']}")
    print(f"Games with DirectX extracted: {stats['directx']}")
    print(f"Saved to: {NORMALIZED_FILE}")
    print("====================================")

if __name__ == "__main__":
    main()
