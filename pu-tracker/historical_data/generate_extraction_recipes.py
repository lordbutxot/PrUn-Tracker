"""
Generate synthetic extraction recipes for tier-0 materials.

Extraction buildings (COL, EXT, RIG) extract raw materials but have no
traditional recipes in buildingrecipes.csv. This script creates synthetic
recipe data for them so workforce costs can be calculated.

Standard extraction rates (approximate, based on game mechanics):
- COL (Collector): ~24 hours per 100 units (gases, liquids)
- EXT (Extractor): ~24 hours per 100 units (ores, minerals)  
- RIG (Rig): ~48 hours per 100 units (rare ores, H2O)
"""

import pandas as pd
import json
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / "cache"

# Extraction building data (base times for average concentration)
EXTRACTION_BUILDINGS = {
    'COL': {'workforce': 'PIONEER', 'capacity': 50, 'base_hours_per_100': 24},
    'EXT': {'workforce': 'PIONEER', 'capacity': 60, 'base_hours_per_100': 24},
    'RIG': {'workforce': 'PIONEER', 'capacity': 30, 'base_hours_per_100': 48}
}

# Material types extracted by each building (based on category/type)
BUILDING_MATERIAL_TYPES = {
    'COL': ['gases'],  # Collects gases from atmospheres
    'EXT': ['ores', 'minerals'],  # Extracts solid resources
    'RIG': ['liquids', 'ores']  # Deep extraction (H2O, rare ores)
}

def load_planet_resource_factors():
    """
    Load planet resource concentration factors from planetresources.csv.
    Returns dict mapping material ticker to average extraction factor.
    
    Higher factor = better concentration = faster extraction.
    Factor typically ranges from 0.01 (very poor) to 1.0+ (excellent).
    """
    planetresources_path = CACHE_DIR / "planetresources.csv"
    
    if not planetresources_path.exists():
        print("[WARN] planetresources.csv not found, using default extraction times")
        return {}
    
    try:
        df = pd.read_csv(planetresources_path)
        
        # Calculate average factor per material across all planets
        avg_factors = df.groupby('Ticker')['Factor'].agg(['mean', 'min', 'max', 'count']).to_dict('index')
        
        print(f"[INFO] Loaded extraction factors for {len(avg_factors)} materials")
        print(f"[INFO] Sample factors: FEO={avg_factors.get('FEO', {}).get('mean', 0):.3f}, "
              f"H2O={avg_factors.get('H2O', {}).get('mean', 0):.3f}, "
              f"O={avg_factors.get('O', {}).get('mean', 0):.3f}")
        
        return avg_factors
    except Exception as e:
        print(f"[ERROR] Failed to load planet resources: {e}")
        return {}

def calculate_extraction_time(base_hours, avg_factor_data):
    """
    Calculate actual extraction time based on average planet concentration.
    
    Formula: actual_time = base_time / concentration_factor
    - High concentration (factor=1.0): 24h / 1.0 = 24h (fast)
    - Medium concentration (factor=0.5): 24h / 0.5 = 48h (average)
    - Low concentration (factor=0.1): 24h / 0.1 = 240h (very slow)
    
    Args:
        base_hours: Base extraction time (24h or 48h)
        avg_factor_data: Dict with 'mean', 'min', 'max', 'count' from planet data
    
    Returns:
        Adjusted extraction time in hours
    """
    if not avg_factor_data or 'mean' not in avg_factor_data:
        return base_hours  # No data, use default
    
    avg_factor = avg_factor_data['mean']
    
    # Avoid division by zero or extreme values
    if avg_factor <= 0.001:
        return base_hours * 10  # Very poor concentration = 10x slower
    
    # Calculate time: lower concentration = longer time
    adjusted_hours = base_hours / avg_factor
    
    # Cap at reasonable limits (6h minimum, 240h maximum per 100 units)
    adjusted_hours = max(6, min(240, adjusted_hours))
    
    return adjusted_hours

def get_extraction_building_for_material(ticker, material_name, category, tier):
    """
    Determine which extraction building produces a material.
    
    Args:
        ticker: Material ticker (e.g., 'FEO', 'H2O')
        material_name: Full name
        category: Material category
        tier: Material tier (should be 0 for extractables)
    
    Returns:
        Building code ('COL', 'EXT', or 'RIG') or None
    """
    if tier != 0.0:
        return None
        
    category_lower = category.lower()
    name_lower = material_name.lower()
    
    # Special cases
    if ticker == 'H2O' or 'water' in name_lower:
        return 'RIG'
    
    # Gas collectors
    if 'gas' in category_lower or ticker in ['H', 'O', 'N', 'CL', 'F', 'HE', 'NE', 'AR', 'H2']:
        return 'COL'
    
    # Deep rigs for specific ores
    if ticker in ['AUO', 'GAL', 'TIT']:  # Rare/valuable ores
        return 'RIG'
    
    # Default extractor for ores/minerals
    if 'ore' in category_lower or 'mineral' in category_lower:
        return 'EXT'
    
    # Fallback to extractor
    return 'EXT'


