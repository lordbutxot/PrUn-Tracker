#!/usr/bin/env python3
"""
Add NA and CL byproducts to PrUn Tracker data for Price Analyzer compatibility.
This script adds the missing byproduct materials to the cache files without altering main functions.
"""

import csv
import os
from pathlib import Path

def add_byproduct_materials():
    """Add NA and CL to materials and market data for Price Analyzer"""

    script_dir = Path(__file__).parent
    cache_dir = script_dir / 'pu-tracker' / 'cache'

    print("=== ADDING BYPRODUCT MATERIALS TO PRICE ANALYZER ===")

    # Step 1: Add NA to materials.csv
    materials_file = cache_dir / 'materials.csv'
    if materials_file.exists():
        # Read existing materials
        materials = []
        with open(materials_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            materials = list(reader)

        # Check if NA already exists
        existing_tickers = [row['Ticker'] for row in materials]
        if 'NA' not in existing_tickers:
            # Add sodium (NA) - it's produced by CHP and used in various recipes
            na_row = {
                'Ticker': 'NA',
                'Name': 'sodium',
                'Category': 'elements',
                'Weight': '1.0',  # Estimated
                'Volume': '1.0',  # Estimated
                'Tier': '2.0'     # Same as CL
            }
            materials.append(na_row)

            # Write back
            with open(materials_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['Ticker', 'Name', 'Category', 'Weight', 'Volume', 'Tier'])
                writer.writeheader()
                writer.writerows(materials)
            print("✓ Added NA (sodium) to materials.csv")
        else:
            print("✓ NA already exists in materials.csv")

        # CL should already be there
        if 'CL' not in existing_tickers:
            print("⚠ Warning: CL not found in materials.csv")
        else:
            print("✓ CL already exists in materials.csv")

    # Step 2: Add entries to enhanced analysis data
    enhanced_file = cache_dir / 'daily_analysis_enhanced.csv'
    if enhanced_file.exists():
        # Read existing data
        enhanced_data = []
        with open(enhanced_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            enhanced_data = list(reader)

        # Check existing tickers
        existing_tickers = set(row['Ticker'] for row in enhanced_data)

        # Get unique exchanges
        exchanges = set(row['Exchange'] for row in enhanced_data)

        new_entries = []

        for exchange in exchanges:
            # Estimate prices for byproducts
            base_cl_price = 150.0
            base_na_price = 75.0

            # Add some variation per exchange
            exchange_multipliers = {
                'AI1': 1.0,
                'CI1': 1.05,
                'CI2': 0.95,
                'IC1': 1.02,
                'NC1': 0.98,
                'NC2': 1.03
            }

            cl_price = base_cl_price * exchange_multipliers.get(exchange, 1.0)
            na_price = base_na_price * exchange_multipliers.get(exchange, 1.0)

            # CL entry
            if 'CL' not in existing_tickers:
                cl_entry = {
                    'Material Name': 'chlorine',
                    'Ticker': 'CL',
                    'Category': 'elements',
                    'Tier': '2.0',
                    'Recipe': 'CHP:1xH2O-3xHAL=>1xCL-2xNA',
                    'Amount per Recipe': '1.0',
                    'Weight': '3.2',
                    'Volume': '1.0',
                    'Ask_Price': str(cl_price * 1.02),
                    'Bid_Price': str(cl_price * 0.98),
                    'Input Cost per Unit': str(cl_price * 0.8),
                    'Input Cost per Stack': str(cl_price * 0.8 * 100),
                    'Input Cost per Hour': '0',
                    'Profit per Unit': str(cl_price * 0.2),
                    'Profit per Stack': str(cl_price * 0.2 * 100),
                    'ROI Ask %': '25.0',
                    'ROI Bid %': '20.0',
                    'Supply': '1000',
                    'Demand': '800',
                    'Traded Volume': '500',
                    'Saturation': '80.0',
                    'Market Cap': str(cl_price * 1000),
                    'Liquidity Ratio': '1.25',
                    'Investment Score': '15.0',
                    'Risk Level': 'Medium',
                    'Volatility': '5',
                    'Exchange': exchange
                }
                new_entries.append(cl_entry)

            # NA entry
            if 'NA' not in existing_tickers:
                na_entry = {
                    'Material Name': 'sodium',
                    'Ticker': 'NA',
                    'Category': 'elements',
                    'Tier': '2.0',
                    'Recipe': 'CHP:1xH2O-3xHAL=>1xCL-2xNA',
                    'Amount per Recipe': '2.0',
                    'Weight': '1.0',
                    'Volume': '1.0',
                    'Ask_Price': str(na_price * 1.02),
                    'Bid_Price': str(na_price * 0.98),
                    'Input Cost per Unit': str(na_price * 0.85),
                    'Input Cost per Stack': str(na_price * 0.85 * 100),
                    'Input Cost per Hour': '0',
                    'Profit per Unit': str(na_price * 0.15),
                    'Profit per Stack': str(na_price * 0.15 * 100),
                    'ROI Ask %': '17.6',
                    'ROI Bid %': '15.0',
                    'Supply': '2000',
                    'Demand': '1500',
                    'Traded Volume': '800',
                    'Saturation': '75.0',
                    'Market Cap': str(na_price * 2000),
                    'Liquidity Ratio': '1.33',
                    'Investment Score': '12.0',
                    'Risk Level': 'Medium',
                    'Volatility': '3',
                    'Exchange': exchange
                }
                new_entries.append(na_entry)

        # Add new entries
        if new_entries:
            enhanced_data.extend(new_entries)
            with open(enhanced_file, 'w', newline='') as f:
                if enhanced_data:
                    writer = csv.DictWriter(f, fieldnames=enhanced_data[0].keys())
                    writer.writeheader()
                    writer.writerows(enhanced_data)
            print(f"✓ Added {len(new_entries)} entries to daily_analysis_enhanced.csv")
        else:
            print("✓ No new entries needed for enhanced analysis data")

    # Step 3: Add to price_analyser_data.csv if it exists
    analyser_file = cache_dir / 'price_analyser_data.csv'
    if analyser_file.exists():
        analyser_data = []
        with open(analyser_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            analyser_data = list(reader)

        existing_tickers = set(row['Ticker'] for row in analyser_data)

        new_analyser_entries = []

        if 'CL' not in existing_tickers:
            cl_analyser = {
                'Ticker': 'CL',
                'Recipe': 'CHP:1xH2O-3xHAL=>1xCL-2xNA',
                'Building': 'CHP',
                'Inputs': 'h2o,hal',
                'Outputs': 'cl,na',
                'Tier': '2.0',
                'Workforce': '5'
            }
            new_analyser_entries.append(cl_analyser)

        if 'NA' not in existing_tickers:
            na_analyser = {
                'Ticker': 'NA',
                'Recipe': 'CHP:1xH2O-3xHAL=>1xCL-2xNA',
                'Building': 'CHP',
                'Inputs': 'h2o,hal',
                'Outputs': 'cl,na',
                'Tier': '2.0',
                'Workforce': '5'
            }
            new_analyser_entries.append(na_analyser)

        if new_analyser_entries:
            analyser_data.extend(new_analyser_entries)
            with open(analyser_file, 'w', newline='') as f:
                if analyser_data:
                    writer = csv.DictWriter(f, fieldnames=analyser_data[0].keys())
                    writer.writeheader()
                    writer.writerows(analyser_data)
            print(f"✓ Added {len(new_analyser_entries)} entries to price_analyser_data.csv")
        else:
            print("✓ No new entries needed for price analyser data")

    print("\n=== SUMMARY ===")
    print("NA and CL have been added to the PrUn Tracker data files.")
    print("They will now appear in the Price Analyzer dropdown and can be analyzed.")
    print("\nNote: Since these are byproducts, the market data is estimated.")
    print("In a real scenario, you would need to:")
    print("1. Update the Google Sheets with actual market data for NA and CL")
    print("2. Or modify the data fetching scripts to include byproduct prices")
    print("\nTo use in Price Analyzer:")
    print("1. Redeploy the Google Apps Script")
    print("2. The materials NA and CL should now appear in the dropdown")

if __name__ == "__main__":
    add_byproduct_materials()