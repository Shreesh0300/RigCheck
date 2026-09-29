"""
validate_expansion.py  –  Post-expansion validation
=====================================================
Validates the expanded 1,000-game database against all requirements.
"""
import json
import os
from collections import Counter

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_FILE = os.path.join(DATA_DIR, 'games_database_final.json')
BACKUP = os.path.join(DATA_DIR, 'games_database_final_BACKUP.json')

def main():
    print("=" * 60)
    print("POST-EXPANSION VALIDATION")
    print("=" * 60)

    db = json.load(open(DB_FILE, 'r', encoding='utf-8'))
    backup = json.load(open(BACKUP, 'r', encoding='utf-8'))
    
    backup_ids = {int(g.get('appid') or g.get('steam_appid')) for g in backup}
    final_ids = {int(g.get('appid') or g.get('steam_appid')) for g in db}
    
    new_games = [g for g in db if int(g.get('appid') or g.get('steam_appid')) not in backup_ids]
    
    print(f"\n1. GAME COUNTS")
    print(f"   Backup (original): {len(backup)}")
    print(f"   Final database: {len(db)}")
    print(f"   New games added: {len(new_games)}")
    total_ok = len(db) == 1000
    print(f"   Total = 1000? {'PASS' if total_ok else 'FAIL'}")
    
    print(f"\n2. EXISTING 750 PRESERVED")
    preserved = all(bid in final_ids for bid in backup_ids)
    missing = backup_ids - final_ids
    print(f"   All 750 present? {'PASS' if preserved else 'FAIL'}")
    if missing:
        print(f"   Missing IDs: {missing}")
    
    print(f"\n3. DUPLICATE APPIDS")
    all_ids = [int(g.get('appid') or g.get('steam_appid')) for g in db]
    dupes = {k: v for k, v in Counter(all_ids).items() if v > 1}
    print(f"   Duplicate AppIDs: {'None - PASS' if not dupes else f'FAIL - {dupes}'}")
    
    print(f"\n4. DUPLICATE NAMES")
    all_names = [g['name'] for g in db if g.get('name')]
    name_dupes = {k: v for k, v in Counter(all_names).items() if v > 1}
    print(f"   Duplicate names: {'None - PASS' if not name_dupes else f'{len(name_dupes)} duplicates'}")
    if name_dupes:
        for nm, cnt in name_dupes.items():
            print(f"     {nm}: {cnt}x")
    
    print(f"\n5. SCHEMA CONSISTENCY")
    # Check required keys present in all games
    required_keys = {'appid', 'name', 'steam_appid', 'short_description', 'genres',
                     'categories', 'header_image', 'minimum', 'recommended',
                     'price_overview', 'platforms', 'about_the_game', 'detailed_description'}
    
    old_keys = set(backup[0].keys())
    issues = 0
    for g in new_games:
        gkeys = set(g.keys())
        # Extra keys are OK; missing required keys are not
        missing_required = required_keys - gkeys
        if missing_required:
            aid = g.get('appid') or g.get('steam_appid')
            print(f"   MISSING keys in {aid} ({g.get('name','')}): {missing_required}")
            issues += 1
    print(f"   Schema issues: {issues} {'- PASS' if issues == 0 else '- FAIL'}")
    
    print(f"\n6. FIELD COMPLETENESS (new 250 games)")
    fields = ['name', 'short_description', 'genres', 'categories', 'header_image',
              'minimum', 'recommended', 'price_overview', 'about_the_game',
              'detailed_description', 'trailers', 'platforms']
    for field in fields:
        present = sum(1 for g in new_games if g.get(field))
        pct = present / len(new_games) * 100 if new_games else 0
        print(f"   {field:30s}: {present:3d}/{len(new_games)} ({pct:.0f}%)")
    
    print(f"\n7. HARDWARE REQUIREMENTS (new games)")
    has_min_cpu_tiers = sum(1 for g in new_games if g.get('minimum') and isinstance(g['minimum'], dict) and g['minimum'].get('cpu_tiers'))
    has_min_gpu_tiers = sum(1 for g in new_games if g.get('minimum') and isinstance(g['minimum'], dict) and g['minimum'].get('gpu_tiers'))
    has_ram = sum(1 for g in new_games if g.get('minimum') and isinstance(g['minimum'], dict) and g['minimum'].get('ram_gb'))
    has_storage = sum(1 for g in new_games if g.get('minimum') and isinstance(g['minimum'], dict) and g['minimum'].get('storage_gb'))
    print(f"   Min CPU tiers: {has_min_cpu_tiers}/{len(new_games)}")
    print(f"   Min GPU tiers: {has_min_gpu_tiers}/{len(new_games)}")
    print(f"   RAM GB: {has_ram}/{len(new_games)}")
    print(f"   Storage GB: {has_storage}/{len(new_games)}")
    
    print(f"\n8. PRICE COMPATIBILITY (P2)")
    free_games = sum(1 for g in new_games if g.get('is_free'))
    with_price = sum(1 for g in new_games if g.get('price_overview') and isinstance(g['price_overview'], dict) and g['price_overview'].get('final'))
    inr_prices = sum(1 for g in new_games if g.get('price_overview') and isinstance(g['price_overview'], dict) and g['price_overview'].get('currency') == 'INR')
    no_price = sum(1 for g in new_games if not g.get('is_free') and not (g.get('price_overview') and isinstance(g['price_overview'], dict) and g['price_overview'].get('final')))
    print(f"   Free games: {free_games}")
    print(f"   With price data: {with_price}")
    print(f"   INR prices: {inr_prices}")
    print(f"   Missing price (non-free): {no_price}")
    
    print(f"\n9. GENRE DIVERSITY")
    all_genres = []
    for g in new_games:
        all_genres.extend(g.get('genres', []))
    genre_counts = Counter(all_genres)
    print(f"   Total genre tags: {len(all_genres)}")
    print(f"   Unique genres: {len(genre_counts)}")
    for genre, count in genre_counts.most_common(20):
        print(f"     {genre:30s}: {count}")
    
    # Overall verdict
    print(f"\n{'='*60}")
    all_pass = total_ok and preserved and not dupes and issues == 0
    print(f"OVERALL: {'ALL CHECKS PASSED' if all_pass else 'SOME CHECKS FAILED'}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
