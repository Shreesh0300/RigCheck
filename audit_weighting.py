import sys
from model.rigcheck_engine import clean_and_expand_input, _load_dataset, _build_vocabulary, _build_bm25_index

def audit_weighting():
    # 1. Load the actual dataset which already has Phase 2 metadata
    df = _load_dataset()
    bm25 = _build_bm25_index(df)
    
    # 2. Pick a single-word query that exists as a Title in one game, and as Metadata in another.
    # For example: "cowboy"
    query = "zombie"
    cleaned = clean_and_expand_input(query)
    tokenized_query = cleaned.split()
    
    # 3. Get raw BM25 scores for all games
    scores = bm25.get_scores(tokenized_query)
    df["bm25_score"] = scores
    
    # Sort
    results = df.sort_values(by="bm25_score", ascending=False)
    
    print(f"--- AUDIT WEIGHTING: '{query}' ---")
    for idx, row in results.head(10).iterrows():
        title = row['Title']
        score = row['bm25_score']
        master_search = row['Master_Search']
        
        if score > 0:
            term_freq = master_search.split().count(tokenized_query[0])
            doc_len = len(master_search.split())
            print(f"Title: {title:<40} | Score: {score:.4f} | TF: {term_freq} | Doc Len: {doc_len}")

if __name__ == "__main__":
    audit_weighting()
