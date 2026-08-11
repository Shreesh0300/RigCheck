import os

def patch_engine():
    path = "v:/Projects/RigCheck/model/rigcheck_engine.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if "import re" not in content:
        content = "import re\n" + content

    old_clean = """def clean_and_expand_input(user_input):
    final_keywords = []"""

    new_clean = """# Phase 4: Game Acronym Expansion
_game_aliases = {}
_aliases_path = os.path.join(os.path.dirname(__file__), "..", "data", "game_aliases.json")
if os.path.exists(_aliases_path):
    with open(_aliases_path, "r", encoding="utf-8") as f:
        _game_aliases = json.load(f)

def expand_game_aliases(user_input):
    expanded = user_input
    for alias, canonical in _game_aliases.items():
        pattern = r'\\b' + re.escape(alias) + r'\\b'
        expanded = re.sub(pattern, lambda m: f"{m.group(0)} {canonical}", expanded, flags=re.IGNORECASE)
    return expanded

def clean_and_expand_input(user_input):
    user_input = expand_game_aliases(user_input)
    final_keywords = []"""

    content = content.replace(old_clean, new_clean)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print("Successfully patched rigcheck_engine.py with Phase 4 aliases!")

if __name__ == "__main__":
    patch_engine()
