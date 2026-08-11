import os

def update_eval():
    path = "v:/Projects/RigCheck/evaluate_search.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Inject new queries
    new_queries = """    "Vague_Coop": "coop game",

    # ---------------------------------------------
    # PHASE 4 ALIAS TESTS
    # ---------------------------------------------
    "Alias_rdr2_1": "rdr2",
    "Alias_RDR2_2": "RDR2",
    "Alias_rdr_2": "rdr 2",
    "Alias_gta": "gta",
    "Alias_gta_5": "gta 5",
    "Alias_gta_v": "gta v",
    "Alias_l4d2": "l4d2",
    "Alias_cs2": "cs2",
    "Alias_tlou": "tlou",
    
    # Context Tests
    "Context_gta_5": "games similar to gta 5",
    "Context_rdr2_1": "open world games like rdr2",
    "Context_rdr2_2": "rdr2 style western game",
    "Context_l4d2": "games like l4d2",
    "Context_cs2": "something like cs2 but tactical"
}"""
    
    content = content.replace('    "Vague_Coop": "coop game"\n}', new_queries)
    
    # Inject targets
    new_targets = """    "Multi_StealthSamurai": "Sekiro™: Shadows Die Twice - GOTY Edition",
    
    "Alias_rdr2_1": "Red Dead Redemption 2",
    "Alias_RDR2_2": "Red Dead Redemption 2",
    "Alias_rdr_2": "Red Dead Redemption 2",
    "Alias_gta": "Grand Theft Auto V Legacy",
    "Alias_gta_5": "Grand Theft Auto V Legacy",
    "Alias_gta_v": "Grand Theft Auto V Legacy",
    "Alias_l4d2": "Left 4 Dead 2",
    "Alias_cs2": "Counter-Strike 2",
    "Alias_tlou": "The Last of Us™ Part I",
    
    "Context_gta_5": "Grand Theft Auto V Legacy",
    "Context_rdr2_1": "Red Dead Redemption 2",
    "Context_rdr2_2": "Red Dead Redemption 2",
    "Context_l4d2": "Left 4 Dead 2",
    "Context_cs2": "Counter-Strike 2"
}"""
    
    content = content.replace('    "Multi_StealthSamurai": "Sekiro™: Shadows Die Twice - GOTY Edition"\n}', new_targets)
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    update_eval()