def generate_extraction_recipes():
    """
    Generate synthetic extraction recipes for all tier-0 materials.
    Uses BASE extraction times (24h/48h) without planet adjustment.
    Planet-specific adjustments are done in the frontend when user selects a planet.
    """
    print("\n[INFO] Generating extraction recipes for tier-0 materials...")
    
    # Load materials
    materials_path = CACHE_DIR / "materials.csv"
    if not materials_path.exists():
        print(f"[ERROR] materials.csv not found at {materials_path}")
        return False
    
    materials_df = pd.read_csv(materials_path)
    
    # Filter tier-0 materials
    tier0_materials = materials_df[materials_df['Tier'] == 0.0].copy()
    print(f"[INFO] Found {len(tier0_materials)} tier-0 materials")
    
    # Note: We're NOT loading planet factors here - we use base times only
    print(f"[INFO] Using base extraction times (24h for COL/EXT, 48h for RIG)")
    
    # Generate extraction recipes
    extraction_recipes = []
    extraction_outputs = []
    
    for _, mat in tier0_materials.iterrows():
        ticker = mat['Ticker']
        name = mat['Name']
        category = mat.get('Category', '')
        
        # Determine extraction building
        building = get_extraction_building_for_material(ticker, name, category, 0.0)
        
        if not building:
            print(f"[WARN] No extraction building for {ticker}")
            continue
        
        # Create synthetic recipe key (format: BUILDING=>100xTICKER)
        recipe_key = f"{building}=>100x{ticker}"
        
        # Get building data - USE BASE HOURS (no planet adjustment)
        building_data = EXTRACTION_BUILDINGS[building]
        base_hours = building_data['base_hours_per_100']
        workforce_capacity = building_data['capacity']
        
        # Use base extraction time directly (no planet factor adjustment)
        duration_seconds = int(base_hours * 3600)
        time_minutes = base_hours * 60  # Convert to minutes for Time column
        
        # Add to extraction recipes (buildingrecipes format)
        # Include all required columns: Key, Building, Duration, Time, Workforce, WorkforceAmount
        extraction_recipes.append({
            'Key': recipe_key,
            'Building': building,
            'Duration': duration_seconds,
            'Time': time_minutes,
            'Workforce': 'Pioneer',
            'WorkforceAmount': workforce_capacity
        })
        
        # Add to extraction outputs (recipe_outputs format)
        extraction_outputs.append({
            'Key': recipe_key,
            'Material': ticker,
            'Amount': 100
        })
        
        # Show extraction info
        print(f"[INFO] {ticker:4} -> {building} (Pioneer x{building_data['capacity']}, {base_hours}h/100 units - BASE TIME)")
    
    # Save extraction recipes
    extraction_recipes_df = pd.DataFrame(extraction_recipes)
    extraction_recipes_path = CACHE_DIR / "extraction_recipes.csv"
    extraction_recipes_df.to_csv(extraction_recipes_path, index=False)
    print(f"[SUCCESS] Saved {len(extraction_recipes)} extraction recipes to extraction_recipes.csv")
    
    # Save extraction outputs  
    extraction_outputs_df = pd.DataFrame(extraction_outputs)
    extraction_outputs_path = CACHE_DIR / "extraction_outputs.csv"
    extraction_outputs_df.to_csv(extraction_outputs_path, index=False)
    print(f"[SUCCESS] Saved {len(extraction_outputs)} extraction outputs to extraction_outputs.csv")
    
    # Merge with existing buildingrecipes.csv (remove any existing extraction recipes first)
    buildingrecipes_path = CACHE_DIR / "buildingrecipes.csv"
    if buildingrecipes_path.exists():
        existing_recipes = pd.read_csv(buildingrecipes_path)
        # Remove old extraction recipes (Key starts with COL=>, EXT=>, or RIG=>)
        existing_recipes = existing_recipes[~existing_recipes['Key'].str.match(r'^(COL|EXT|RIG)=>')]
        combined_recipes = pd.concat([existing_recipes, extraction_recipes_df], ignore_index=True)
        # Remove any duplicates based on Key
        combined_recipes = combined_recipes.drop_duplicates(subset=['Key'], keep='last')
        combined_recipes.to_csv(buildingrecipes_path, index=False)
        print(f"[SUCCESS] Merged extraction recipes into buildingrecipes.csv ({len(combined_recipes)} total)")
    
    # Merge with existing recipe_outputs.csv (remove any existing extraction outputs first)
    recipe_outputs_path = CACHE_DIR / "recipe_outputs.csv"
    if recipe_outputs_path.exists():
        existing_outputs = pd.read_csv(recipe_outputs_path)
        # Remove old extraction outputs
        existing_outputs = existing_outputs[~existing_outputs['Key'].str.match(r'^(COL|EXT|RIG)=>')]
        combined_outputs = pd.concat([existing_outputs, extraction_outputs_df], ignore_index=True)
        # Remove any duplicates based on Key
        combined_outputs = combined_outputs.drop_duplicates(subset=['Key'], keep='last')
        combined_outputs.to_csv(recipe_outputs_path, index=False)
        print(f"[SUCCESS] Merged extraction outputs into recipe_outputs.csv ({len(combined_outputs)} total)")
    
    return True


if __name__ == "__main__":
    success = generate_extraction_recipes()
    if success:
        print("\n[SUCCESS] Extraction recipes generated successfully!")
    else:
        print("\n[ERROR] Failed to generate extraction recipes")
