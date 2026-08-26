import re

# A controlled vocabulary of concepts.
CONCEPT_VOCAB = {
    "story-driven", "co-op", "multiplayer", "competitive", "single-player", 
    "shooter", "third-person", "stealth", "horror", "survival", "zombie", 
    "rpg", "action-rpg", "soulslike", "strategy", "simulation", "sandbox", 
    "racing", "sports", "platformer", "roguelike", "indie", "casual", 
    "challenging", "exploration", "crime", "heist", "driving", "fantasy", 
    "sci-fi", "puzzle", "city-building", "management", "open-world"
}

# Mapping natural language query phrases to canonical concepts.
QUERY_MAPPING = {
    r"\b(good|great|strong|focused|heavy)\s+story\b": ["story-driven"],
    r"\bstory\b": ["story-driven"],
    r"\bnarrative\b": ["story-driven"],
    r"\bcharacters?\b": ["story-driven"],
    
    r"\bwith\s+friends\b": ["co-op", "multiplayer"],
    r"\bplay\s+together\b": ["co-op", "multiplayer"],
    r"\bco-?op(erative)?\b": ["co-op", "multiplayer"],
    r"\bmulti-?player\b": ["multiplayer"],
    r"\bsingle-?player\b": ["single-player"],
    
    r"\b(like\s+gta|gta-?like)\b": ["open-world", "crime", "driving", "shooter"],
    
    r"\bzombies?\b": ["zombie"],
    r"\bundead\b": ["zombie"],
    
    r"\bheist(s)?\b": ["heist", "crime"],
    r"\brobber(y|ies)\b": ["heist", "crime"],
    r"\bbank(s)?\b": ["heist"],
    r"\bcrime(s)?\b": ["crime"],
    
    r"\bboss(es)?\b": ["challenging", "soulslike"],
    r"\bdifficult\b": ["challenging"],
    r"\bchallenging\b": ["challenging"],
    r"\bhard\b": ["challenging"],
    r"\bsouls-?like\b": ["soulslike", "action-rpg", "challenging"],
    
    r"\bscar(y|ing)\b": ["horror"],
    r"\bcreepy\b": ["horror"],
    r"\bterrifying\b": ["horror"],
    r"\bhorror\b": ["horror"],
    
    r"\bsurviv(al|e)\b": ["survival"],
    
    r"\bopen-?\s*world\b": ["open-world"],
    r"\bexplor(e|ation)\b": ["exploration"],
    
    r"\bdriv(e|ing)\b": ["driving"],
    r"\bcar(s)?\b": ["driving", "racing"],
    r"\bracing\b": ["racing"],
    
    r"\bshoot(er|ing)?\b": ["shooter"],
    r"\bfps\b": ["shooter"],
    
    r"\bfantasy\b": ["fantasy"],
    r"\bsci-?fi\b": ["sci-fi"],
    r"\bspace\b": ["sci-fi"],
    
    r"\bbuild(ing)?\b": ["city-building"],
    r"\bmanage(ment)?\b": ["management"],
    r"\bstrateg(y|ic)\b": ["strategy"],
}

def extract_query_concepts(query: str) -> list[str]:
    """
    Extract canonical concepts from a raw user query.
    """
    query_lower = query.lower()
    concepts = set()
    
    for pattern, mapped_concepts in QUERY_MAPPING.items():
        if re.search(pattern, query_lower):
            concepts.update(mapped_concepts)
            
    return list(concepts)

def extract_game_concepts(row: dict) -> list[str]:
    """
    Generate canonical concepts for a game based on explicit metadata.
    Does NOT over-rely on the generic 'Description' to avoid false positives.
    """
    genres = str(row.get("Genres", "")).lower()
    categories = str(row.get("Categories", "")).lower()
    title = str(row.get("Title", "")).lower()
    desc = str(row.get("Description", "")).lower() # Only Short Description
    tags = str(row.get("Tags", "")).lower() # explicit Tags string
    
    concepts = set()
    
    # 1. Categories (Strong signals)
    if "co-op" in categories or "coop" in categories or "cooperative" in categories:
        concepts.update(["co-op", "multiplayer"])
    if "multi-player" in categories or "multiplayer" in categories:
        concepts.add("multiplayer")
    if "single-player" in categories or "singleplayer" in categories:
        concepts.add("single-player")
        
    # 2. Genres (Strong signals)
    if "rpg" in genres or "role-playing" in genres:
        concepts.add("rpg")
    if "action" in genres and ("rpg" in genres or "role-playing" in genres):
        concepts.add("action-rpg")
    if "strategy" in genres:
        concepts.add("strategy")
    if "simulation" in genres:
        concepts.add("simulation")
    if "racing" in genres:
        concepts.update(["racing", "driving"])
    if "sports" in genres:
        concepts.add("sports")
    if "indie" in genres:
        concepts.add("indie")
    if "casual" in genres:
        concepts.add("casual")
        
    # 3. Targeted Keyword Matching in explicit fields (Heuristics)
    combined_explicit = genres + " " + categories + " " + title + " " + tags
    
    if re.search(r"\bzombies?\b|\bundead\b", combined_explicit + " " + desc):
        concepts.add("zombie")
        
    if re.search(r"\bheist(s)?\b|\brobber(y|ies)\b|\bbank(s)?\b", combined_explicit + " " + desc):
        concepts.update(["heist", "crime"])
        
    if "crime" in combined_explicit + " " + desc:
        concepts.add("crime")
        
    if "open world" in combined_explicit or "open-world" in combined_explicit:
        concepts.add("open-world")
        
    if "story" in categories or "narrative" in combined_explicit:
        concepts.add("story-driven")
        
    if "shooter" in combined_explicit or "fps" in combined_explicit:
        concepts.add("shooter")
        
    if "stealth" in combined_explicit:
        concepts.add("stealth")
        
    if "horror" in combined_explicit:
        concepts.add("horror")
        
    if "survival" in combined_explicit:
        concepts.add("survival")
        
    if "souls-like" in combined_explicit or "soulslike" in combined_explicit:
        concepts.update(["soulslike", "challenging"])
        
    if "platformer" in combined_explicit:
        concepts.add("platformer")
        
    if "roguelike" in combined_explicit or "roguelite" in combined_explicit:
        concepts.add("roguelike")
        
    if "puzzle" in combined_explicit:
        concepts.add("puzzle")
        
    if "sci-fi" in combined_explicit:
        concepts.add("sci-fi")
        
    if "fantasy" in combined_explicit:
        concepts.add("fantasy")

    return list(concepts.intersection(CONCEPT_VOCAB))
