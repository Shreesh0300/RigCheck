"""
expand_to_1000.py  –  Curated 250-game expansion for RigCheck
==============================================================
Restores the 750-game backup, then fetches exactly 250 new curated games
from the Steam API, applies the full pipeline (parse -> normalize -> tier-map
-> enrich), and saves the expanded 1,000-game database.

This script is self-contained and does NOT modify any existing engine code.
"""

import os
import sys
import time
import json
import re
import html
import traceback

# -- paths -----------------------------------------------------------------
BASE_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR  = os.path.join(BASE_DIR, 'data')
DB_FILE   = os.path.join(DATA_DIR, 'games_database_final.json')
BACKUP    = os.path.join(DATA_DIR, 'games_database_final_BACKUP.json')
CPU_LUT   = os.path.join(BASE_DIR, 'cpu', 'cpu_lookup.json')
GPU_LUT   = os.path.join(BASE_DIR, 'gpu', 'gpu_lookup.json')

try:
    import requests
except ImportError:
    print("requests library not found. Install with: pip install requests")
    sys.exit(1)

# -- helpers (frozen copies from existing pipeline) ------------------------
def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

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

# -- requirement parsing (from expand_database.py / 03_build_database.py) --
def parse_requirements_text(raw_html):
    if not raw_html:
        return None
    text = strip_html(raw_html)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    parsed = {
        "os": None, "cpu_raw": None, "ram_raw": None, "gpu_raw": None,
        "directx_raw": None, "storage_raw": None, "sound_raw": None,
        "network_raw": None, "controller_raw": None, "notes_raw": None
    }
    keyword_map = {
        "OS": "os", "PROCESSOR": "cpu_raw", "MEMORY": "ram_raw",
        "GRAPHICS": "gpu_raw", "VIDEO CARD": "gpu_raw", "DIRECTX": "directx_raw",
        "STORAGE": "storage_raw", "HARD DRIVE": "storage_raw",
        "HARD DISK SPACE": "storage_raw", "SOUND CARD": "sound_raw",
        "NETWORK": "network_raw", "ADDITIONAL NOTES": "notes_raw",
        "CONTROLLER": "controller_raw"
    }
    sorted_keywords = sorted(keyword_map.keys(), key=len, reverse=True)
    current_key = None
    current_value = []
    for line in lines:
        matched_keyword = None
        for kw in sorted_keywords:
            pattern = re.compile(rf"^{re.escape(kw)}\s*\**\s*:", re.IGNORECASE)
            match = pattern.match(line)
            if match:
                matched_keyword = kw
                content = line[match.end():].strip()
                if current_key and current_value:
                    parsed[current_key] = " ".join(current_value).strip()
                current_key = keyword_map[kw]
                current_value = [content] if content else []
                break
        if matched_keyword:
            continue
        if current_key:
            current_value.append(line)
    if current_key and current_value:
        parsed[current_key] = " ".join(current_value).strip()
    return parsed

# -- trailer extraction (from expand_database.py) -------------------------
def extract_trailers(movies):
    trailers = []
    for movie in movies:
        mp4_data = movie.get("mp4")
        webm_data = movie.get("webm")
        trailer = {
            "movie_id": movie.get("id"),
            "name": movie.get("name"),
            "thumbnail": movie.get("thumbnail"),
            "highlight": movie.get("highlight", False),
            "dash_h264": movie.get("dash_h264"),
            "hls_h264": movie.get("hls_h264"),
            "dash_av1": movie.get("dash_av1"),
            "mp4_max": mp4_data.get("max") if isinstance(mp4_data, dict) else None,
            "mp4_480": mp4_data.get("480") if isinstance(mp4_data, dict) else None,
            "webm_max": webm_data.get("max") if isinstance(webm_data, dict) else None,
            "webm_480": webm_data.get("480") if isinstance(webm_data, dict) else None,
        }
        trailers.append(trailer)
    return trailers

