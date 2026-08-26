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
from model.concept_engine import extract_game_concepts, extract_query_concepts

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
    "my",
    "me",
    "we",
    "us",
    "our",
    "they",
    "them",
    "he",
    "she",
    "it",
    "am",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "shall",
    "should",
    "can",
    "could",
    "may",
    "might",
    "must",
    "but",
    "if",
    "or",
    "because",
    "as",
    "until",
    "of",
    "at",
    "by",
    "on",
    "off",
    "then",
    "once",
    "here",
    "there",
    "when",
    "where",
    "why",
    "how",
    "all",
    "any",
    "both",
    "each",
    "few",
    "more",
    "most",
    "other",
    "some",
    "such",
    "no",
    "nor",
    "not",
    "only",
    "own",
    "same",
    "so",
    "than",
    "too",
    "very",
    "s",
    "t",
    "just",
    "now"
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
    dataframe["Concepts"] = dataframe.apply(extract_game_concepts, axis=1)
    dataframe["Master_Search"] = dataframe.apply(create_master_search, axis=1)
    return dataframe


def _build_game_vocab(dataframe):
    game_vocab = set()
    all_titles = dataframe["Title"].astype(str).str.lower()
    for title in all_titles:
        for word in title.split():
            clean_word = word.strip(",.!?-")
            if clean_word:
                game_vocab.add(clean_word)
    return game_vocab


def _build_bm25_index(dataframe):
    tokenized_corpus = [doc.split(" ") for doc in dataframe["Master_Search"]]
    return BM25Okapi(tokenized_corpus)


import nltk
def _initialize_english_vocab():
    try:
        nltk.data.find('corpora/words.zip')
    except LookupError:
        nltk.download('words', quiet=True)
    from nltk.corpus import words
    
    eng_vocab = set(word.lower() for word in words.words())
    # Add gaming terms and all concepts
    from model.concept_engine import CONCEPT_VOCAB
    gaming_terms = {"pc", "fps", "rpg", "co-op", "coop", "multiplayer", "game", "games", "friends", "friend", "characters", "bosses", "zombies", "zombie", "heists", "heist", "robberies", "robbery", "casual", "competitive", "story"}
    eng_vocab.update(gaming_terms)
    for concept in CONCEPT_VOCAB:
        for word in concept.split("-"):
            eng_vocab.add(word)
    return eng_vocab


df = _load_dataset()
game_vocab_list = list(_build_game_vocab(df))
exact_titles = {str(t).lower() for t in df["Title"]}
english_vocab = _initialize_english_vocab()
bm25_index = _build_bm25_index(df)


def auto_correct(word):
    if word in english_vocab:
        return word
    matches = difflib.get_close_matches(word, game_vocab_list, n=1, cutoff=0.7)
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

_concept_synonyms = {
    "heist": "heist crime robbery",
    "heists": "heist crime robbery",
    "robbery": "robbery heist crime",
    "robberies": "robbery heist crime",
    "friends": "friend co-op multiplayer",
    "friend": "friend co-op multiplayer",
    "sneak": "sneak stealth",
    "sneaking": "sneak stealth",
    "ship": "ship naval",
    "ships": "ship naval",
    "submarine": "submarine naval",
    "submarines": "submarine naval",
}

def clean_and_expand_input(user_input):
    user_input = expand_game_aliases(user_input)
    final_keywords = []

    for word in user_input.lower().split():
        clean_word = word.strip(",.!?-")
        if clean_word and clean_word not in ignore_words:
            corrected_word = auto_correct(clean_word)
            
            # Apply general concept expansion
            if corrected_word in _concept_synonyms:
                expanded_words = _concept_synonyms[corrected_word].split()
                for ew in expanded_words:
                    stemmed_ew = stemmer.stem(ew)
                    if stemmed_ew not in final_keywords:
                        final_keywords.append(stemmed_ew)
            else:
                stemmed_word = stemmer.stem(corrected_word)
                if stemmed_word not in final_keywords:
                    final_keywords.append(stemmed_word)

    # Inject extracted concepts as keywords so BM25 can retrieve conceptually relevant games
    from model.concept_engine import extract_query_concepts
    concepts = extract_query_concepts(user_input)
    for concept in concepts:
        # Split multi-word concepts (like 'story-driven') and stem them
        for concept_word in concept.split("-"):
            stemmed = stemmer.stem(concept_word)
            if stemmed not in final_keywords:
                final_keywords.append(stemmed)

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
    
    def calculate_new_score(row):
        # 1. Use raw BM25 score instead of squashing it to 1.0
        # Normalizing to 1.0 destroyed the TF-IDF weighting and allowed the raw word-count bonus to dominate.
        base_score = row["Vibe_Score"]
        
        master_search = str(row["Master_Search"]).lower()
        search_words = master_search.split()
        
        bonus = 0.0
        
        # 2. Add continuous IDF-weighted bonuses (no negative penalties)
        for c in constraints:
            word = c['word']
            idf = c['idf']
            tf = search_words.count(word)
            if tf > 0:
                capped_tf = min(tf, 3)
                # Base weight: A word with IDF 5 gives 0.5 bonus per occurrence
                term_weight = (idf / 10.0) * capped_tf
                bonus += term_weight
                
        final_score = base_score + bonus
        return final_score

    vibe_results["Rerank_Score"] = vibe_results.apply(calculate_new_score, axis=1)
    
    # Re-sort by the new score
    reranked = vibe_results.sort_values("Rerank_Score", ascending=False)
    
    # Overwrite Vibe_Score so the rest of the engine behaves normally
    reranked["Vibe_Score"] = reranked["Rerank_Score"]
    
    return reranked

