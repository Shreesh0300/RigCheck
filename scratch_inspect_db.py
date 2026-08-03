import json

with open("data/games_database_final.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Check screenshot and trailer format
for g in data[:3]:
    print(f"appid={g.get('appid')} | name={g.get('name')}")
    ss = g.get('screenshots', [])
    print(f"  screenshots ({len(ss)}): type={type(ss[0]) if ss else 'N/A'}")
    if ss:
        print(f"    sample: {ss[0][:120]}...")
    tr = g.get('trailers', [])
    print(f"  trailers ({len(tr)}): type={type(tr[0]) if tr else 'N/A'}")
    if tr:
        print(f"    sample: {tr[0][:120]}...")
    print()

# Check how screenshots are stored - string URLs or objects?
for g in data:
    ss = g.get('screenshots', [])
    if ss:
        first = ss[0]
        if isinstance(first, dict):
            print(f"DICT screenshots found in appid={g.get('appid')}, keys={list(first.keys())}")
            break
        elif isinstance(first, str):
            # Check if it has path_full or path_thumbnail substrings
            pass
        break
print()

# Count screenshot formats
str_count = 0
dict_count = 0
for g in data:
    ss = g.get('screenshots', [])
    if ss:
        if isinstance(ss[0], str):
            str_count += 1
        elif isinstance(ss[0], dict):
            dict_count += 1
print(f"Games with string screenshots: {str_count}")
print(f"Games with dict screenshots: {dict_count}")
