from model.rigcheck_engine import run_rigcheck, _load_dataset
import pandas as pd
import json

def full_trace():
    df = _load_dataset()
    p2 = df[df["Title"] == "PAYDAY 2"].iloc[0]
    sts = df[df["Title"] == "Slay the Spire"].iloc[0]
    
    print("--- PAYDAY 2 DEBUG ---")
    print(f"Price_INR Type: {type(p2['Price_INR'])}")
    print(f"Price_INR Value: {p2['Price_INR']}")
    print(f"Price_INR <= 500: {p2['Price_INR'] <= 500}")
    
    print("\n--- SLAY THE SPIRE DEBUG ---")
    print(f"Price_INR Type: {type(sts['Price_INR'])}")
    print(f"Price_INR Value: {sts['Price_INR']}")
    print(f"Price_INR <= 1000: {sts['Price_INR'] <= 1000}")
    
    res = run_rigcheck(
        user_input="An action-packed co-op shooter where my friends and I plan and execute bank heists.",
        budget=500,
        user_gpu="GTX 1050",
        user_ram=8,
        user_cpu="AMD Ryzen 9 9950X3D",
        user_storage_gb=498
    )
    
    res2 = run_rigcheck(
        user_input="A roguelike deckbuilder where I climb a spire, collect cards, and battle monsters.",
        budget=1000,
        user_gpu="GTX 1060",
        user_ram=8,
        user_cpu="AMD Ryzen 9 9950X3D",
        user_storage_gb=498
    )

    with open("trace_results.json", "w", encoding="utf-8") as f:
        json.dump({"payday2": res, "sts": res2}, f, indent=4)
    print("\nDumped results to trace_results.json")

if __name__ == "__main__":
    full_trace()
