import re
import json
import os
import difflib

import pandas as pd
from nltk.stem import PorterStemmer
from rank_bm25 import BM25Okapi

from model.compatibility_engine import evaluate_game, rank_games
from model.steam_database import load_database
from model.steam_adapter import adapt_all_games

# Core NLP + recommendation logic belongs here so the API layer stays thin and reusable.
# This separation makes the system easier to test, evolve, and reuse from scripts or APIs.

stemmer = PorterStemmer()

ignore_words = [
    "i",
    "want",
    "a",
    "an",
    "the",
    "game",
    "games",
    "to",
    "play",
    "which",
    "is",
    "with",
    "that",
    "like",
    "and",
    "from",
    "into",
    "through",
    "can",
    "where",
    "their",
    "there",
    "this",
    "these",
    "those",
    "for",
    "while",
    "about",
    "around",
    "over",
    "under",
    "between",
    "among",
    "inside",
    "outside",
    "player",
    "players",
    "you",
    "your",
]


def create_master_search(row):
    # Weight search metadata higher by including it twice
    search_meta = str(row.get("Search_Metadata", ""))
    combined_text = str(row["Title"]) + " " + str(row["Description"]) + " " + str(row["Tags"]) + " " + search_meta + " " + search_meta
    return " ".join([stemmer.stem(word.strip(",.!?-")) for word in combined_text.lower().split()])


def _load_dataset():
    """Load the Steam game database and build a DataFrame with the same
    column names (Title, Description, Tags, Price_INR, Min_GPU_Tier, etc.)
    that the BM25 search engine and compatibility engine expect."""
    steam_games = load_database()
    adapted_records = adapt_all_games(steam_games)
    
    # Phase 2: Load search metadata
    metadata_path = os.path.join(os.path.dirname(__file__), "..", "data", "search_metadata.json")
    search_meta = {}
    if os.path.exists(metadata_path):
        with open(metadata_path, "r", encoding="utf-8") as f:
            search_meta = json.load(f)
            
    for rec in adapted_records:
        title = rec.get("Title")
        # Join concepts into a single string if metadata exists
        if title in search_meta:
            rec["Search_Metadata"] = " ".join(search_meta[title])
        else:
            rec["Search_Metadata"] = ""
            
    dataframe = pd.DataFrame(adapted_records)
    dataframe["Master_Search"] = dataframe.apply(create_master_search, axis=1)
    return dataframe


def _build_vocabulary(dataframe):
    vocabulary = set()
    all_text = (
        dataframe["Title"].astype(str)
        + " "
        + dataframe["Description"].astype(str)
        + " "
        + dataframe["Tags"].astype(str)
        + " "
        + dataframe.get("Search_Metadata", pd.Series([""] * len(dataframe))).astype(str)
    ).str.lower()

    for sentence in all_text:
        for word in sentence.split():
            clean_word = word.strip(",.!?-")
            if clean_word:
                vocabulary.add(clean_word)

    return vocabulary


def _build_bm25_index(dataframe):
    tokenized_corpus = [doc.split(" ") for doc in dataframe["Master_Search"]]
    return BM25Okapi(tokenized_corpus)


df = _load_dataset()
vocabulary = _build_vocabulary(df)
vocabulary_list = list(vocabulary)
bm25_index = _build_bm25_index(df)


def auto_correct(word):
    # Checks against your dynamically generated dataset vocabulary.
    matches = difflib.get_close_matches(word, vocabulary_list, n=1, cutoff=0.7)
    return matches[0] if matches else word


# Phase 4: Game Acronym Expansion
_game_aliases = {}
_aliases_path = os.path.join(os.path.dirname(__file__), "..", "data", "game_aliases.json")
if os.path.exists(_aliases_path):
    with open(_aliases_path, "r", encoding="utf-8") as f:
        _game_aliases = json.load(f)

def expand_game_aliases(user_input):
    expanded = user_input
    for alias, canonical in _game_aliases.items():
        pattern = r'\b' + re.escape(alias) + r'\b'
        expanded = re.sub(pattern, lambda m: f"{m.group(0)} {canonical}", expanded, flags=re.IGNORECASE)
    return expanded

