import requests
import json
import time

URL = "http://127.0.0.1:8000/recommend"

queries = [
    "payday 2",
    "left 4 dead 2",
    "games like gta 5",
    "games like rdr2",
    "games like skyrim",
    "games like fallout",
    "games like minecraft",
    "cybeprunk 2077",
    "fun games to play with friends",
    "good story games",
    "open world games",
    "cheap open world games for a potato pc"
]

results_log = []

for q in queries:
    payload = {
        "description": q,
        "budget": 99999,
        "gpu_name": "RTX 4090",
        "ram": 64,
        "cpu_name": "Core i9",
        "storage_gb": 1000
    }
    if "cheap" in q and "potato" in q:
        payload["budget"] = 500
        payload["gpu_name"] = "GTX 1050"
        payload["ram"] = 4
        payload["cpu_name"] = "Core i3"
        payload["storage_gb"] = 100
        
    try:
        resp = requests.post(URL, json=payload)
        data = resp.json()
        top_games = []
        if data and "title" in data:
            top_games.append(data["title"])
            top_games.extend([g["title"] for g in data.get("recommendations", [])[:4]])
        results_log.append({
            "query": q,
            "top_5": top_games
        })
    except Exception as e:
        results_log.append({
            "query": q,
            "error": str(e)
        })
    time.sleep(0.5)

with open("regression_results.json", "w", encoding="utf-8") as f:
    json.dump(results_log, f, indent=4)
print("Regression tests completed.")
