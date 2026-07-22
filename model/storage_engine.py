"""
RigCheck Storage Availability Engine
======================================
Pure availability check — NOT a performance metric.

No tiers.  No scores.  No rankings.  No upgrade suggestions.
Only answers: "Can the user install this game?"

Functions:
    check_storage(user_free_gb, game_required_gb) -> dict
"""

from __future__ import annotations


def check_storage(user_free_gb: float, game_required_gb: float) -> dict:
    """
    Check whether the user has enough free storage to install a game.

    Parameters
    ----------
    user_free_gb : float
        Free storage the user currently has (in GB).
    game_required_gb : float
        Storage the game requires for installation (in GB).

    Returns
    -------
    dict with keys:
        status       : "PASS" | "FAIL"
        required_gb  : float  — storage the game needs
        available_gb : float  — storage the user has
        missing_gb   : float  — shortfall (0 when PASS)
        message      : str    — human-readable summary
    """
    if user_free_gb < 0:
        user_free_gb = 0.0
    if game_required_gb < 0:
        game_required_gb = 0.0

    user_free_gb = round(float(user_free_gb), 2)
    game_required_gb = round(float(game_required_gb), 2)

    if user_free_gb >= game_required_gb:
        return {
            "status": "PASS",
            "required_gb": game_required_gb,
            "available_gb": user_free_gb,
            "missing_gb": 0,
            "message": "✅ Enough storage",
        }

    missing = round(game_required_gb - user_free_gb, 2)
    return {
        "status": "FAIL",
        "required_gb": game_required_gb,
        "available_gb": user_free_gb,
        "missing_gb": missing,
        "message": f"❌ Need {missing}GB more free storage",
    }
