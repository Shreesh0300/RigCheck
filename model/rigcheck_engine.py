from pathlib import Path

import difflib

import pandas as pd
from nltk.stem import PorterStemmer
from rank_bm25 import BM25Okapi

# Core NLP + recommendation logic belongs here so the API layer stays thin and reusable.
# This separation makes the system easier to test, evolve, and reuse from scripts or APIs.

stemmer = PorterStemmer()

DATA_PATH = Path(__file__).resolve().parent.parent / "games_dataset.csv"

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
    combined_text = str(row["Title"]) + " " + str(row["Description"]) + " " + str(row["Tags"])
    return " ".join([stemmer.stem(word.strip(",.!?-")) for word in combined_text.lower().split()])


def _load_dataset():
    dataframe = pd.read_csv(DATA_PATH)
    dataframe.columns = dataframe.columns.str.strip()
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


def clean_and_expand_input(user_input):
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


def recommend_game(user_input, budget, gpu_tier, ram):
    cleaned_vibe = clean_and_expand_input(user_input)
    vibe_results = run_vibe_check(cleaned_vibe, top_n=len(df))

    if vibe_results.empty or vibe_results.iloc[0]["Vibe_Score"] == 0:
        return _empty_response("No games match that vibe.")

    top_score = vibe_results.iloc[0]["Vibe_Score"]
    # Tighter threshold — alternatives must be at least 45% as relevant as the best match
    dynamic_threshold = top_score * 0.45
    vibe_passed = vibe_results[vibe_results["Vibe_Score"] >= dynamic_threshold]

    wallet_passed = vibe_passed[vibe_passed["Price_INR"] <= budget]
    if wallet_passed.empty:
        return _empty_response("Games found, but they are out of your budget.")

    rig_passed = wallet_passed[
        (wallet_passed["Min_GPU_Tier"] <= gpu_tier)
        & (wallet_passed["Min_RAM_GB"] <= ram)
    ]
    if rig_passed.empty:
        return _empty_response("Your PC hardware is too weak to run these games.")

    winner = rig_passed.iloc[0]
    advice = get_graphics_advice(
        gpu_tier,
        ram,
        winner["Min_GPU_Tier"],
        winner["Min_RAM_GB"],
    )

    max_possible = max(1, len(cleaned_vibe.split()) * 1.5)
    confidence = min(99, int((winner["Vibe_Score"] / max_possible) * 100))
    if confidence < 40:
        confidence += 30

    matched_keywords = []
    for word in cleaned_vibe.split():
        if word in str(winner["Master_Search"]) and word not in matched_keywords:
            matched_keywords.append(word)

    # Build richer alternative game objects with tags, description, and confidence
    alternative_games = []
    if len(rig_passed) > 1:
        for i in range(1, min(4, len(rig_passed))):
            alt = rig_passed.iloc[i]
            alt_conf = min(99, int((alt["Vibe_Score"] / max_possible) * 100))
            if alt_conf < 40:
                alt_conf += 30
            # Parse tags into a clean list
            raw_tags = str(alt.get("Tags", ""))
            tag_list = [t.strip() for t in raw_tags.split(",") if t.strip()]
            alternative_games.append(
                {
                    "title": str(alt["Title"]),
                    "price_inr": int(alt["Price_INR"]),
                    "description": str(alt["Description"]),
                    "tags": tag_list,
                    "confidence": int(alt_conf),
                    "store_url": _get_store_url(alt),
                }
            )

    return {
        "recommended_game": str(winner["Title"]),
        "confidence": int(confidence),
        "description": str(winner["Description"]),
        "hardware_advice": advice,
        "matched_keywords": matched_keywords,
        "alternative_games": alternative_games,
        "store_url": _get_store_url(winner),
    }


def run_rigcheck(user_input, budget, user_gpu_tier, user_ram):
    return recommend_game(
        user_input=user_input,
        budget=budget,
        gpu_tier=user_gpu_tier,
        ram=user_ram,
    )