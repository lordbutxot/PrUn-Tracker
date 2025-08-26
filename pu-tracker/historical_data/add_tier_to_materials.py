import pandas as pd
import os
import json

def main():
    """Main function to add tier information to materials."""
    try:
        cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'cache'))
        materials_path = os.path.join(cache_dir, "materials.csv")

        if not os.path.exists(materials_path):
            print(f"Materials file not found at {materials_path}")
            return

        # Load materials CSV
        df = pd.read_csv(materials_path)

        # Load tier information from chains.json if it exists
        chains_path = os.path.join(cache_dir, "chains.json")
        if os.path.exists(chains_path):
            with open(chains_path, 'r', encoding='utf-8') as f:
                chains = json.load(f)
            
            # Update tier information from chains
            for ticker, chain_info in chains.items():
                if isinstance(chain_info, dict) and 'tier' in chain_info:
                    mask = df['Ticker'].str.lower() == ticker.lower()
                    if mask.any():
                        df.loc[mask, 'Tier'] = chain_info['tier']
            
            print(f"Updated tier information from chains.json for {len(chains)} materials")
        else:
            # If no chains.json, just add default tier column
            if 'Tier' not in df.columns:
                df['Tier'] = 0
                print("Added 'Tier' column with default value 0.")
            else:
                df['Tier'] = df['Tier'].fillna(0)
                print("'Tier' column already exists. Filled missing values with 0.")

        # Save updated materials
        df.to_csv(materials_path, index=False)
        print(f"Updated {materials_path}")

        # Also create a separate tiers.json file for easy access
        tiers_dict = dict(zip(df['Ticker'].str.lower(), df['Tier']))
        tiers_path = os.path.join(cache_dir, "tiers.json")
        with open(tiers_path, "w", encoding="utf-8") as f:
            json.dump(tiers_dict, f, indent=2)
        print(f"Created {tiers_path} with {len(tiers_dict)} tier mappings")
        
    except Exception as e:
        print(f"Error adding tier to materials: {e}")
        raise

if __name__ == "__main__":
    main()