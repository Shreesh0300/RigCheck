from model.rigcheck_engine import clean_and_expand_input, extract_hardware_intent, get_explicit_references, df, bm25_index, exact_titles, recommend_game
import pandas as pd
from model.concept_engine import extract_query_concepts

query = 'games like gta 5'
cleaned = clean_and_expand_input(query)
refs = get_explicit_references(query)
print('Refs:', refs)

tokenized = cleaned.split()
bm25_scores = bm25_index.get_scores(tokenized)

candidates_df = df.copy()
candidates_df['BM25_Score'] = bm25_scores
candidates_df['Has_Reference'] = candidates_df['Title'].apply(lambda t: t.lower() in refs)

candidates_df = candidates_df.sort_values(by='BM25_Score', ascending=False)
print('Top 5 BM25 matches for GTA:')
for _, row in candidates_df.head(5).iterrows():
    print(f"{row['Title']} ({row['Steam_AppID']}): {row['BM25_Score']}, Ref: {row['Has_Reference']}, Price: {row['Price_INR']}")

# Let's run full rank_games
payload = {
    'user_input': query,
    'budget': 10000,
    'gpu_name': 'RTX 4070',
    'ram': 16,
    'cpu_name': 'Ryzen 5 5600X',
    'storage_gb': 1000
}
res = recommend_game(**payload)
print('Recommended:', res.get('recommended_game'), res.get('confidence'))
