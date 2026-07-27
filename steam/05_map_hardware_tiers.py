import os
import re
from utils import ensure_directory, load_json, save_json

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')

NORMALIZED_FILE = os.path.join(DATA_DIR, 'games_database_normalized.json')
FINAL_FILE = os.path.join(DATA_DIR, 'games_database_final.json')

CPU_LOOKUP_FILE = os.path.join(BASE_DIR, 'cpu', 'cpu_lookup.json')
GPU_LOOKUP_FILE = os.path.join(BASE_DIR, 'gpu', 'gpu_lookup.json')

def normalize_for_lookup(text):
    if not text:
        return ""
    # Standardize casing
    text = text.lower()
    # Collapse multiple spaces into a single space
    text = re.sub(r'\s+', ' ', text)
    # Trim leading and trailing whitespace
    return text.strip()

def build_lookup_dict(filepath):
    """
    Reads a lookup table JSON file and returns a flattened dictionary
    mapping normalized names to tiers for O(1) lookups.
    Supports either an object-based lookup {"model": tier}
    or array-based lookup [{"name": "model", "tier": tier}].
    """
    data = load_json(filepath)
    if not data:
        return {}
        
    lookup = {}
    if isinstance(data, dict):
        for k, v in data.items():
            lookup[normalize_for_lookup(k)] = v
    elif isinstance(data, list):
        for item in data:
            name = item.get("name") or item.get("model")
            tier = item.get("tier")
            if name and tier is not None:
                lookup[normalize_for_lookup(name)] = tier
                
    return lookup

def extract_tier(mapped_value):
    """Safely extracts the tier from the lookup table value."""
    if isinstance(mapped_value, int):
        return mapped_value
    elif isinstance(mapped_value, dict):
        return mapped_value.get("tier")
    return mapped_value

def main():
    ensure_directory(DATA_DIR)
    
    if not os.path.exists(NORMALIZED_FILE):
        print(f"File not found: {NORMALIZED_FILE}")
        return

    games = load_json(NORMALIZED_FILE)
    if not games:
        print("No games to process.")
        return

    # Build memory-efficient lookup tables
    cpu_lookup = build_lookup_dict(CPU_LOOKUP_FILE)
    gpu_lookup = build_lookup_dict(GPU_LOOKUP_FILE)
    
    if not cpu_lookup:
        print(f"WARNING: No CPU lookup data found at {CPU_LOOKUP_FILE}")
    if not gpu_lookup:
        print(f"WARNING: No GPU lookup data found at {GPU_LOOKUP_FILE}")

    total_games = len(games)
    final_games = []
    
    # Validation counters
    stats = {
        "matched_cpu": 0,
        "matched_gpu": 0,
        "unmatched_cpu": 0,
        "unmatched_gpu": 0,
        "games_complete": 0,
        "games_partial": 0,
        "games_no_map": 0
    }

    for i, game in enumerate(games):
        print(f"\n[{i + 1} / {total_games}]")
        print("Mapping Hardware Tiers")
        print(game.get('name', 'Unknown'))
        
        # Clone to preserve prior stage data exactly as is
        new_game = dict(game)
        
        game_total_hw = 0
        game_matched_hw = 0

        for req_type in ["minimum", "recommended"]:
            req = game.get(req_type)
            if not req:
                continue
                
            new_req = dict(req)
            
            # Map CPUs
            cpu_list = new_req.get("cpu", [])
            cpu_tiers = []
            unmatched_cpu = []
            
            for cpu_name in cpu_list:
                norm_name = normalize_for_lookup(cpu_name)
                tier_val = cpu_lookup.get(norm_name)
                
                if tier_val is not None:
                    cpu_tiers.append({
                        "name": cpu_name,
                        "tier": extract_tier(tier_val)
                    })
                    stats["matched_cpu"] += 1
                    game_matched_hw += 1
                else:
                    unmatched_cpu.append(cpu_name)
                    stats["unmatched_cpu"] += 1
                    
                game_total_hw += 1
                    
            # Map GPUs
            gpu_list = new_req.get("gpu", [])
            gpu_tiers = []
            unmatched_gpu = []
            
            for gpu_name in gpu_list:
                norm_name = normalize_for_lookup(gpu_name)
                tier_val = gpu_lookup.get(norm_name)
                
                if tier_val is not None:
                    gpu_tiers.append({
                        "name": gpu_name,
                        "tier": extract_tier(tier_val)
                    })
                    stats["matched_gpu"] += 1
                    game_matched_hw += 1
                else:
                    unmatched_gpu.append(gpu_name)
                    stats["unmatched_gpu"] += 1
                    
                game_total_hw += 1

            # Inject the new arrays into the requirement block
            new_req["cpu_tiers"] = cpu_tiers
            new_req["gpu_tiers"] = gpu_tiers
            new_req["unmatched_cpu"] = unmatched_cpu
            new_req["unmatched_gpu"] = unmatched_gpu
            
            new_game[req_type] = new_req
            
        # Determine mapping completion for this game
        if game_total_hw > 0:
            if game_matched_hw == game_total_hw:
                stats["games_complete"] += 1
            elif game_matched_hw == 0:
                stats["games_no_map"] += 1
            else:
                stats["games_partial"] += 1
            
        final_games.append(new_game)
        
    save_json(FINAL_FILE, final_games)
    
    print("\n====================================")
    print("HARDWARE MAPPING COMPLETE")
    print(f"Total Games Processed: {total_games}")
    print(f"Matched CPUs: {stats['matched_cpu']}")
    print(f"Matched GPUs: {stats['matched_gpu']}")
    print(f"Unmatched CPUs: {stats['unmatched_cpu']}")
    print(f"Unmatched GPUs: {stats['unmatched_gpu']}")
    print(f"Games with complete hardware mappings: {stats['games_complete']}")
    print(f"Games with partial mappings: {stats['games_partial']}")
    print(f"Games with no mappings: {stats['games_no_map']}")
    print(f"Saved to: {FINAL_FILE}")
    print("====================================")

if __name__ == "__main__":
    main()
