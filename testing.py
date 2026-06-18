"""Local scratch pad for manual testing.

Keep terminal interaction and NLP logic out of this file. The recommendation
engine lives in model/rigcheck_engine.py and can be called directly.
"""

from model.rigcheck_engine import recommend_game


def sample_request():
    return recommend_game(
        user_input="story rich platformer",
        budget=1000,
        gpu_tier=2,
        ram=8,
    )