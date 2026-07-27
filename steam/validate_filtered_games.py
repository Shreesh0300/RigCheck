import os
from collections import Counter
from utils import load_json, save_json

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
FILTERED_FILE = os.path.join(DATA_DIR, 'filtered_games.json')
REPORT_FILE = os.path.join(DATA_DIR, 'validation_report.json')

def main():
    if not os.path.exists(FILTERED_FILE):
        print(f"File not found: {FILTERED_FILE}")
        return
        
    games = load_json(FILTERED_FILE)
    if not games:
        print("No data found in filtered_games.json")
        return

    # Basic stats
    total_games = len(games)
    
    # Report Statistics
    games_with_minimum = 0
    games_with_recommended = 0
    games_missing_requirements = 0
    games_with_price = 0
    games_free = 0
    games_paid = 0
    games_with_trailers = 0
    games_with_screenshots = 0
    games_with_metacritic = 0
    games_with_recommendations = 0
    games_with_website = 0
    games_windows = 0
    games_mac = 0
    games_linux = 0

    # Missing Field Analysis
    missing_counts = {
        "developers": 0,
        "publishers": 0,
        "genres": 0,
        "categories": 0,
        "release_date": 0,
        "header_image": 0,
        "website": 0,
        "supported_languages": 0,
        "price_overview": 0,
        "minimum": 0,
        "recommended": 0
    }

    # Top Statistics
    genre_counter = Counter()
    category_counter = Counter()
    developer_counter = Counter()
    publisher_counter = Counter()

    for game in games:
        # Minimum & Recommended Check
        has_min = bool(game.get("minimum"))
        has_rec = bool(game.get("recommended"))
        
        if has_min:
            games_with_minimum += 1
        else:
            missing_counts["minimum"] += 1
            
        if has_rec:
            games_with_recommended += 1
        else:
            missing_counts["recommended"] += 1
            
        if not has_min and not has_rec:
            games_missing_requirements += 1
            
        # Price and Free Check
        if game.get("price_overview"):
            games_with_price += 1
            
        if game.get("is_free"):
            games_free += 1
        elif game.get("is_free") is False:
            games_paid += 1
            
        if game.get("trailers"):
            games_with_trailers += 1
            
        if game.get("screenshots"):
            games_with_screenshots += 1
            
        if game.get("metacritic") is not None:
            games_with_metacritic += 1
            
        if game.get("recommendations") is not None:
            games_with_recommendations += 1
            
        if game.get("website"):
            games_with_website += 1
        else:
            missing_counts["website"] += 1
            
        # Platforms
        platforms = game.get("platforms", {})
        if platforms.get("windows"):
            games_windows += 1
        if platforms.get("mac"):
            games_mac += 1
        if platforms.get("linux"):
            games_linux += 1
            
        # Missing Field Analysis for remaining fields
        if not game.get("developers"):
            missing_counts["developers"] += 1
        if not game.get("publishers"):
            missing_counts["publishers"] += 1
        if not game.get("genres"):
            missing_counts["genres"] += 1
        if not game.get("categories"):
            missing_counts["categories"] += 1
        if not game.get("release_date"):
            missing_counts["release_date"] += 1
        if not game.get("header_image"):
            missing_counts["header_image"] += 1
        if not game.get("supported_languages"):
            missing_counts["supported_languages"] += 1
        if not game.get("price_overview"):
            missing_counts["price_overview"] += 1
            
        # Top Stats Extraction
        for dev in game.get("developers", []):
            developer_counter[dev] += 1
        for pub in game.get("publishers", []):
            publisher_counter[pub] += 1
        for gen in game.get("genres", []):
            genre_counter[gen] += 1
        for cat in game.get("categories", []):
            category_counter[cat] += 1

    report = {
        "report_statistics": {
            "total_games": total_games,
            "games_with_minimum": games_with_minimum,
            "games_with_recommended": games_with_recommended,
            "games_missing_requirements": games_missing_requirements,
            "games_with_price": games_with_price,
            "games_free": games_free,
            "games_paid": games_paid,
            "games_with_trailers": games_with_trailers,
            "games_with_screenshots": games_with_screenshots,
            "games_with_metacritic": games_with_metacritic,
            "games_with_recommendations": games_with_recommendations,
            "games_with_website": games_with_website,
            "games_windows": games_windows,
            "games_mac": games_mac,
            "games_linux": games_linux
        },
        "missing_field_analysis": missing_counts,
        "top_statistics": {
            "top_20_genres": dict(genre_counter.most_common(20)),
            "top_20_categories": dict(category_counter.most_common(20)),
            "top_20_developers": dict(developer_counter.most_common(20)),
            "top_20_publishers": dict(publisher_counter.most_common(20))
        }
    }

    save_json(REPORT_FILE, report)
    
    # Console Output
    print("\n============================")
    print("VALIDATION COMPLETE")
    print("\nGames:")
    print(total_games)
    print("\nMinimum Specs:")
    print(games_with_minimum)
    print("\nRecommended Specs:")
    print(games_with_recommended)
    print("\nMissing Specs:")
    print(games_missing_requirements)
    print("\nGames with Trailers:")
    print(games_with_trailers)
    print("\nGames with Screenshots:")
    print(games_with_screenshots)
    print("============================")

    # Warning Section
    print()
    threshold = total_games * 0.05
    for field, count in missing_counts.items():
        if count > threshold:
            print(f"WARNING:\nLarge number of games missing {field.replace('_', ' ')}.")

if __name__ == "__main__":
    main()
