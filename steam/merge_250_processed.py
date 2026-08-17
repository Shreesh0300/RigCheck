import os, json
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')

def main():
    final_db_file = os.path.join(DATA_DIR, 'games_database_final.json')
    backup_file = os.path.join(DATA_DIR, 'games_database_final_BACKUP.json')
    
    # 1. Load the 500 games
    old_games = json.load(open(backup_file, encoding='utf-8'))
    print(f"Old games count: {len(old_games)}")
    
    # 2. Load the 250 newly processed games from final DB
    # (Since 04,05,06,07 process games_database.json -> games_database_final.json,
    # games_database_final.json now ONLY contains the 250 new processed games!)
    new_games = json.load(open(final_db_file, encoding='utf-8'))
    print(f"New games count: {len(new_games)}")
    
    # 3. Merge
    old_games.extend(new_games)
    
    # 4. Save
    with open(final_db_file, 'w', encoding='utf-8') as f:
        json.dump(old_games, f, indent=4, ensure_ascii=False)
        
    print(f"Merge complete! Final count: {len(old_games)}")
    
if __name__ == '__main__':
    main()