def clean_and_expand_input(user_input):
    user_input = expand_game_aliases(user_input)
    final_keywords = []

    for word in user_input.lower().split():
        clean_word = word.strip(",.!?-")
        if clean_word and clean_word not in ignore_words:
            corrected_word = auto_correct(clean_word)
            stemmed_word = stemmer.stem(corrected_word)

            if stemmed_word not in final_keywords:
                final_keywords.append(stemmed_word)

    return " ".join(final_keywords)


def get_graphics_advice(user_gpu, user_ram, game_gpu, game_ram):
    gpu_diff = user_gpu - game_gpu

    if gpu_diff >= 2 and user_ram > game_ram:
        return "ULTRA: You can max out every setting. Enjoy the eye-candy!"
    elif gpu_diff >= 1:
        return "HIGH: You should get a smooth 60 FPS with most settings turned up."
    elif gpu_diff == 0:
        if user_ram > game_ram:
            return "MEDIUM: Safe bet for stable performance. You have extra RAM to help!"
        else:
            return "LOW/MEDIUM: Stick to lower settings to keep your frame rate steady."
    else:
        return "STABLE: Focus on performance over visuals for the best experience."


def run_vibe_check(cleaned_query, dataframe=None, index=None, top_n=8):
    # Uses Master_Search (not just Tags) for broader matches.
    if dataframe is None:
        dataframe = df
    if index is None:
        index = bm25_index

    tokenized_query = cleaned_query.split(" ")
    doc_scores = index.get_scores(tokenized_query)

    scored_df = dataframe.copy()
    scored_df["Vibe_Score"] = doc_scores
    ranked_df = scored_df.sort_values("Vibe_Score", ascending=False)

    return ranked_df.head(top_n)


# Fallback URLs for games not sold on Steam
_NON_STEAM_URLS = {
    "Valorant": "https://playvalorant.com/en-us/",
    "Minecraft": "https://www.minecraft.net/en-us/store/minecraft-java-bedrock-edition-pc",
}


def _get_store_url(row):
    """Build a store page URL from the Steam_AppID column, or return a fallback."""
    title = str(row.get("Title", ""))
    if title in _NON_STEAM_URLS:
        return _NON_STEAM_URLS[title]
    app_id = int(row.get("Steam_AppID", 0))
    if app_id > 0:
        return f"https://store.steampowered.com/app/{app_id}"
    return ""


def _empty_response(message):
    return {
        "recommended_game": "",
        "confidence": 0,
        "description": message,
        "hardware_advice": "",
        "matched_keywords": [],
        "alternative_games": [],
        "store_url": "",
    }



def extract_query_constraints(cleaned_query):
    constraints = []
    for word in cleaned_query.split():
        idf = bm25_index.idf.get(word, 0)
        constraints.append({'word': word, 'idf': idf})
    return constraints

def rerank_candidates(vibe_results, cleaned_query):
    if vibe_results.empty:
        return vibe_results

    constraints = extract_query_constraints(cleaned_query)
    
    # Classify terms
    # High: IDF > 3.0 (appears in < ~20 games out of 500)
    # Medium: 1.5 < IDF <= 3.0 (appears in 20-100 games)
    # Low: IDF <= 1.5 (appears in > 100 games)
    high_value_terms = [c['word'] for c in constraints if c['idf'] > 3.0]
    medium_value_terms = [c['word'] for c in constraints if 1.5 < c['idf'] <= 3.0]
    
    max_bm25 = vibe_results["Vibe_Score"].max()
    if max_bm25 == 0:
        max_bm25 = 1.0

    def calculate_new_score(row):
        # 1. Normalize BM25
        base_score = row["Vibe_Score"] / max_bm25
        
        master_search = str(row["Master_Search"]).lower()
        search_words = set(master_search.split())
        
        match_count = 0
        bonus = 0
        penalty = 0
        
        # 2. Check high value terms
        for term in high_value_terms:
            if term in search_words:
                match_count += 1
                bonus += 0.4
            else:
                penalty += 0.2
                
        # 3. Check medium value terms
        for term in medium_value_terms:
            if term in search_words:
                match_count += 0.5
                bonus += 0.15
                
        # 4. Multi-constraint synergy
        if match_count > 1:
            bonus *= (match_count * 0.7)
            
        final_score = base_score + bonus - penalty
        return max(0.0, final_score)

    vibe_results["Rerank_Score"] = vibe_results.apply(calculate_new_score, axis=1)
    
    # Re-sort by the new score
    reranked = vibe_results.sort_values("Rerank_Score", ascending=False)
    
    # Overwrite Vibe_Score so the rest of the engine behaves normally
    reranked["Vibe_Score"] = reranked["Rerank_Score"]
    
    return reranked