def extract_hardware_intent(user_input):
    words = []
    for word in user_input.lower().split():
        clean_word = word.strip(",.!?-")
        if clean_word:
            words.append(auto_correct(clean_word))
        else:
            words.append(word)
    q = " ".join(words).replace("'", "")
    
    low_patterns = [
        r"\b(old|older|low end|low-end|weak|potato)\s+(pc|computer|gpu|hardware|system)\b",
        r"\b(low|bad)\s+(specs|specifications)\b",
        r"\b(not|isnt|is not|aint|without being)\s+(very\s+|too\s+)?(powerful|demanding|heavy|taxing)\b",
        r"\b(lightweight|light game|easy to run)\b",
        r"\bruns\s+(easily\s+)?on\s+(low end|old)\b"
    ]
    for p in low_patterns:
        if re.search(p, q):
            return "LOW_HARDWARE"
            
    high_patterns = [
        r"\b(powerful|high end|high-end|strong|beast|top tier)\s+(pc|computer|gpu|hardware|system)\b",
        r"\bhigh\s+(specs|specifications)\b",
        r"\bmodern\s+gaming\s+pc\b",
        r"\bcan\s+(run|handle)\s+anything\b",
        r"\b(graphically\s+|very\s+)?demanding\b",
        r"\b(max|ultra)\s+settings\b",
        r"\baaa\b"
    ]
    for p in high_patterns:
        if re.search(p, q):
            return "HIGH_HARDWARE"
            
    return "NO_HARDWARE_INTENT"

GENERIC_WORDS = {"good", "great", "fun", "interesting", "awesome", "cool", "nice", "something", "anything", "game", "games", "play", "recommend", "recommendation", "best"}

