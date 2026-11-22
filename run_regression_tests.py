"""Run the original API scenarios in-process, or against a server with --url."""
import argparse
import json
from pathlib import Path

from model.steam_database import get_game_by_appid

# Pre-change results from 037695b: ordered (Steam App ID, confidence, compatibility %).
SCENARIOS = {
    "payday 2": [(218620, 99, 100), (1272080, 83, 100), (274170, 91, 100), (730, 42, 100)],
    "left 4 dead 2": [(550, 87, 100), (500, 99, 100), (924970, 89, 100), (1174180, 80, 100)],
    "games like gta 5": [(271590, 84, 100), (12220, 66, 100), (12210, 79, 100), (11390, 89, 100)],
    "games like rdr2": [(1174180, 99, 100), (207610, 75, 100), (550, 59, 100), (1200, 54, 100)],
    "games like skyrim": [(72850, 87, 100), (489830, 92, 100), (611670, 99, 100), (22330, 80, 100)],
    "games like fallout": [(22370, 48, 100), (588430, 52, 100), (377160, 66, 100), (240760, 48, 100)],
    "games like minecraft": [(40800, 58, 100)],
    "cybeprunk 2077": [(1091500, 77, 100), (2144740, 50, 100), (1139900, 38, 100), (1116170, 55, 100)],
    "fun games to play with friends": [(42700, 82, 100), (550, 82, 100), (1985810, 79, 100), (1938090, 76, 100)],
    "good story games": [(554620, 63, 100), (2054970, 58, 100), (294100, 38, 100), (1286830, 55, 100)],
    "open world games": [(1551360, 60, 100), (298110, 53, 100), (548570, 53, 100), (1465360, 52, 100)],
    "cheap open world games for a potato pc": [(298110, 65, 95), (518790, 60, 80), (2369390, 53, 68), (552520, 48, 82)],
}


def payload_for(query):
    payload = dict(description=query, budget=99999, gpu_name="RTX 4090", ram=64,
                   cpu_name="Core i9", storage_gb=1000)
    if "potato" in query:
        payload.update(budget=500, gpu_name="GTX 1050", ram=4, cpu_name="Core i3", storage_gb=100)
    return payload


def check_result(result, budget, expected):
    assert {"recommended_game", "hardware_advice", "matched_keywords", "alternative_games"} <= result.keys()
    assert isinstance(result["recommended_game"], str) and result["recommended_game"]
    assert isinstance(result["matched_keywords"], list)
    alternatives = result["alternative_games"]
    assert isinstance(alternatives, list) and len(alternatives) <= 3
    games = [(result["recommended_game"], result)]
    for alt in alternatives:
        assert isinstance(alt["tags"], list)
        games.append((alt["title"], alt))

    actual = []
    for title, game in games:
        assert {"appid", "price_inr", "description", "header_image", "confidence", "store_url", "compatibility"} <= game.keys()
        appid = game["appid"]
        assert type(appid) is int and appid > 0
        record = get_game_by_appid(appid)
        assert record and record["name"] == title, (appid, title)
        assert 0 <= game["price_inr"] <= budget
        assert type(game["confidence"]) is int and 0 <= game["confidence"] <= 100
        compat = game["compatibility"]
        assert {"gpu", "cpu", "ram", "storage", "compatibility_pct", "estimated_fps",
                "expected_settings", "reduction_reasons"} <= compat.keys()
        actual.append((appid, game["confidence"], compat["compatibility_pct"]))
    assert actual == expected, f"expected {expected}, received {actual}"
    return [title for title, _ in games]


def main():
    if not __debug__:
        raise SystemExit("Run the regression checks with Python assertions enabled")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", help="Full URL of a running /recommend endpoint")
    parser.add_argument("--output", type=Path, default=Path("regression_results.json"))
    args = parser.parse_args()
    if args.url:
        import requests
        client, url = requests.Session(), args.url
    else:
        from fastapi.testclient import TestClient
        from app import app
        # No lifespan context: exercise routing without running MongoDB index setup.
        client, url = TestClient(app), "/recommend"

    report = []
    try:
        for query, expected in SCENARIOS.items():
            payload = payload_for(query)
            try:
                response = client.post(url, json=payload, timeout=30) if args.url else client.post(url, json=payload)
                response.raise_for_status()
                titles = check_result(response.json(), payload["budget"], expected)
                report.append({"query": query, "top_5": titles})
            except Exception as exc:
                report.append({"query": query, "error": repr(exc)})
                print(f"FAIL {query}: {exc!r}")
    finally:
        client.close()
    args.output.write_text(json.dumps(report, indent=4), encoding="utf-8")
    failed = sum("error" in row for row in report)
    print(f"{len(report) - failed}/{len(report)} scenarios passed. Report: {args.output}")
    return int(bool(failed))


if __name__ == "__main__":
    raise SystemExit(main())