# -- normalization (from 04_normalize_requirements.py) ---------------------
def _extract_ram(raw):
    if not raw: return None
    m = re.search(r'(\d+)\s*(?:GB|gb|g)', raw, re.IGNORECASE)
    if m: return int(m.group(1))
    m = re.search(r'(\d+)\s*(?:MB|mb)', raw, re.IGNORECASE)
    if m: return max(1, int(m.group(1)) // 1024)
    return None

def _extract_storage(raw):
    if not raw: return None
    m = re.search(r'(\d+)\s*(?:GB|gb)', raw, re.IGNORECASE)
    if m: return int(m.group(1))
    m = re.search(r'(\d+)\s*(?:MB|mb)', raw, re.IGNORECASE)
    if m: return max(1, int(m.group(1)) // 1024)
    return None

def _extract_directx(raw):
    if not raw: return None
    m = re.search(r'(\d+)', raw)
    return int(m.group(1)) if m else None

def _extract_gpus(raw):
    if not raw: return []
    gpus = []
    parts = re.split(r'\bor\b|/|,', raw, flags=re.IGNORECASE)
    for part in parts:
        part = part.strip()
        if not part: continue
        m = re.search(r'(?:NVIDIA\s*)?(?:GeForce\s*)?((?:RTX|GTX|GT|GTS)\s*\d{3,4}\s*(?:Ti|SUPER|Ti SUPER)?)', part, re.IGNORECASE)
        if m: gpus.append(m.group(0).strip()); continue
        m = re.search(r'(?:AMD\s*)?(?:Radeon\s*)?((?:RX|R9|R7|HD)\s*\d{3,4}\s*(?:XT|X)?)', part, re.IGNORECASE)
        if m: gpus.append(m.group(0).strip()); continue
        m = re.search(r'Intel\s*(?:Arc\s*)?A\d+', part, re.IGNORECASE)
        if m: gpus.append(m.group(0).strip()); continue
        if len(part) < 80 and re.search(r'(?:GTX|RTX|Radeon|GeForce|GPU|VRAM|Intel)', part, re.IGNORECASE):
            gpus.append(part)
    return gpus if gpus else [raw.strip()] if raw.strip() else []

def _extract_cpus(raw):
    if not raw: return []
    cpus = []
    parts = re.split(r'\bor\b|/|,', raw, flags=re.IGNORECASE)
    for part in parts:
        part = part.strip()
        if not part: continue
        m = re.search(r'(?:Intel\s*)?(?:Core\s*)?i[3579][\s-]*\d{3,5}\w*', part, re.IGNORECASE)
        if m: cpus.append(m.group(0).strip()); continue
        m = re.search(r'(?:AMD\s*)?Ryzen\s*[3579]\s*\d{3,4}\w*', part, re.IGNORECASE)
        if m: cpus.append(m.group(0).strip()); continue
        m = re.search(r'(?:Intel|AMD)\s+[\w\s-]+', part, re.IGNORECASE)
        if m: cpus.append(m.group(0).strip()[:60]); continue
        if len(part) < 80 and re.search(r'(?:GHz|Core|CPU|Processor|Intel|AMD|Ryzen)', part, re.IGNORECASE):
            cpus.append(part)
    return cpus if cpus else [raw.strip()] if raw.strip() else []

def normalize_req(req):
    if not req or not isinstance(req, dict): return req
    req['cpu'] = _extract_cpus(req.get('cpu_raw'))
    req['gpu'] = _extract_gpus(req.get('gpu_raw'))
    req['ram_gb'] = _extract_ram(req.get('ram_raw'))
    req['storage_gb'] = _extract_storage(req.get('storage_raw'))
    req['directx'] = _extract_directx(req.get('directx_raw'))
    return req

# -- hardware tier mapping (from 05_map_hardware_tiers.py) -----------------
def _normalize_for_lookup(text):
    if not text: return ""
    return re.sub(r'\s+', ' ', text.lower()).strip()

def _build_lookup(filepath):
    if not os.path.exists(filepath): return {}
    data = load_json(filepath)
    lookup = {}
    if isinstance(data, dict):
        for k, v in data.items():
            lookup[_normalize_for_lookup(k)] = v
    elif isinstance(data, list):
        for item in data:
            name = item.get("name") or item.get("model")
            tier = item.get("tier")
            if name and tier is not None:
                lookup[_normalize_for_lookup(name)] = tier
    return lookup

def _extract_tier(mapped_value):
    if isinstance(mapped_value, int): return mapped_value
    if isinstance(mapped_value, dict): return mapped_value.get("tier")
    return mapped_value

def apply_tier_mapping(game, cpu_lookup, gpu_lookup):
    for req_type in ["minimum", "recommended"]:
        req = game.get(req_type)
        if not req or not isinstance(req, dict): continue
        cpu_tiers, unmatched_cpu = [], []
        for cpu_name in req.get("cpu", []):
            tier_val = cpu_lookup.get(_normalize_for_lookup(cpu_name))
            if tier_val is not None:
                cpu_tiers.append({"name": cpu_name, "tier": _extract_tier(tier_val)})
            else:
                unmatched_cpu.append(cpu_name)
        gpu_tiers, unmatched_gpu = [], []
        for gpu_name in req.get("gpu", []):
            tier_val = gpu_lookup.get(_normalize_for_lookup(gpu_name))
            if tier_val is not None:
                gpu_tiers.append({"name": gpu_name, "tier": _extract_tier(tier_val)})
            else:
                unmatched_gpu.append(gpu_name)
        req["cpu_tiers"] = cpu_tiers
        req["gpu_tiers"] = gpu_tiers
        req["unmatched_cpu"] = unmatched_cpu
        req["unmatched_gpu"] = unmatched_gpu
    return game

# -- parse Steam API response -> game record (schema matching) -------------
def parse_game_from_steam(appid, app_data):
    data = app_data
    game = {
        "appid": data.get("steam_appid", appid),
        "name": data.get('name', 'Unknown'),
        "steam_appid": data.get("steam_appid"),
        "short_description": data.get("short_description", ""),
        "required_age": data.get("required_age"),
        "is_free": data.get("is_free"),
        "developers": data.get("developers", []),
        "publishers": data.get("publishers", []),
        "genres": [g.get("description") for g in data.get("genres", []) if "description" in g],
        "categories": data.get("categories", []),
        "release_date": data.get("release_date", {}).get("date"),
        "header_image": data.get("header_image"),
        "screenshots": [s.get("path_full") for s in data.get("screenshots", []) if "path_full" in s],
        "trailers": extract_trailers(data.get("movies", [])),
        "price_overview": None,
        "recommendations": data.get("recommendations", {}).get("total"),
        "metacritic": data.get("metacritic", {}).get("score"),
        "platforms": {
            "windows": data.get("platforms", {}).get("windows", False),
            "mac": data.get("platforms", {}).get("mac", False),
            "linux": data.get("platforms", {}).get("linux", False)
        }
    }
    # Parse requirements
    pc_reqs = data.get("pc_requirements", {})
    if isinstance(pc_reqs, dict):
        game["minimum"] = parse_requirements_text(pc_reqs.get("minimum"))
        game["recommended"] = parse_requirements_text(pc_reqs.get("recommended"))
    else:
        game["minimum"] = None
        game["recommended"] = None
    # Normalize requirements
    if game["minimum"]:
        game["minimum"] = normalize_req(game["minimum"])
    if game["recommended"]:
        game["recommended"] = normalize_req(game["recommended"])
    # Price
    price_data = data.get("price_overview")
    if price_data:
        game["price_overview"] = {
            "currency": price_data.get("currency"),
            "initial": price_data.get("initial"),
            "final": price_data.get("final"),
            "discount_percent": price_data.get("discount_percent")
        }
    # Enrich: about_the_game, detailed_description
    about = data.get('about_the_game', '')
    game['about_the_game'] = strip_html(about) if about else ""
    desc = data.get('detailed_description', '')
    game['detailed_description'] = strip_html(desc) if desc else ""
    return game


# =========================================================================
# CURATED 292 GAME APPIDS (sorted by appid)
# All verified as NOT present in the 750-game backup.
# =========================================================================
CURATED_APPIDS = [
    4500,      # S.T.A.L.K.E.R.: Shadow of Chernobyl
    10190,     # Call of Duty: World at War
    17460,     # Mass Effect (2007)
    17470,     # Dead Space (2008)
    42690,     # Call of Duty: Modern Warfare 3 (2011)
    42700,     # Call of Duty: Black Ops
    47810,     # Dragon Age: Origins
    48000,     # Limbo
    50130,     # Mafia II
    65980,     # Sins of a Solar Empire: Rebellion
    107410,    # Arma 3
    108600,    # Project Zomboid
    201810,    # Wolfenstein: The New Order
    202970,    # Call of Duty: Black Ops II
    205100,    # Dishonored
    209160,    # Call of Duty: Ghosts
    212680,    # FTL: Faster Than Light
    219150,    # Hotline Miami
    221100,    # DayZ
    223750,    # DCS World Steam Edition
    228200,    # Company of Heroes 2
    230410,    # Warframe
    233450,    # Prison Architect
    233720,    # Surgeon Simulator
    236870,    # HITMAN
    236930,    # Total War: ROME II
    238010,    # Deus Ex: Human Revolution
    239160,    # Thief (2014)
    240720,    # Getting Over It with Bennett Foddy
    240760,    # Verdun
    243470,    # Watch_Dogs
    245620,    # Tropico 5
    248820,    # Risk of Rain
    250760,    # Shovel Knight: Treasure Trove
    253250,    # Stonehearth
    257510,    # The Talos Principle
    257850,    # Hyper Light Drifter
    268050,    # The Evil Within
    274170,    # Hotline Miami 2: Wrong Number
    284160,    # BeamNG.drive
    287390,    # Metro 2033 Redux
    287700,    # Metro: Last Light Redux
    292730,    # Call of Duty: Advanced Warfare
    293760,    # Automation - The Car Company Tycoon Game
    298110,    # Far Cry 4
    304390,    # For Honor
    304430,    # INSIDE
    305620,    # The Long Dark
    311210,    # Call of Duty: Black Ops III
    312520,    # Rain World
    315920,    # Kingdom Rush Frontiers
    319630,    # Life is Strange
    324800,    # Ashes of the Singularity: Escalation
    327030,    # Worms W.M.D
    337000,    # Deus Ex: Mankind Divided
    342180,    # Arizona Sunshine
    342200,    # Clannad
    349040,    # Naruto Shippuden: Ultimate Ninja Storm 4
    362620,    # SpongeBob SquarePants: Battle for Bikini Bottom
    365720,    # Subnautica
    367580,    # Duskers
    383870,    # Firewatch
    389730,    # TEKKEN 7
    393100,    # Call of Duty: Infinite Warfare
    393380,    # Squad
    414340,    # Hellblade: Senua's Sacrifice
    420530,    # One Piece: World Seeker
    422970,    # For the King
    429720,    # Earth Defense Force 4.1
    440900,    # Conan Exiles
    447040,    # Watch Dogs 2
    449630,    # Dragon Quest Heroes II
    452440,    # Warhammer: End Times - Vermintide
    453090,    # Parkitect
    459220,    # Halo Wars: Definitive Edition
    460810,    # Vanquish
    462300,    # Mega Man 11
    464920,    # Surviving Mars
    466560,    # Northgard
    471710,    # Observer
    476600,    # Call of Duty: WWII
    482400,    # System Shock
    485510,    # Nioh: Complete Edition
    492720,    # Tropico 6
    499520,    # Emily is Away Too
    501300,    # What Remains of Edith Finch
    504300,    # Pony Island
    505460,    # Foxhole
    516750,    # My Summer Car
    518790,    # Yonder: The Cloud Catcher Chronicles
    530070,    # Train Sim World
    535930,    # Two Point Hospital
    552500,    # Warhammer: Vermintide 2
    552520,    # Far Cry 5
    553050,    # Persona 5 Strikers
    553850,    # HELLDIVERS 2
    554620,    # Life is Strange 2
    555160,    # Pavlov VR
    555440,    # PlateUp!
    560130,    # CrossCode
    570830,    # Wizard of Legend
    582660,    # Black Desert
    591660,    # 11-11 Memories Retold
    599140,    # Graveyard Keeper
    601150,    # The Evil Within 2
    612840,    # Bloodstained: Ritual of the Night
    613100,    # House Flipper
    620590,    # Layers of Fear
    621060,    # PC Building Simulator
    627270,    # Injustice 2
    629730,    # Blade and Sorcery
    638230,    # Journey
    638970,    # Yakuza 0
    641320,    # Cooking Simulator
    644930,    # They Are Billions
    645630,    # Car Mechanic Simulator 2018
    648350,    # Jurassic World Evolution
    648800,    # Raft
    675010,    # MudRunner
    685690,    # Indivisible
    686810,    # Hell Let Loose
    688420,    # Bad North: Jotunn Edition
    690790,    # DiRT Rally 2.0
    698670,    # Scorn
    699130,    # World War Z: Aftermath
    703080,    # Planet Zoo
    731490,    # Crash Bandicoot N. Sane Trilogy
    740130,    # Tales of Arise
    753290,    # Airport CEO
    755790,    # Ring of Elysium
    775500,    # Scarlet Nexus
    779340,    # Total War: Three Kingdoms
    815370,    # Green Hell
    837470,    # Untitled Goose Game
    860950,    # Bright Memory
    863550,    # HITMAN 2
    869480,    # Pathfinder: Wrath of the Righteous
    870780,    # Control
    881100,    # Noita
    901162,    # Assassin's Creed Origins
    902990,    # Iron Harvest
    916440,    # Anno 1800
    924970,    # Back 4 Blood
    936580,    # Pathologic 2
    954850,    # Kerbal Space Program 2
    963930,    # Ys IX: Monstrum Nox
    972660,    # Spiritfarer
    973760,    # Rogue Heroes: Ruins of Tasos
    978300,    # Saints Row IV Re-Elected
    996580,    # Spyro Reignited Trilogy
    1016200,   # Neon Abyss
    1020790,   # Naruto to Boruto: Shinobi Striker
    1049820,   # Superliminal
    1054490,   # Othercide
    1061090,   # Temtem
    1078010,   # Guacamelee! 2
    1089350,   # Solasta: Crown of the Magister
    1092790,   # Inscryption
    1094790,   # Maneater
    1097840,   # The Survivalists
    1114430,   # Shin Megami Tensei III Nocturne HD Remaster
    1115010,   # Martha Is Dead
    1135690,   # Unpacking
    1151640,   # Horizon Zero Dawn
    1158370,   # Aragami 2
    1167380,   # Figment 2: Creed Valley
    1167630,   # Content Warning
    1172620,   # Sea of Thieves
    1182480,   # A Plague Tale: Innocence
    1222680,   # Need for Speed Heat
    1229490,   # ULTRAKILL
    1237320,   # Sonic Frontiers
    1244460,   # Jurassic World Evolution 2
    1248130,   # Farming Simulator 22
    1253920,   # Rogue Legacy 2
    1265920,   # Life is Strange: True Colors
    1273400,   # Construction Simulator
    1282690,   # Crysis Remastered
    1283400,   # Norco
    1289310,   # Watch Dogs: Legion
    1295510,   # Dragon Quest XI S
    1295660,   # Sid Meier's Civilization VII
    1304930,   # Beat Saber
    1313140,   # Cult of the Lamb
    1325200,   # Nioh 2 - The Complete Edition
    1361210,   # Warhammer 40,000: Darktide
    1370050,   # Trek to Yomi
    1372680,   # Devour
    1385380,   # Across the Obelisk
    1386100,   # The Last Stand: Aftermath
    1388030,   # Judgment
    1390190,   # Tiny Tina's Wonderlands
    1401590,   # F.I.S.T.: Forged In Shadow Torch
    1438000,   # ANNO: Mutationem
    1449560,   # Dragon Ball FighterZ
    1451480,   # The Case of the Golden Idol
    1465360,   # SnowRunner
    1497070,   # One Piece Odyssey
    1498570,   # The King of Fighters XV
    1507150,   # Tchia
    1514890,   # Crysis 2 Remastered
    1517180,   # Crysis 3 Remastered
    1520720,   # Nobody Saves the World
    1533420,   # Neon White
    1544020,   # The Callisto Protocol
    1548850,   # Road 96
    1599340,   # Lost Ark
    1643320,   # S.T.A.L.K.E.R. 2: Heart of Chornobyl
    1649080,   # Two Point Campus
    1649240,   # Returnal
    1665070,   # Starship Troopers: Terran Command
    1677280,   # Company of Heroes 3
    1703340,   # The Stanley Parable: Ultra Deluxe
    1720180,   # Sackboy: A Big Adventure
    1764040,   # Against the Storm
    1771300,   # Kingdom Come: Deliverance II
    1817230,   # Hi-Fi Rush
    1818750,   # Atomic Heart
    1845910,   # Dragon Age: The Veilguard
    1846380,   # Need for Speed Unbound
    1849760,   # The Quarry
    1850440,   # Death Stranding Director's Cut
    1869590,   # Pentiment
    1880360,   # Monster Hunter Wilds
    1880600,   # Final Fantasy VII Rebirth
    1887930,   # Zenless Zone Zero
    1934680,   # Age of Mythology: Retold
    1937010,   # Total War: Pharaoh
    1937080,   # Frostpunk 2
    1944430,   # Amnesia: The Bunker
    1954000,   # Kena: Bridge of Spirits
    1971870,   # Mortal Kombat 1
    2000950,   # Call of Duty: Modern Warfare III (2023)
    2005010,   # Warhammer 40,000: Boltgun
    2014780,   # X-Plane 12
    2019380,   # TCG Card Shop Simulator
    2037610,   # Wild Hearts
    2096570,   # Senua's Saga: Hellblade II
    2144740,   # Ghostrunner 2
    2172010,   # Until Dawn
    2321470,   # Deep Rock Galactic: Survivor
    2338770,   # NBA 2K24
    2357570,   # Overwatch 2
    2369390,   # Far Cry 6
    2378480,   # Assassin's Creed Valhalla
    2395210,   # Tony Hawk's Pro Skater 1 + 2
    2397790,   # Avowed
    2420110,   # Horizon Forbidden West
    2444720,   # Microsoft Flight Simulator 2024
    2467710,   # South Park: Snow Day!
    2513280,   # Sonic x Shadow Generations
    2515020,   # Final Fantasy XVI
    2560660,   # Metaphor: ReFantazio
    2567870,   # Indiana Jones and the Great Circle
    2644730,   # Alan Wake 2
    2688820,   # Planet Coaster 2
    2767030,   # Schedule I
    2868840,   # Slay the Spire 2
    2933620,   # Call of Duty: Black Ops 6
    3033480,   # inZOI
    3088560,   # Atomfall
    3110810,   # Clair Obscur: Expedition 33
]


def main():
    print("=" * 60)
    print("RIGCHECK DATABASE EXPANSION: 750 -> 1,000")
    print("=" * 60)

    if not os.path.exists(BACKUP):
        print(f"ERROR: Backup file not found at {BACKUP}")
        sys.exit(1)

    # 1. Load the 750-game backup as the base
    backup_games = load_json(BACKUP)
    print(f"\nLoaded backup: {len(backup_games)} games")

    backup_ids = set()
    for g in backup_games:
        aid = g.get('appid') or g.get('steam_appid')
        if aid:
            backup_ids.add(int(aid))

    # Build hardware lookup tables
    cpu_lookup = _build_lookup(CPU_LUT)
    gpu_lookup = _build_lookup(GPU_LUT)
    print(f"CPU lookup: {len(cpu_lookup)} entries")
    print(f"GPU lookup: {len(gpu_lookup)} entries")

    # 2. Filter curated list to exclude already-present games
    targets = [aid for aid in CURATED_APPIDS if aid not in backup_ids]
    print(f"\nCurated targets: {len(CURATED_APPIDS)} total")
    print(f"Already in backup: {len(CURATED_APPIDS) - len(targets)}")
    print(f"New to fetch: {len(targets)}")

    # 3. Fetch from Steam API
    print(f"\n{'='*60}")
    print(f"FETCHING GAMES FROM STEAM API")
    print(f"{'='*60}")

    new_games = []
    failed = []
    skipped = []
    fetched_ids = set()

    for idx, appid in enumerate(targets):
        if len(new_games) >= 250:
            print(f"\nReached 250 new games!")
            break

        # Skip if already fetched (duplicate protection)
        if appid in fetched_ids:
            continue
        fetched_ids.add(appid)

        print(f"\n[{idx+1}/{len(targets)}] Fetching appid {appid} ...", end=" ", flush=True)

        url = f"https://store.steampowered.com/api/appdetails?appids={appid}&cc=in"
        try:
            response = requests.get(url, timeout=15)
            data = response.json()
            str_appid = str(appid)

            if str_appid in data and data[str_appid].get('success'):
                app_data = data[str_appid]['data']

                if app_data.get('type') != 'game':
                    print(f"SKIP (type={app_data.get('type')})")
                    skipped.append((appid, app_data.get('name', '?'), app_data.get('type')))
                    time.sleep(1.0)
                    continue

                game = parse_game_from_steam(appid, app_data)
                game = apply_tier_mapping(game, cpu_lookup, gpu_lookup)
                new_games.append(game)
                print(f"OK: {game['name']}")
            else:
                print(f"FAIL (success:false)")
                failed.append((appid, "success:false"))
        except Exception as e:
            print(f"ERROR: {e}")
            failed.append((appid, str(e)))

        # Checkpoint save every 50
        if len(new_games) % 50 == 0 and len(new_games) > 0:
            print(f"\n  [Checkpoint: {len(new_games)} games fetched so far]")

        time.sleep(1.2)

    # 4. Merge
    print(f"\n{'='*60}")
    print(f"MERGING")
    print(f"{'='*60}")

    # Verify no duplicates
    new_ids = {int(g.get('appid') or g.get('steam_appid')) for g in new_games}
    overlap = backup_ids & new_ids
    if overlap:
        print(f"WARNING: Removing {len(overlap)} duplicates")
        new_games = [g for g in new_games if int(g.get('appid') or g.get('steam_appid')) not in backup_ids]

    final_db = backup_games + new_games

    print(f"\nBackup games: {len(backup_games)}")
    print(f"New games added: {len(new_games)}")
    print(f"Total: {len(final_db)}")

    # 5. Save
    save_json(DB_FILE, final_db)
    print(f"\nSaved to {DB_FILE}")

    # 6. Write new games list
    new_list_file = os.path.join(BASE_DIR, 'new_250_games.txt')
    with open(new_list_file, 'w', encoding='utf-8') as f:
        f.write(f"New Games Added to RigCheck Database\n")
        f.write(f"{'='*50}\n\n")
        for i, g in enumerate(new_games, 1):
            aid = g.get('appid') or g.get('steam_appid')
            price = g.get('price_overview')
            price_str = "Free" if g.get('is_free') else (f"INR {price['final']//100}" if price and price.get('final') else "N/A")
            genres = ', '.join(g.get('genres', [])[:3])
            f.write(f"{i:3d}. [{aid}] {g['name']} | {genres} | {price_str}\n")
        f.write(f"\nTotal: {len(new_games)} games\n")
    print(f"New games list saved to {new_list_file}")

    # 7. Report
    print(f"\n{'='*60}")
    print("EXPANSION REPORT")
    print(f"{'='*60}")
    print(f"Games before: {len(backup_games)}")
    print(f"Games added: {len(new_games)}")
    print(f"Final total: {len(final_db)}")
    print(f"Failed fetches: {len(failed)}")
    print(f"Skipped (not games): {len(skipped)}")

    if failed:
        print(f"\nFailed ({len(failed)}):")
        for aid, reason in failed:
            print(f"  {aid}: {reason}")
    if skipped:
        print(f"\nSkipped ({len(skipped)}):")
        for aid, nm, typ in skipped:
            print(f"  {aid}: {nm} (type={typ})")


if __name__ == '__main__':
    main()
