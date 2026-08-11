import os

def patch_engine():
    path = "v:/Projects/RigCheck/model/rigcheck_engine.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Add imports if not present
    if "import json" not in content:
        content = "import json\nimport os\n" + content

    # Patch create_master_search
    old_create = """def create_master_search(row):
    combined_text = str(row["Title"]) + " " + str(row["Description"]) + " " + str(row["Tags"])
    return " ".join([stemmer.stem(word.strip(",.!?-")) for word in combined_text.lower().split()])"""

    new_create = """def create_master_search(row):
    # Weight search metadata higher by including it twice
    search_meta = str(row.get("Search_Metadata", ""))
    combined_text = str(row["Title"]) + " " + str(row["Description"]) + " " + str(row["Tags"]) + " " + search_meta + " " + search_meta
    return " ".join([stemmer.stem(word.strip(",.!?-")) for word in combined_text.lower().split()])"""

    content = content.replace(old_create, new_create)

    # Patch _load_dataset
    old_load = """def _load_dataset():
    \"\"\"Load the Steam game database and build a DataFrame with the same
    column names (Title, Description, Tags, Price_INR, Min_GPU_Tier, etc.)
    that the BM25 search engine and compatibility engine expect.\"\"\"
    steam_games = load_database()
    adapted_records = adapt_all_games(steam_games)
    dataframe = pd.DataFrame(adapted_records)
    dataframe["Master_Search"] = dataframe.apply(create_master_search, axis=1)
    return dataframe"""

    new_load = """def _load_dataset():
    \"\"\"Load the Steam game database and build a DataFrame with the same
    column names (Title, Description, Tags, Price_INR, Min_GPU_Tier, etc.)
    that the BM25 search engine and compatibility engine expect.\"\"\"
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
    return dataframe"""

    content = content.replace(old_load, new_load)

    # Patch _build_vocabulary
    old_vocab = """def _build_vocabulary(dataframe):
    vocabulary = set()
    all_text = (
        dataframe["Title"].astype(str)
        + " "
        + dataframe["Description"].astype(str)
        + " "
        + dataframe["Tags"].astype(str)
    ).str.lower()"""

    new_vocab = """def _build_vocabulary(dataframe):
    vocabulary = set()
    all_text = (
        dataframe["Title"].astype(str)
        + " "
        + dataframe["Description"].astype(str)
        + " "
        + dataframe["Tags"].astype(str)
        + " "
        + dataframe.get("Search_Metadata", pd.Series([""] * len(dataframe))).astype(str)
    ).str.lower()"""

    content = content.replace(old_vocab, new_vocab)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print("Successfully patched rigcheck_engine.py with Phase 2 metadata!")

if __name__ == "__main__":
    patch_engine()
