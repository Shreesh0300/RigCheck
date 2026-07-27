import json
import os
import time
import requests

def ensure_directory(path):
    """Ensure that a directory exists, creating it if necessary."""
    if not os.path.exists(path):
        os.makedirs(path)

def load_json(filepath, default=None):
    """Load JSON from a file, returning default if file doesn't exist or is invalid."""
    if not os.path.exists(filepath):
        return default
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return default

def save_json(filepath, data):
    """Save data to a JSON file."""
    tmp_filepath = f"{filepath}.tmp"
    with open(tmp_filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
        f.flush()
    os.replace(tmp_filepath, filepath)

def safe_request(url, max_retries=3, delay_between_retries=1.0):
    """Make an HTTP GET request with retries."""
    headers = {"User-Agent": "RigCheck/1.0"}
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            # Accept any successful status code (2xx)
            response.raise_for_status()
            return response
        except requests.exceptions.Timeout:
            print("Timeout occurred")
        except requests.exceptions.HTTPError as e:
            print(f"HTTP {e.response.status_code} {e.response.reason}")
        except requests.exceptions.ConnectionError:
            print("Connection Error")
        except requests.exceptions.RequestException as e:
            print(f"Request Exception: {e}")
            
        if attempt < max_retries - 1:
            print(f"Retry {attempt + 1}/{max_retries}")
            time.sleep(delay_between_retries)
        else:
            print(f"Failed after {max_retries} retries.")
            return None
