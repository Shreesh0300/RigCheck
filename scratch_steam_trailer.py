import json
import requests

# Fetch Uncharted from Steam API
appid = 1659420
url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
response = requests.get(url, timeout=10)
data = response.json()

if str(appid) in data and data[str(appid)].get('success'):
    app_data = data[str(appid)]['data']
    
    # Check movies field
    movies = app_data.get('movies', [])
    print(f"MOVIES COUNT: {len(movies)}")
    if movies:
        print("\nFIRST MOVIE KEYS:")
        print(json.dumps(list(movies[0].keys()), indent=2))
        print("\nFIRST MOVIE FULL DATA:")
        print(json.dumps(movies[0], indent=2))
    else:
        print("NO MOVIES FOUND IN STEAM RESPONSE")
    
    # Check for any mp4/webm/dash fields
    print("\n=== SEARCHING FOR VIDEO FIELDS ===")
    for movie in movies:
        print(f"\nMovie: {movie.get('name')}")
        for key in movie:
            if key in ('mp4', 'webm', 'dash_h264', 'hls_h264', 'dash_av1'):
                print(f"  {key}: {json.dumps(movie[key], indent=4)}")
else:
    print("STEAM API REQUEST FAILED")
