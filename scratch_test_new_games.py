import json
from model.rigcheck_engine import recommend_game, df

with open('data/games_database_final.json', 'r', encoding='utf-8') as f:
    new_db = json.load(f)
with open('data/games_database_final_BACKUP.json', 'r', encoding='utf-8') as f:
    old_db = json.load(f)

old_ids = {g['appid'] for g in old_db}
new_games = [g for g in new_db if g['appid'] not in old_ids]
print(f'Found {len(new_games)} new games.')

queries = []
for g in new_games[:10]:
    name = g['name']
    print(f"- {name} ({g['appid']})")
    queries.append(name)

print("\n--- Testing queries for new games ---")
for q in queries:
    payload = {
        'user_input': q,
        'budget': 10000,
        'gpu_name': 'RTX 4070',
        'ram': 16,
        'cpu_name': 'Ryzen 5 5600X',
        'storage_gb': 1000
    }
    res = recommend_game(**payload)
    print(f"Query: {q}")
    print(f"Recommended: {res.get('recommended_game')} ({res.get('confidence')})")