def detect_query_vagueness(user_input, query_concepts):
    # Check if exact title or alias
    if user_input.lower() in exact_titles:
        return 1.0, "SPECIFIC"
    if expand_game_aliases(user_input) != user_input:
        return 1.0, "SPECIFIC"
    
    raw_words = [w.strip(",.!?-").lower() for w in user_input.split() if w.strip(",.!?-")]
    
    meaningful_count = 0
    generic_count = 0
    
    for w in raw_words:
        if w in GENERIC_WORDS:
            generic_count += 1
        elif w not in ignore_words:
            meaningful_count += 1
            
    concept_count = len(query_concepts)
    
    if concept_count >= 2 or meaningful_count >= 3:
        return 1.0, "SPECIFIC"
    elif concept_count == 1 or meaningful_count >= 1:
        return 0.6, "MODERATELY_SPECIFIC"
    else:
        return 0.2, "VAGUE"

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

    hw_intent = extract_hardware_intent(user_input)
    query_concepts = extract_query_concepts(user_input)
    vagueness_score, vagueness_class = detect_query_vagueness(user_input, query_concepts)
    
    cleaned_vibe = clean_and_expand_input(user_input)
    
    if vagueness_class == "VAGUE":
        generic_stems = {stemmer.stem(w) for w in GENERIC_WORDS}
        cleaned_vibe = " ".join([w for w in cleaned_vibe.split() if w not in generic_stems])
        
    top_n_candidates = 50
    if vagueness_class == "MODERATELY_SPECIFIC":
        top_n_candidates = 100
    elif vagueness_class == "VAGUE":
        top_n_candidates = 150
        
    # 1. Retrieve a larger candidate pool
    vibe_results = run_vibe_check(cleaned_vibe, top_n=top_n_candidates)

    if vibe_results.empty or (vagueness_class != "VAGUE" and vibe_results.iloc[0]["Vibe_Score"] == 0):
        return _empty_response("No games match that vibe.")

    # 2. Intent-Aware Reranking
    vibe_results = rerank_candidates(vibe_results, cleaned_vibe)

    # 2.5 Concept-Aware Semantic Scoring
    max_rerank = vibe_results["Vibe_Score"].max() if not vibe_results.empty else 1.0
    if max_rerank == 0:
        max_rerank = 1.0

    vibe_results["Raw_Vibe"] = vibe_results["Vibe_Score"]

    def compute_concept_score(row):
        game_concepts = row.get("Concepts", [])
        if not query_concepts:
            return 0.0
        matches = set(query_concepts) & set(game_concepts)
        return len(matches) / len(query_concepts)

    vibe_results["Concept_Score"] = vibe_results.apply(compute_concept_score, axis=1)

    def compute_semantic_score(row):
        base_normalized = row["Vibe_Score"] / max_rerank
        score = (base_normalized * 0.70) + (row["Concept_Score"] * 0.30)
        if vagueness_class == "VAGUE":
            popularity_boost = min(1.0, row.get("Popularity", 0) / 1000000.0) * 0.30
            score += popularity_boost
        return score
        
    vibe_results["Semantic_Score"] = vibe_results.apply(compute_semantic_score, axis=1)
    vibe_results = vibe_results.sort_values("Semantic_Score", ascending=False)
    vibe_results["Vibe_Score"] = vibe_results["Semantic_Score"]

    # 3. Filter by Budget First
    # Ensure Price_INR >= 0 so that games with UNKNOWN prices (-1) do not automatically pass.
    affordable_candidates = vibe_results[
        (vibe_results["Price_INR"] >= 0) & 
        (vibe_results["Price_INR"] <= budget)
    ]
    if affordable_candidates.empty:
        return _empty_response("Games found, but they are out of your budget.")

    # 4. Apply Threshold on new Rerank_Score (using affordable top score)
    top_score = affordable_candidates.iloc[0]["Vibe_Score"]
    dynamic_threshold = top_score * 0.10
    wallet_passed = affordable_candidates[affordable_candidates["Vibe_Score"] >= dynamic_threshold]

    # ── Compatibility Evaluation ─────────────────────────────────────────
    # Evaluate ALL vibe+budget candidates through the compatibility engine.
    # Games that fail hardware checks are NOT rejected — they are ranked
    # lower by compatibility score instead.
    # A base of 15.0 ensures that short/ambiguous queries do not artificially reach 100% semantic confidence.
    max_possible = max(15.0, len(cleaned_vibe.split()) * 1.5)

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
        compat_result["raw_vibe"] = float(row["Raw_Vibe"])
        compat_result["concept_score"] = float(row["Concept_Score"])
        compat_result["price_inr"] = int(row["Price_INR"])
        compat_result["store_url"] = _get_store_url(row)
        compat_result["description"] = str(row["Description"])
        compat_result["header_image"] = str(row.get("Header_Image", ""))

        # Parse tags
        raw_tags = str(row.get("Tags", ""))
        compat_result["tags"] = [t.strip() for t in raw_tags.split(",") if t.strip()]

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
    ranked = rank_games(evaluated_games, vibe_score_map, budget_score_map, hw_intent)

    if not ranked:
        return _empty_response("No compatible games found.")

    # ── P6 Confidence Calculation ──
    has_concepts = len(query_concepts) > 0
    for i, game in enumerate(ranked):
        semantic_conf = min(1.0, game.get("raw_vibe", 0.0) / max_possible)
        semantic_conf *= vagueness_score
        concept_conf = game.get("concept_score", 0.0) if has_concepts else semantic_conf
        hw_conf = game.get("compat_normalized", 0.0)
        budget_conf = game.get("budget_normalized", 0.0)
        
        if i + 1 < len(ranked):
            score_1 = game.get("final_score", 0.0)
            score_2 = ranked[i+1].get("final_score", 0.0)
            gap_conf = min(1.0, (score_1 - score_2) / 0.10)
        else:
            gap_conf = 1.0
            
        confidence = (
            semantic_conf * 0.35
            + concept_conf * 0.20
            + hw_conf * 0.15
            + budget_conf * 0.10
            + gap_conf * 0.20
        )
        game["confidence"] = int(round(confidence * 100))

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
            "price_inr": alt["price_inr"] if alt["price_inr"] >= 0 else "UNKNOWN",
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
        "price_inr": winner["price_inr"] if winner["price_inr"] >= 0 else "UNKNOWN",
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