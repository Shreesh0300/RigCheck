import logging

# Set up temporary debug logging
debug_log = []

def log_debug_info(game, game_price, price_type, price_currency, user_budget, normalized_price, normalized_budget, price_lte_budget, compatibility, final_eligible):
    debug_log.append({
        "GAME": game,
        "GAME PRICE": game_price,
        "PRICE TYPE": price_type,
        "PRICE CURRENCY": price_currency,
        "USER BUDGET": user_budget,
        "NORMALIZED PRICE": normalized_price,
        "NORMALIZED BUDGET": normalized_budget,
        "PRICE <= BUDGET": price_lte_budget,
        "COMPATIBILITY": compatibility,
        "FINAL ELIGIBLE": final_eligible
    })
    print(f"\n--- DEBUG LOG FOR {game} ---")
    print(f"GAME: {game}")
    print(f"GAME PRICE: {game_price}")
    print(f"PRICE TYPE: {price_type}")
    print(f"PRICE CURRENCY: {price_currency}")
    print(f"USER BUDGET: {user_budget}")
    print(f"NORMALIZED PRICE: {normalized_price}")
    print(f"NORMALIZED BUDGET: {normalized_budget}")
    print(f"PRICE <= BUDGET: {price_lte_budget}")
    print(f"COMPATIBILITY: {compatibility}")
    print(f"FINAL ELIGIBLE: {final_eligible}")
