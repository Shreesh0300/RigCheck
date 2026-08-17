import json
import random

db = json.load(open('data/games_database_final.json', encoding='utf-8'))
new_games = db[-250:]

# Let's handpick 5 recognizable games that have good data
# Wait, I'll just print 10 and pick 5 manually.
random.seed(45)
sample = random.sample(new_games, 20)

for g in sample:
    name = g.get('name')
    price = g.get('price_overview', {}).get('final', 0) // 100
    if not price and g.get('price_inr'):
        price = g.get('price_inr')
    ram = g.get('minimum', {}).get('ram_gb', 0)
    storage = g.get('minimum', {}).get('storage_gb', 0)
    desc = g.get('about_the_game', '')[:200]
    
    print(f"NAME: {name}")
    print(f"PRICE: {price}")
    print(f"RAM: {ram}")
    print(f"STORAGE: {storage}")
    print(f"DESC: {desc}")
    print("-" * 40)