def recommend_game(user_input, budget, gpu_name, ram,
                   cpu_name=None, storage_gb=None, gpu_tier=None):
    # ── Backward Compatibility ──
    if isinstance(gpu_name, int) or (isinstance(gpu_name, str) and gpu_name.isdigit()):
        gpu_tier = int(gpu_name)
        gpu_name = None

    # ── Resolve GPU Model ──
    gpu_benchmark_score = None
    resolved_gpu_tier = 1

    if gpu_name:
        from gpu.gpu_tier_engine import validateGpu
        gpu_res = validateGpu(gpu_name)
        if gpu_res.get("error"):
            raise ValueError(gpu_res["error"])
        
        letter_tier = gpu_res.get("tier", "D")
        tier_map = {"D": 1, "C": 2, "B": 3, "A": 4, "S": 5}
        resolved_gpu_tier = tier_map.get(letter_tier, 1)
        gpu_benchmark_score = gpu_res.get("benchmark_score")
    elif gpu_tier is not None:
        resolved_gpu_tier = int(gpu_tier)
    else:
        raise ValueError("GPU model not recognized. Please check the spelling and try again.")

    # ── Resolve CPU Model ──
    cpu_benchmark_score = None
    resolved_cpu_tier = 1

    if cpu_name and cpu_name.strip():
        from cpu.cpu_tier_engine import validateCpu
        cpu_res = validateCpu(cpu_name)
        if cpu_res.get("error"):
            raise ValueError("CPU model not recognized. Please check the spelling and try again.")
        
        letter_tier_cpu = cpu_res.get("tier", "D")
        tier_map = {"D": 1, "C": 2, "B": 3, "A": 4, "S": 5}
        resolved_cpu_tier = tier_map.get(letter_tier_cpu, 1)
        cpu_benchmark_score = cpu_res.get("benchmark_score")

    cleaned_vibe = clean_and_expand_input(user_input)
    # 1. Retrieve a larger candidate pool
    vibe_results = run_vibe_check(cleaned_vibe, top_n=50)

    if vibe_results.empty or vibe_results.iloc[0]["Vibe_Score"] == 0:
        return _empty_response("No games match that vibe.")

    # 2. Intent-Aware Reranking
    vibe_results = rerank_candidates(vibe_results, cleaned_vibe)

    # 3. Filter by Budget First
    affordable_candidates = vibe_results[vibe_results["Price_INR"] <= budget]
    if affordable_candidates.empty:
        return _empty_response("Games found, but they are out of your budget.")

    # 4. Apply Threshold on new Rerank_Score (using affordable top score)
    top_score = affordable_candidates.iloc[0]["Vibe_Score"]
    dynamic_threshold = top_score * 0.45
    wallet_passed = affordable_candidates[affordable_candidates["Vibe_Score"] >= dynamic_threshold]

    # ── Compatibility Evaluation ─────────────────────────────────────────
    # Evaluate ALL vibe+budget candidates through the compatibility engine.
    # Games that fail hardware checks are NOT rejected — they are ranked
    # lower by compatibility score instead.
    max_possible = max(1, len(cleaned_vibe.split()) * 1.5)

    evaluated_games = []
    vibe_score_map = {}
    budget_score_map = {}

    for i in range(len(wallet_passed)):
        row = wallet_passed.iloc[i]
        game_dict = row.to_dict()

        # Run full 4-component compatibility evaluation
        compat_result = evaluate_game(
            game_row=game_dict,
            user_gpu_tier=resolved_gpu_tier,
            user_ram_gb=ram,
            user_cpu_name=cpu_name,
            user_storage_gb=storage_gb,
            user_gpu_score=gpu_benchmark_score,
            user_cpu_score=cpu_benchmark_score,
            user_cpu_tier=resolved_cpu_tier,
        )

        # Attach vibe and budget info
        vibe_sc = float(row["Vibe_Score"])
        title = str(row["Title"])
        compat_result["vibe_score"] = vibe_sc
        compat_result["price_inr"] = int(row["Price_INR"])
        compat_result["store_url"] = _get_store_url(row)
        compat_result["description"] = str(row["Description"])
        compat_result["header_image"] = str(row.get("Header_Image", ""))

        # Parse tags
        raw_tags = str(row.get("Tags", ""))
        compat_result["tags"] = [t.strip() for t in raw_tags.split(",") if t.strip()]

        # Confidence
        conf = min(99, int((vibe_sc / max_possible) * 100))
        if conf < 40:
            conf += 30
        compat_result["confidence"] = conf

        evaluated_games.append(compat_result)
        # Check if this game is PAYDAY 2 or Slay the Spire for debug logging
        if title in ["PAYDAY 2", "Slay the Spire"]:
            from .debug_logger import log_debug_info
            # Since steam API returns prices natively in INR and our budget is natively INR, 
            # normalized price/budget are the same.
            price = int(row["Price_INR"])
            log_debug_info(
                game=title,
                game_price=price,
                price_type="final",
                price_currency="INR",
                user_budget=budget,
                normalized_price=price,
                normalized_budget=budget,
                price_lte_budget=price <= budget,
                compatibility=f"{compat_result['compatibility_pct']}%",
                final_eligible=True # It made it this far
            )

        # Budget Score: closer to 0 is better (cheaper relative to budget)
        vibe_score_map[title] = vibe_sc
        budget_score_map[title] = max(0, 1.0 - (int(row["Price_INR"]) / max(budget, 1)))

    # Rank games: compatibility → vibe → budget
    ranked = rank_games(evaluated_games, vibe_score_map, budget_score_map)

    if not ranked:
        return _empty_response("No compatible games found.")

    # Build response — winner is the top-ranked game
    winner = ranked[0]
    advice = get_graphics_advice(
        resolved_gpu_tier,
        ram,
        int(wallet_passed.iloc[0].get("Min_GPU_Tier", 1)),
        int(wallet_passed.iloc[0].get("Min_RAM_GB", 2)),
    )

    matched_keywords = []
    for word in cleaned_vibe.split():
        winner_row = wallet_passed[wallet_passed["Title"] == winner["title"]]
        if not winner_row.empty:
            if word in str(winner_row.iloc[0].get("Master_Search", "")):
                if word not in matched_keywords:
                    matched_keywords.append(word)

    # Build alternative games list (all ranked games after the winner)
    alternative_games = []
    for alt in ranked[1:min(4, len(ranked))]:
        alternative_games.append({
            "title": alt["title"],
            "price_inr": alt["price_inr"],
            "description": alt["description"],
            "tags": alt["tags"],
            "header_image": alt.get("header_image", ""),
            "confidence": alt["confidence"],
            "store_url": alt["store_url"],
            "compatibility": {
                "compatibility_pct": alt["compatibility_pct"],
                "gpu": alt["gpu"],
                "cpu": alt["cpu"],
                "ram": alt["ram"],
                "storage": alt["storage"],
                "estimated_fps": alt["estimated_fps"],
                "expected_settings": alt["expected_settings"],
                "reduction_reasons": alt["reduction_reasons"],
            },
        })

    return {
        "recommended_game": winner["title"],
        "confidence": winner["confidence"],
        "description": winner["description"],
        "hardware_advice": advice,
        "matched_keywords": matched_keywords,
        "header_image": winner.get("header_image", ""),
        "alternative_games": alternative_games,
        "store_url": winner["store_url"],
        "price_inr": winner["price_inr"],   # actual game price, independent of user budget
        "compatibility": {
            "compatibility_pct": winner["compatibility_pct"],
            "gpu": winner["gpu"],
            "cpu": winner["cpu"],
            "ram": winner["ram"],
            "storage": winner["storage"],
            "estimated_fps": winner["estimated_fps"],
            "expected_settings": winner["expected_settings"],
            "reduction_reasons": winner["reduction_reasons"],
        },
    }


def run_rigcheck(user_input, budget, user_gpu, user_ram,
                 user_cpu=None, user_storage_gb=None):
    return recommend_game(
        user_input=user_input,
        budget=budget,
        gpu_name=user_gpu,
        ram=user_ram,
        cpu_name=user_cpu,
        storage_gb=user_storage_gb,
    )