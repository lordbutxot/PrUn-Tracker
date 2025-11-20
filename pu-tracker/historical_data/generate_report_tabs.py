import pandas as pd
from pathlib import Path
import sys
import time
import concurrent.futures
import json

try:
    from sheets_manager import UnifiedSheetsManager as SheetsManager
except ImportError:
    from sheets_manager import SheetsManager

# Import refactored modules
from loaders import load_recipe_inputs, load_recipe_outputs, load_buildingrecipes, load_workforceneeds
from calculators import calculate_detailed_costs

EXCHANGES = ['AI1', 'CI1', 'CI2', 'IC1', 'NC1', 'NC2']
PROFESSION_ORDER = [
    'METALLURGY', 'MANUFACTURING', 'CONSTRUCTION', 'CHEMISTRY',
    'FOOD_INDUSTRIES', 'AGRICULTURE', 'FUEL_REFINING', 'ELECTRONICS',
    'RESOURCE_EXTRACTION'
]
REPORT_TABS = [f"Report {exch}" for exch in EXCHANGES]
SPREADSHEET_ID = "1-9vXBU43YjU6LMdivpVwL2ysLHANShHzrCW6MmmGvoI"

CACHE_DIR = Path(__file__).parent.parent / "cache"
ENHANCED_FILE = CACHE_DIR / "daily_analysis_enhanced.csv"
ORDERS_FILE = CACHE_DIR / "orders.csv"

REPORT_COLUMNS = [
    "Ticker", "Name", "Product", "Buy Price", "Sell Price", "Profit",
    "Buy Exchange", "Sell Exchange", "ROI", "Opportunity Size", "Opportunity Level"
]

def section_header(title, width):
    return [[title.upper()] + [""] * (width - 1)]

def summary_section(df):
    width = 4
    # --- ENSURE COLUMN NAMES EXIST ---
    profit_col = 'Profit per Unit' if 'Profit per Unit' in df.columns else 'Profit_Ask'
    roi_col = 'ROI_Ask' if 'ROI_Ask' in df.columns else 'ROI Ask %'
    rows = [
        ["SUMMARY", "", "", ""],
        ["Total Products", len(df), "", ""],
        ["Median Profit", f"{df[profit_col].median():,.2f}" if profit_col in df else "", "", ""],
        ["Median ROI", f"{df[roi_col].median():.2f}%" if roi_col in df else "", "", ""],
        ["", "", "", ""]
    ]
    return rows

def arbitrage_section(arbitrage_df, exch, top_n=None, orders_df=None):
    df = arbitrage_df[arbitrage_df['Buy Exchange'] == exch].copy()
    df = df[(df['Profit'] > 0) & (df['Opportunity Size'] > 0)]
    level_order = {'Very High': 0, 'High': 1, 'Medium': 2, 'Low': 3, 'Very Low': 4}
    df['LevelSort'] = df['Opportunity Level'].map(level_order).astype('float64').fillna(99)
    df = df.sort_values(['Sell Exchange', 'LevelSort', 'Opportunity Size'], ascending=[True, True, False])
    df = df.drop(columns=['LevelSort'])
    for col in ["Buy Price", "Sell Price", "Profit"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            df[col] = df[col].map('{:,.2f}'.format)
    subheader = REPORT_COLUMNS
    rows = df[REPORT_COLUMNS].values.tolist()
    return section_header("Arbitrage Opportunities", len(subheader)) + [subheader] + rows + [[""] * len(subheader)]

def buy_vs_produce_section(df, exch, top_n=None):
    # Show EACH recipe separately instead of aggregating by ticker
    exch_df = df[df['Exchange'] == exch] if 'Exchange' in df.columns else df
    rows = []
    subheader = ["Name", "Ticker", "Recipe", "Building", "Buy Price", "Produce Cost", "Difference", "Recommendation", "Level"]
    
    for _, row in exch_df.iterrows():
        ticker = row.get('Ticker', '')
        recipe = row.get('Recipe', 'N/A')
        building = row.get('Building', 'N/A')
        
        # Convert recipe to string and handle NaN/None
        if pd.isna(recipe) or recipe is None or recipe == '':
            recipe = 'N/A'
        else:
            recipe = str(recipe)
        
        # Convert building to string and handle NaN/None
        if pd.isna(building) or building is None or building == '':
            building = 'N/A'
        else:
            building = str(building)
        
        # Try both possible column names for Ask Price
        buy_price = (
            row.get('Ask Price', None)
            if 'Ask Price' in row else
            row.get('Ask_Price', None)
        )
        if buy_price is None or pd.isna(buy_price):
            buy_price = 0
        produce_cost = (
            row.get('Input Cost per Unit', None)
            if 'Input Cost per Unit' in row else
            row.get('Input_Cost_per_Unit', None)
        )
        if produce_cost is None or pd.isna(produce_cost):
            produce_cost = 0
        
        # Skip N/A recipes (raw materials)
        if recipe == 'N/A':
            continue
            
        diff = buy_price - produce_cost
        if diff < -100:
            rec, level = "Buy", "High"
        elif diff < -20:
            rec, level = "Buy", "Medium"
        elif abs(diff) <= 20:
            rec, level = "Neutral", "Low"
        elif diff > 100:
            rec, level = "Produce", "High"
        elif diff > 20:
            rec, level = "Produce", "Medium"
        else:
            rec, level = "Depends", "Low"
        
        rows.append([
            row.get('Material Name', ticker),
            ticker,
            recipe[:30] if len(recipe) > 30 else recipe,  # Truncate long recipe names
            building,
            f"{buy_price:,.2f}" if buy_price else "0",
            f"{produce_cost:,.2f}" if produce_cost else "0",
            f"{diff:,.2f}" if not pd.isna(diff) else "0",
            rec,
            level
        ])
    def sort_key(x):
        rec_order = {"Buy": 0, "Produce": 1, "Neutral": 2, "Depends": 3}
        rec = x[7]  # Updated from 5 to 7 (Recommendation column)
        try:
            diff_val = abs(float(x[6].replace(',', ''))) if x[6] != "N/A" else 0  # Updated from 4 to 6 (Difference column)
        except Exception:
            diff_val = 0
        return (rec_order.get(rec, 99), -diff_val)
    rows = sorted(rows, key=sort_key)
    return section_header("Buy vs Produce", len(subheader)) + [subheader] + rows + [[""] * len(subheader)]

def top_invest_section(df, exch, top_n=20):
    df = df.copy()
    # Use Bid/Ask for buy/sell price display if available
    if "Buy Price" not in df.columns and "Ask_Price" in df.columns:
        df["Buy Price"] = df["Ask_Price"]
    if "Sell Price" not in df.columns and "Bid_Price" in df.columns:
        df["Sell Price"] = df["Bid_Price"]
    # Use stored 'Profit per Unit' from data instead of calculating
    if "Profit per Unit" in df.columns:
        df["Profit"] = df["Profit per Unit"]
    elif "Profit_Ask" in df.columns:
        df["Profit"] = df["Profit_Ask"]
    else:
        # Fallback: calculate from Bid - Input Cost
        if "Bid_Price" in df.columns and "Input Cost per Unit" in df.columns:
            df["Profit"] = df["Bid_Price"] - df["Input Cost per Unit"]
        else:
            df["Profit"] = 0
    # --- FILL 'Investment Score' IF MISSING ---
    if "Investment Score" not in df.columns and "Investment_Score" in df.columns:
        df["Investment Score"] = df["Investment_Score"]
    top_invest = df.sort_values("Investment Score", ascending=False).head(top_n)
    subheader = ["Ticker", "Name", "Product", "Buy Price", "Sell Price", "Profit", "Investment Score"]
    rows = []
    for _, row in top_invest.iterrows():
        rows.append([
            row.get("Ticker", ""),
            row.get("Name", row.get("Material Name", "")),
            row.get("Product", ""),
            row.get("Buy Price", ""),
            row.get("Sell Price", ""),
            row.get("Profit", ""),
            row.get("Investment Score", ""),
        ])
    return section_header("TOP MATERIALS TO INVEST IN", len(subheader)) + [subheader] + rows + [[""] * len(subheader)]

def bottleneck_section(df, exch, top_n=None):
    df = df.copy()
    # Add this block to ensure Sell Price exists
    if "Sell Price" not in df.columns and "Bid_Price" in df.columns:
        df["Sell Price"] = df["Bid_Price"]
    if "Buy Price" not in df.columns and "Ask_Price" in df.columns:
        df["Buy Price"] = df["Ask_Price"]
    if "Input Cost per Unit" not in df.columns:
        df["Input Cost per Unit"] = 0
    df["Profit"] = df["Sell Price"] - df["Input Cost per Unit"]

    # Add InputCount if available
    if "InputCount" not in df.columns and "Ticker" in df.columns:
        recipe_inputs_path = Path(__file__).parent.parent / "cache" / "recipe_inputs.csv"
        if recipe_inputs_path.exists():
            recipe_inputs = pd.read_csv(recipe_inputs_path)
            input_counts = recipe_inputs['Material'].value_counts().to_dict()
            df['InputCount'] = df['Ticker'].map(input_counts).fillna(0)
        else:
            df['InputCount'] = 0

    # Detect No Stock and No Buyers situations
    critical_issues = []
    for _, row in df.iterrows():
        supply = row.get("Supply", 0)
        demand = row.get("Demand", 0)
        
        if supply == 0 and demand > 0:
            critical_issues.append({
                'Ticker': row.get('Ticker', ''),
                'Name': row.get('Material Name', row.get('Name', '')),
                'Product': row.get('Product', ''),
                'Buy Price': row.get('Buy Price', 0),
                'Sell Price': row.get('Sell Price', 0),
                'Profit': row.get('Profit', 0),
                'Supply': 0,
                'Demand': demand,
                'Chokepoint Type': 'No Stock',
                'Level': 'Critical'
            })
        elif demand == 0 and supply > 0:
            critical_issues.append({
                'Ticker': row.get('Ticker', ''),
                'Name': row.get('Material Name', row.get('Name', '')),
                'Product': row.get('Product', ''),
                'Buy Price': row.get('Buy Price', 0),
                'Sell Price': row.get('Sell Price', 0),
                'Profit': row.get('Profit', 0),
                'Supply': supply,
                'Demand': 0,
                'Chokepoint Type': 'No Buyers',
                'Level': 'Critical'
            })

    # Normalize for composite score
    df['SupplyNorm'] = 1 - (df['Supply'] / (df['Supply'].max() or 1))
    df['DemandNorm'] = df['Demand'] / (df['Demand'].max() or 1)
    df['ProfitNorm'] = df['Profit'] / (df['Profit'].max() or 1)
    df['InputNorm'] = df['InputCount'] / (df['InputCount'].max() or 1)

    # Composite score (tune weights as needed)
    df['BottleneckScore'] = (
        0.4 * df['SupplyNorm'] +
        0.3 * df['DemandNorm'] +
        0.2 * df['ProfitNorm'] +
        0.1 * df['InputNorm']
    )

    # Filter: show only items with high score (top 20% or score > 0.6)
    score_thresh = df['BottleneckScore'].quantile(0.8)
    filtered = df[df['BottleneckScore'] >= score_thresh]

    # Compute Chokepoint Type and Level for filtered items
    chokepoint_types = []
    levels = []
    for _, row in filtered.iterrows():
        supply = row.get("Supply", 0)
        demand = row.get("Demand", 0)
        if supply < 100 and demand > 0:
            ctype = "Low Supply & High Demand"
        elif supply < 100:
            ctype = "Low Supply"
        elif demand > 0:
            ctype = "High Demand"
        else:
            ctype = ""
        if supply < 25 or demand > 500:
            level = "High"
        elif supply < 60 or demand > 200:
            level = "Medium"
        else:
            level = "Low"
        chokepoint_types.append(ctype)
        levels.append(level)
    filtered = filtered.copy()
    filtered["Chokepoint Type"] = chokepoint_types
    filtered["Level"] = levels

    # Filter out rows with empty Chokepoint Type
    filtered = filtered[filtered["Chokepoint Type"] != ""]

    # Sort by Chokepoint Type, then Level (Critical > High > Medium > Low)
    level_order = {"Critical": -1, "High": 0, "Medium": 1, "Low": 2}
    filtered["LevelSort"] = filtered["Level"].map(level_order)
    filtered = filtered.sort_values(["Chokepoint Type", "LevelSort"])
    
    subheader = [
        "Ticker", "Name", "Product", "Buy Price", "Sell Price", "Profit",
        "Supply", "Demand", "Chokepoint Type", "Level"
    ]
    rows = []
    
    # Add critical issues first (No Stock, No Buyers)
    for issue in critical_issues:
        rows.append([
            issue["Ticker"],
            issue["Name"],
            issue["Product"],
            issue["Buy Price"],
            issue["Sell Price"],
            issue["Profit"],
            issue["Supply"],
            issue["Demand"],
            issue["Chokepoint Type"],
            issue["Level"]
        ])
    
    # Add other bottlenecks
    for _, row in filtered.iterrows():
        rows.append([
            row.get("Ticker", ""),
            row.get("Name", row.get("Material Name", "")),
            row.get("Product", ""),
            row.get("Buy Price", ""),
            row.get("Sell Price", ""),
            row.get("Profit", ""),
            row.get("Supply", ""),
            row.get("Demand", ""),
            row.get("Chokepoint Type", ""),
            row.get("Level", "")
        ])
    
    if not rows:
        return section_header("CHOKEPOINTS/BOTTLENECKS", len(subheader)) + [[""] * len(subheader)]
    
    return section_header("CHOKEPOINTS/BOTTLENECKS", len(subheader)) + [subheader] + rows + [[""] * len(subheader)]

def pad_section(section, n_rows, width):
    while len(section) < n_rows:
        section.append([""] * width)
    return section

def top_20_traded_section(market_data_path, exch=None):
    df = pd.read_csv(market_data_path)
    # Filter by exchange if provided and column exists
    if exch and 'Exchange' in df.columns:
        df = df[df['Exchange'] == exch]
    # Show top 20 for this exchange
    if 'Traded' in df.columns and 'Ticker' in df.columns:
        traded = df.groupby('Ticker')['Traded'].sum().reset_index()
        traded = traded.sort_values('Traded', ascending=False).head(20)
        subheader = ["Ticker", "Total Traded Amount"]
        rows = traded.values.tolist()
    else:
        amt_cols = [col for col in df.columns if col.endswith('Amt')]
        if amt_cols and 'Ticker' in df.columns:
            df['TotalAmt'] = df[amt_cols].sum(axis=1)
            traded = df.groupby('Ticker')['TotalAmt'].sum().reset_index()
            traded = traded.sort_values('TotalAmt', ascending=False).head(20)
            subheader = ["Ticker", "Total Traded Amount"]
            rows = traded.values.tolist()
        else:
            subheader = ["Ticker", "Total Traded Amount"]
            rows = [["", ""]]
    return section_header("Top Traded Products", len(subheader)) + [subheader] + rows + [[""] * len(subheader)]

def build_report_tab(df, exch, arbitrage_df, all_df, orders_df=None, market_data_path=None):
    summary = summary_section(df)
    arbitrage = arbitrage_section(arbitrage_df, exch, orders_df=orders_df)
    buy_vs_produce = buy_vs_produce_section(all_df, exch)
    top_invest = top_invest_section(df, exch)
    bottleneck = bottleneck_section(df, exch, top_n=20)
    top_traded = top_20_traded_section(market_data_path, exch=exch) if market_data_path else []
    
    # NEW: Add profession sections
    metallurgy = profession_section(df, exch, "METALLURGY")
    manufacturing = profession_section(df, exch, "MANUFACTURING")
    construction = profession_section(df, exch, "CONSTRUCTION")
    chemistry = profession_section(df, exch, "CHEMISTRY")
    food = profession_section(df, exch, "FOOD_INDUSTRIES")
    agriculture = profession_section(df, exch, "AGRICULTURE")
    fuel = profession_section(df, exch, "FUEL_REFINING")
    electronics = profession_section(df, exch, "ELECTRONICS")
    extraction = profession_section(df, exch, "RESOURCE_EXTRACTION")

    max_rows = max(
        len(summary), len(arbitrage), len(buy_vs_produce), len(top_invest), 
        len(bottleneck), len(top_traded), len(metallurgy), len(manufacturing),
        len(construction), len(chemistry), len(food), len(agriculture), len(fuel), 
        len(electronics), len(extraction)
    )

    summary = pad_section(summary, max_rows, len(summary[0]))
    arbitrage = pad_section(arbitrage, max_rows, len(arbitrage[0]))
    buy_vs_produce = pad_section(buy_vs_produce, max_rows, len(buy_vs_produce[0]))
    top_invest = pad_section(top_invest, max_rows, len(top_invest[0]))
    bottleneck = pad_section(bottleneck, max_rows, len(bottleneck[0]))
    top_traded = pad_section(top_traded, max_rows, len(top_traded[0]))
    metallurgy = pad_section(metallurgy, max_rows, len(metallurgy[0]))
    manufacturing = pad_section(manufacturing, max_rows, len(manufacturing[0]))
    construction = pad_section(construction, max_rows, len(construction[0]))
    chemistry = pad_section(chemistry, max_rows, len(chemistry[0]))
    food = pad_section(food, max_rows, len(food[0]))
    agriculture = pad_section(agriculture, max_rows, len(agriculture[0]))
    fuel = pad_section(fuel, max_rows, len(fuel[0]))
    electronics = pad_section(electronics, max_rows, len(electronics[0]))
    extraction = pad_section(extraction, max_rows, len(extraction[0]))

    # Debug: print section shapes
    print("Section shapes:")
    print("  summary:", len(summary[0]), "cols")
    print("  arbitrage:", len(arbitrage[0]), "cols")
    print("  buy_vs_produce:", len(buy_vs_produce[0]), "cols")
    print("  top_invest:", len(top_invest[0]), "cols")
    print("  bottleneck:", len(bottleneck[0]), "cols")
    print("  top_traded:", len(top_traded[0]), "cols")
    print("  metallurgy:", len(metallurgy[0]), "cols")
    print("  manufacturing:", len(manufacturing[0]), "cols")
    print("  construction:", len(construction[0]), "cols")
    print("  chemistry:", len(chemistry[0]), "cols")
    print("  food:", len(food[0]), "cols")
    print("  agriculture:", len(agriculture[0]), "cols")
    print("  fuel:", len(fuel[0]), "cols")
    print("  electronics:", len(electronics[0]), "cols")
    print("  extraction:", len(extraction[0]), "cols")

    summary_df = pd.DataFrame(summary)
    arbitrage_df = pd.DataFrame(arbitrage)
    buy_vs_produce_df = pd.DataFrame(buy_vs_produce)
    top_invest_df = pd.DataFrame(top_invest)
    bottleneck_df = pd.DataFrame(bottleneck)
    top_traded_df = pd.DataFrame(top_traded)
    metallurgy_df = pd.DataFrame(metallurgy)
    manufacturing_df = pd.DataFrame(manufacturing)
    construction_df = pd.DataFrame(construction)
    chemistry_df = pd.DataFrame(chemistry)
    food_df = pd.DataFrame(food)
    agriculture_df = pd.DataFrame(agriculture)
    fuel_df = pd.DataFrame(fuel)
    electronics_df = pd.DataFrame(electronics)
    extraction_df = pd.DataFrame(extraction)

    report_df = pd.concat(
        [summary_df, arbitrage_df, buy_vs_produce_df, top_invest_df, bottleneck_df, 
         top_traded_df, metallurgy_df, manufacturing_df, construction_df, chemistry_df, 
         food_df, agriculture_df, fuel_df, electronics_df, extraction_df],
        axis=1
    )
    print("Final report_df shape:", report_df.shape)
    print("First row of report_df:", report_df.iloc[0].tolist())
    return report_df

def apply_report_tab_formatting(sheets_manager, sheet_name, df):
    """
    Adapted for horizontal (side-by-side) sections:
    - Section headers colored in their respective column blocks
    - All text centered
    - All columns auto-resize
    """
    from googleapiclient.errors import HttpError

    sheet_id = sheets_manager._get_sheet_id(sheet_name)
    requests = []

    # 0. Clear all formatting
    requests.append({
        "updateCells": {
            "range": {"sheetId": sheet_id},
            "fields": "userEnteredFormat"
        }
    })

    # Section info: (header, color, width)
    section_defs = [
        ("SUMMARY", {"red": 0.2, "green": 0.4, "blue": 0.8}, 4),
        ("ARBITRAGE OPPORTUNITIES", {"red": 0.2, "green": 0.7, "blue": 0.2}, len(REPORT_COLUMNS)),
        ("BUY VS PRODUCE", {"red": 1.0, "green": 0.8, "blue": 0.2}, 9),  # Updated from 8 to 9 (added Recipe)
        ("TOP MATERIALS TO INVEST IN", {"red": 0.85, "green": 0.6, "blue": 0.15}, 8),  # Updated from 7 to 8 (added Recipe)
        ("CHOKEPOINTS/BOTTLENECKS", {"red": 0.8, "green": 0.2, "blue": 0.2}, 10),
        ("TOP TRADED PRODUCTS", {"red": 0.5, "green": 0.2, "blue": 0.7}, 2),
        ("METALLURGY", {"red": 0.6, "green": 0.6, "blue": 0.6}, 9),  # Updated from 8 to 9 (added Recipe)
        ("MANUFACTURING", {"red": 0.4, "green": 0.5, "blue": 0.7}, 9),  # Updated from 8 to 9
        ("CONSTRUCTION", {"red": 0.9, "green": 0.5, "blue": 0.2}, 9),  # Construction materials (orange/brown)
        ("CHEMISTRY", {"red": 0.3, "green": 0.8, "blue": 0.5}, 9),  # Updated from 8 to 9
        ("FOOD_INDUSTRIES", {"red": 0.9, "green": 0.7, "blue": 0.3}, 9),  # Updated from 8 to 9
        ("AGRICULTURE", {"red": 0.5, "green": 0.8, "blue": 0.3}, 9),  # Updated from 8 to 9
        ("FUEL_REFINING", {"red": 0.7, "green": 0.3, "blue": 0.2}, 9),  # Updated from 8 to 9
        ("ELECTRONICS", {"red": 0.2, "green": 0.4, "blue": 0.9}, 9),  # Updated from 8 to 9
        ("RESOURCE_EXTRACTION", {"red": 0.6, "green": 0.4, "blue": 0.2}, 9),  # Updated from 8 to 9
    ]

    # Find section start columns by scanning the first row for each header
    section_starts = []
    first_row = df.iloc[0].fillna("").astype(str).str.strip().str.upper().tolist()
    col = 0
    for header, color, width in section_defs:
        try:
            idx = first_row.index(header)
            section_starts.append((idx, color, width, header))
        except ValueError:
            continue

    # Color each section header block
    for idx, color, width, header in section_starts:
        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": 2,
                    "startColumnIndex": idx,
                    "endColumnIndex": idx + width
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": color,
                        "textFormat": {"bold": True, "fontSize": 12, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                        "horizontalAlignment": "CENTER"
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
            }
        })

    # --- SUBHEADER FORMATTING (row 3, index 2) ---
    def complementary_color(rgb):
        # Simple complementary: invert each channel
        return {k: 1.0 - v for k, v in rgb.items()}

    for idx, color, width, header in section_starts:
        comp_color = complementary_color(color)
        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 2,
                    "endRowIndex": 3,
                    "startColumnIndex": idx,
                    "endColumnIndex": idx + width
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": comp_color,
                        "textFormat": {"bold": True, "fontSize": 11, "foregroundColor": {"red": 0, "green": 0, "blue": 0}},
                        "horizontalAlignment": "CENTER"
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
            }
        })

    # Center all text
    requests.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": len(df) + 1,
                "startColumnIndex": 0,
                "endColumnIndex": len(df.columns)
            },
            "cell": {
                "userEnteredFormat": {
                    "horizontalAlignment": "CENTER"
                }
            },
            "fields": "userEnteredFormat(horizontalAlignment)"
        }
    })

    # Auto-resize all columns
    requests.append({
        "autoResizeDimensions": {
            "dimensions": {
                "sheetId": sheet_id,
                "dimension": "COLUMNS",
                "startIndex": 0,
                "endIndex": len(df.columns)
            }
        }
    })

    # Find "Recommendation" column for Buy vs Produce section
    rec_col = None
    subheader_row = None
    for idx, (col_idx, _, width, header) in enumerate(section_starts):
        if header == "BUY VS PRODUCE":
            # Subheader is the next row (row 2), columns col_idx to col_idx+width
            subheader_row = 1
            subheader = df.iloc[subheader_row, col_idx:col_idx+width]
            for i, col_name in enumerate(subheader):
                if str(col_name).strip().lower() == "recommendation":
                    rec_col = col_idx + i
            break

    # Find rows with recommendations to color
    rec_rows = []
    if rec_col is not None and subheader_row is not None:
        for idx in range(subheader_row + 1, len(df)):
            val = df.iloc[idx, rec_col]
            if val in ("Buy", "Produce", "Neutral", "Depends"):
                rec_rows.append((idx, val))

    rec_colors = {
        "Buy": {"red": 0.2, "green": 0.7, "blue": 0.2},
        "Produce": {"red": 0.9, "green": 0.4, "blue": 0.2},
        "Neutral": {"red": 1.0, "green": 0.9, "blue": 0.2},
        "Depends": {"red": 0.7, "green": 0.7, "blue": 0.7},
    }
    if rec_col is not None:
        for row_idx, rec in rec_rows:
            color = rec_colors.get(rec, {"red": 1, "green": 1, "blue": 1})
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": row_idx + 1,
                        "endRowIndex": row_idx + 2,
                        "startColumnIndex": rec_col,
                        "endColumnIndex": rec_col + 1
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": color,
                            "textFormat": {"bold": True, "fontSize": 11, "foregroundColor": {"red": 0, "green": 0, "blue": 0}},
                            "horizontalAlignment": "CENTER"
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
                }
            })
    else:
        print(f"  'Recommendation' column not found in Buy vs Produce section for {sheet_name}, skipping recommendation formatting.")

    # --- EXTRA FORMATTING ---

    # Helper: find column index by header in a section
    def find_col_idx(section_starts, header, subheader_name):
        for idx, (col_idx, _, width, section_header) in enumerate(section_starts):
            if section_header == header:
                subheader_row = 1
                subheader = df.iloc[subheader_row, col_idx:col_idx+width]
                for i, col_name in enumerate(subheader):
                    if str(col_name).strip().lower() == subheader_name.lower():
                        return col_idx + i
        return None

    # 1. Arbitrage: Opportunity Size (gradient red to green, higher better)
    opp_size_col = find_col_idx(section_starts, "ARBITRAGE OPPORTUNITIES", "Opportunity Size")
    if opp_size_col is not None:
        requests.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{
                        "sheetId": sheet_id,
                        "startRowIndex": 2,
                        "endRowIndex": len(df)+1,
                        "startColumnIndex": opp_size_col,
                        "endColumnIndex": opp_size_col+1
                    }],
                    "gradientRule": {
                        "minpoint": {"color": {"red": 1, "green": 0.2, "blue": 0.2}, "type": "NUMBER", "value": "0"},
                        "maxpoint": {"color": {"red": 0.2, "green": 0.8, "blue": 0.2}, "type": "NUMBER", "value": "10000"}
                    }
                },
                "index": 0
            }
        })

    # 2. Arbitrage: Opportunity Level (colors for 5 levels)
    opp_level_col = find_col_idx(section_starts, "ARBITRAGE OPPORTUNITIES", "Opportunity Level")
    if opp_level_col is not None:
        level_colors = {
            "Very High": {"red": 0.0, "green": 0.6, "blue": 0.0},
            "High": {"red": 0.2, "green": 0.8, "blue": 0.2},
            "Medium": {"red": 1.0, "green": 1.0, "blue": 0.2},
            "Low": {"red": 1.0, "green": 0.6, "blue": 0.0},
            "Very Low": {"red": 0.8, "green": 0.2, "blue": 0.2}
        }
        for val, color in level_colors.items():
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 2,
                            "endRowIndex": len(df)+1,
                            "startColumnIndex": opp_level_col,
                            "endColumnIndex": opp_level_col+1
                        }],
                        "booleanRule": {
                            "condition": {
                                "type": "TEXT_EQ",
                                "values": [{"userEnteredValue": val}]
                            },
                            "format": {"backgroundColor": color, "textFormat": {"bold": True}}
                        }
                    },
                    "index": 0
                }
            })

    # 3. Arbitrage: ROI (gradient red to green, 0 to 50+, 50+ stays green)
    roi_col = find_col_idx(section_starts, "ARBITRAGE OPPORTUNITIES", "ROI")
    if roi_col is not None:
        # Data starts at row 4 (index 3), so set startRowIndex=3
        requests.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{
                        "sheetId": sheet_id,
                        "startRowIndex": 3,  # Row 4 in Sheets (0-based)
                        "endRowIndex": len(df)+1,
                        "startColumnIndex": roi_col,
                        "endColumnIndex": roi_col+1
                    }],
                    "gradientRule": {
                        "minpoint": {
                            "color": {"red": 1, "green": 0.2, "blue": 0.2},
                            "type": "NUMBER",
                            "value": "0"
                        },
                        "midpoint": {
                            "color": {"red": 1, "green": 1, "blue": 0.4},
                            "type": "NUMBER",
                            "value": "25"
                        },
                        "maxpoint": {
                            "color": {"red": 0.2, "green": 1, "blue": 0.2},
                            "type": "NUMBER",
                            "value": "50"
                        }
                    }
                },
                "index": 0
            }
        })

    # 4. Buy vs Produce: Level (text color green/yellow/red)
    bvp_level_col = find_col_idx(section_starts, "BUY VS PRODUCE", "Level")
    if bvp_level_col is not None:
        for val, color in [("High", {"red": 0.2, "green": 0.8, "blue": 0.2}),
                           ("Medium", {"red": 1, "green": 1, "blue": 0.2}),
                           ("Low", {"red": 1, "green": 0.2, "blue": 0.2})]:
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 2,
                            "endRowIndex": len(df)+1,
                            "startColumnIndex": bvp_level_col,
                            "endColumnIndex": bvp_level_col+1
                        }],
                        "booleanRule": {
                            "condition": {
                                "type": "TEXT_EQ",
                                "values": [{"userEnteredValue": val}]
                            },
                            "format": {"textFormat": {"foregroundColor": color, "bold": True}}
                        }
                    },
                    "index": 0
                }
            })

    # 5. Top Materials: Investment Score (yellow to green gradient)
    invest_score_col = find_col_idx(section_starts, "TOP MATERIALS TO INVEST IN", "Investment Score")
    if invest_score_col is not None:
        requests.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{
                        "sheetId": sheet_id,
                        "startRowIndex": 2,
                        "endRowIndex": len(df)+1,
                        "startColumnIndex": invest_score_col,
                        "endColumnIndex": invest_score_col+1
                    }],
                    "gradientRule": {
                        "minpoint": {"color": {"red": 1, "green": 1, "blue": 0.2}, "type": "NUMBER", "value": "0"},
                        "maxpoint": {"color": {"red": 0.2, "green": 0.8, "blue": 0.2}, "type": "NUMBER", "value": "100"}
                    }
                },
                "index": 0
            }
        })

    # Chokepoints: Level (color code)
    bottleneck_level_col = find_col_idx(section_starts, "CHOKEPOINTS/BOTTLENECKS", "Level")
    if bottleneck_level_col is not None:
        for val, color in [("Critical", {"red": 1.0, "green": 0.0, "blue": 0.0}),
                           ("High", {"red": 0.8, "green": 0.2, "blue": 0.2}),
                           ("Medium", {"red": 1, "green": 1, "blue": 0.2}),
                           ("Low", {"red": 0.2, "green": 0.8, "blue": 0.2})]:
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 2,
                            "endRowIndex": len(df)+1,
                            "startColumnIndex": bottleneck_level_col,
                            "endColumnIndex": bottleneck_level_col+1
                        }],
                        "booleanRule": {
                            "condition": {
                                "type": "TEXT_EQ",
                                "values": [{"userEnteredValue": val}]
                            },
                            "format": {"backgroundColor": color, "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}}
                        }
                    },
                    "index": 0
                }
            })

    # Chokepoints: Chokepoint Type (distinct color for each type)
    bottleneck_type_col = find_col_idx(section_starts, "CHOKEPOINTS/BOTTLENECKS", "Chokepoint Type")
    if bottleneck_type_col is not None:
        type_colors = {
            "No Stock": {"red": 1.0, "green": 0.0, "blue": 0.0},  # Bright red for critical
            "No Buyers": {"red": 0.5, "green": 0.0, "blue": 0.5},  # Purple for critical
            "Low Supply & High Demand": {"red": 0.8, "green": 0.4, "blue": 0.0},
            "Low Supply": {"red": 0.2, "green": 0.6, "blue": 0.9},
            "High Demand": {"red": 0.9, "green": 0.8, "blue": 0.2},
            "": {"red": 1, "green": 1, "blue": 1}  # Default for empty
        }
        for val, color in type_colors.items():
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 2,
                            "endRowIndex": len(df)+1,
                            "startColumnIndex": bottleneck_type_col,
                            "endColumnIndex": bottleneck_type_col+1
                        }],
                        "booleanRule": {
                            "condition": {
                                "type": "TEXT_EQ",
                                "values": [{"userEnteredValue": val}]
                            },
                            "format": {"backgroundColor": color, "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}}
                        }
                    },
                    "index": 0
                }
            })

    # --- PROFESSION SECTIONS: Formatting for Profit and ROI ---
    profession_sections = [
        "METALLURGY", "MANUFACTURING", "CHEMISTRY", "FOOD_INDUSTRIES",
        "AGRICULTURE", "FUEL_REFINING", "ELECTRONICS", "RESOURCE_EXTRACTION"
    ]
    
    for prof_name in profession_sections:
        # Profit column (gradient red to green)
        profit_col = find_col_idx(section_starts, prof_name, "Profit")
        if profit_col is not None:
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 2,
                            "endRowIndex": len(df)+1,
                            "startColumnIndex": profit_col,
                            "endColumnIndex": profit_col+1
                        }],
                        "gradientRule": {
                            "minpoint": {"color": {"red": 1, "green": 0.2, "blue": 0.2}, "type": "NUMBER", "value": "0"},
                            "midpoint": {"color": {"red": 1, "green": 1, "blue": 0.4}, "type": "NUMBER", "value": "500"},
                            "maxpoint": {"color": {"red": 0.2, "green": 0.8, "blue": 0.2}, "type": "NUMBER", "value": "1000"}
                        }
                    },
                    "index": 0
                }
            })
        
        # ROI % column (gradient yellow to green)
        roi_col = find_col_idx(section_starts, prof_name, "ROI %")
        if roi_col is not None:
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 2,
                            "endRowIndex": len(df)+1,
                            "startColumnIndex": roi_col,
                            "endColumnIndex": roi_col+1
                        }],
                        "gradientRule": {
                            "minpoint": {"color": {"red": 1, "green": 0.8, "blue": 0.2}, "type": "NUMBER", "value": "0"},
                            "midpoint": {"color": {"red": 0.6, "green": 0.9, "blue": 0.3}, "type": "NUMBER", "value": "25"},
                            "maxpoint": {"color": {"red": 0.2, "green": 1, "blue": 0.2}, "type": "NUMBER", "value": "50"}
                        }
                    },
                    "index": 0
                }
            })
        
        # Investment Score column (gradient)
        inv_score_col = find_col_idx(section_starts, prof_name, "Investment Score")
        if inv_score_col is not None:
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 2,
                            "endRowIndex": len(df)+1,
                            "startColumnIndex": inv_score_col,
                            "endColumnIndex": inv_score_col+1
                        }],
                        "gradientRule": {
                            "minpoint": {"color": {"red": 1, "green": 1, "blue": 0.2}, "type": "NUMBER", "value": "0"},
                            "maxpoint": {"color": {"red": 0.2, "green": 0.8, "blue": 0.2}, "type": "NUMBER", "value": "100"}
                        }
                    },
                    "index": 0
                }
            })

    # --- ARBITRAGE SECTION: Visual Borders Between Sell Exchanges ---
    arb_section = next(((col_idx, width) for col_idx, _, width, header in section_starts if header == "ARBITRAGE OPPORTUNITIES"), None)
    if arb_section:
        arb_start_col, arb_width = arb_section
        # Find the rows for bottom border
        bottom_border_rows = find_arbitrage_bottom_border_rows(df, arb_start_col, arb_width)
        for row_idx in bottom_border_rows:
            requests.append({
                "updateBorders": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": row_idx + 1,  # +1 because Google Sheets is 0-based and header rows
                        "endRowIndex": row_idx + 2,
                        "startColumnIndex": arb_start_col,
                        "endColumnIndex": arb_start_col + arb_width
                    },
                    "bottom": {
                        "style": "SOLID_THICK",
                        "width": 2,
                        "color": {"red": 0, "green": 0, "blue": 0}
                    }
                }
            })

    # Send batchUpdate request
    if requests:
        try:
            sheets_manager.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=sheets_manager.spreadsheet_id,
                body={"requests": requests}
            ).execute()
            print(f" Formatting applied to {sheet_name}")
        except HttpError as e:
            print(f" Formatting failed for {sheet_name}: {e}")

def compute_arbitrage_opportunities(df, orders_df=None):
    """
    Compute arbitrage opportunities using full order book crossing.
    For each ticker, for each buy/sell exchange pair, simulate crossing asks and bids.
    Returns a DataFrame with weighted average buy/sell price, profit per unit, ROI, and opportunity size.
    """
    arbitrage_rows = []
    exchanges = df['Exchange'].unique()
    tickers = df['Ticker'].unique()

    for ticker in tickers:
        for buy_ex in exchanges:
            for sell_ex in exchanges:
                if buy_ex == sell_ex:
                    continue
                if orders_df is not None:
                    size, total_profit, matches = compute_arbitrage_opportunity_size(orders_df, ticker, buy_ex, sell_ex)
                    if size > 0 and matches:
                        # Weighted average buy/sell price for matched units
                        total_buy = sum(m[0] * m[2] for m in matches)
                        total_sell = sum(m[1] * m[2] for m in matches)
                        avg_buy = total_buy / size if size else 0
                        avg_sell = total_sell / size if size else 0
                        profit_per_unit = total_profit / size if size else 0
                        roi = (profit_per_unit / avg_buy * 100) if avg_buy > 0 else 0
                        # Get name/product from df
                        mat_rows = df[df['Ticker'] == ticker]
                        name = mat_rows.iloc[0].get('Material Name', ticker) if not mat_rows.empty else ticker
                        product = mat_rows.iloc[0].get('Product', '') if not mat_rows.empty else ''
                        arbitrage_rows.append([
                            ticker,
                            name,
                            product,
                            round(avg_buy, 2),
                            round(avg_sell, 2),
                            round(profit_per_unit, 2),
                            buy_ex,
                            sell_ex,
                            round(roi, 4),
                            int(size),
                            None  # Opportunity Level assigned later
                        ])
    columns = [
        "Ticker", "Name", "Product", "Buy Price", "Sell Price", "Profit",
        "Buy Exchange", "Sell Exchange", "ROI", "Opportunity Size", "Opportunity Level"
    ]
    return pd.DataFrame(arbitrage_rows, columns=columns)

def compute_arbitrage_opportunity_size(orders_df, ticker, buy_ex, sell_ex):
    """
    For a given ticker, buy_ex (where you buy), and sell_ex (where you sell),
    compute the maximum arbitrage size and total profit using the full order book.
    Returns (matched_qty, total_profit, matches) where matches is a list of (ask_price, bid_price, qty_matched).
    """
    # Get asks from buy_ex (where you buy)
    asks = orders_df[
        (orders_df['Ticker'] == ticker) &
        (orders_df['Exchange'] == buy_ex) &
        (orders_df['Side'] == 'ask')
    ].sort_values('Price', ascending=True).copy()
    # Get bids from sell_ex (where you sell)
    bids = orders_df[
        (orders_df['Ticker'] == ticker) &
        (orders_df['Exchange'] == sell_ex) &
        (orders_df['Side'] == 'bid')
    ].sort_values('Price', ascending=False).copy()
    ask_idx, bid_idx = 0, 0
    matched_qty = 0
    total_profit = 0
    matches = []
    while ask_idx < len(asks) and bid_idx < len(bids):
        ask_price = asks.iloc[ask_idx]['Price']
        ask_qty = asks.iloc[ask_idx]['Quantity']
        bid_price = bids.iloc[bid_idx]['Price']
        bid_qty = bids.iloc[bid_idx]['Quantity']
        if bid_price >= ask_price:
            qty = min(ask_qty, bid_qty)
            profit = (bid_price - ask_price) * qty
            matches.append((ask_price, bid_price, qty))
            matched_qty += qty
            total_profit += profit
            # Decrement quantities
            asks.at[asks.index[ask_idx], 'Quantity'] -= qty
            bids.at[bids.index[bid_idx], 'Quantity'] -= qty
            if asks.iloc[ask_idx]['Quantity'] <= 0:
                ask_idx += 1
            if bids.iloc[bid_idx]['Quantity'] <= 0:
                bid_idx += 1
        else:
            break
    return matched_qty, total_profit, matches

def load_and_prepare_orders():
    base_dir = Path(__file__).parent.parent / "cache"
    orders_path = base_dir / "orders.csv"
    bids_path = base_dir / "bids.csv"
    if not orders_path.exists():
        raise FileNotFoundError(f"orders.csv not found at {orders_path}")
    if not bids_path.exists():
        raise FileNotFoundError(f"bids.csv not found at {bids_path}")
    # Load asks (sell orders)
    asks = pd.read_csv(orders_path)
    asks = asks.rename(columns={
        'MaterialTicker': 'Ticker',
        'ExchangeCode': 'Exchange',
        'ItemCount': 'Quantity',
        'ItemCost': 'Price'
    })
    asks['Side'] = 'ask'
    asks = asks[['Ticker', 'Exchange', 'Side', 'Price', 'Quantity']]

    # Load bids (buy orders)
    bids = pd.read_csv(bids_path)
    bids = bids.rename(columns={
        'MaterialTicker': 'Ticker',
        'ExchangeCode': 'Exchange',
        'ItemCount': 'Quantity',
        'ItemCost': 'Price'
    })
    bids['Side'] = 'bid'
    bids = bids[['Ticker', 'Exchange', 'Side', 'Price', 'Quantity']]

    # Combine
    orders_df = pd.concat([asks, bids], ignore_index=True)
    # Ensure numeric
    orders_df['Price'] = pd.to_numeric(orders_df['Price'], errors='coerce')
    orders_df['Quantity'] = pd.to_numeric(orders_df['Quantity'], errors='coerce')
    return orders_df

def fetch_financial_data(sheets_manager, external_spreadsheet_id):
    """
    Fetch economic, financial, and monetary/currency data from external spreadsheet.
    
    Args:
        sheets_manager: SheetsManager instance
        external_spreadsheet_id: ID of the external financial data spreadsheet
    
    Returns:
        dict: Dictionary containing all financial data sheets
    """
    print("[STEP] Fetching financial data from external spreadsheet...", flush=True)
    
    financial_data = {}
    
    try:
        # Get all sheets from the external spreadsheet
        spreadsheet = sheets_manager.sheets_service.spreadsheets().get(
            spreadsheetId=external_spreadsheet_id
        ).execute()
        
        sheets_list = spreadsheet.get('sheets', [])
        
        # Fetch data from each sheet
        for sheet in sheets_list:
            sheet_name = sheet['properties']['title']
            
            # Skip chart sheets and other non-data sheets
            sheet_type = sheet['properties'].get('sheetType', 'GRID')
            if sheet_type != 'GRID':
                print(f"[INFO] Skipping non-data sheet: {sheet_name} (type: {sheet_type})", flush=True)
                continue
            
            print(f"[INFO] Fetching data from sheet: {sheet_name}", flush=True)
            
            try:
                # Read data from the sheet
                result = sheets_manager.sheets_service.spreadsheets().values().get(
                    spreadsheetId=external_spreadsheet_id,
                    range=f"'{sheet_name}'!A:Z"  # Read all columns
                ).execute()
                
                values = result.get('values', [])
                
                if values:
                    # Convert to DataFrame
                    df = pd.DataFrame(values[1:], columns=values[0]) if len(values) > 1 else pd.DataFrame()
                    financial_data[sheet_name] = df
                    print(f"[INFO] Loaded {len(df)} rows from {sheet_name}", flush=True)
                else:
                    print(f"[WARN] No data found in {sheet_name}", flush=True)
            except Exception as e:
                # Handle individual sheet errors gracefully
                if "Unable to parse range" in str(e):
                    print(f"[INFO] Skipping unparseable sheet: {sheet_name}", flush=True)
                else:
                    print(f"[WARN] Could not fetch sheet {sheet_name}: {e}", flush=True)
                continue
        
        # Save financial data to cache for offline access
        cache_financial_data(financial_data)
        
        return financial_data
    
    except Exception as e:
        print(f"[ERROR] Failed to fetch financial data: {e}", flush=True)
        # Try to load from cache
        return load_cached_financial_data()

def cache_financial_data(financial_data):
    """
    Save financial data to cache directory as CSV files.
    """
    financial_cache_dir = CACHE_DIR / "financial_data"
    financial_cache_dir.mkdir(exist_ok=True)
    
    for sheet_name, df in financial_data.items():
        if not df.empty:
            safe_name = sheet_name.replace('/', '_').replace('\\', '_')
            cache_path = financial_cache_dir / f"{safe_name}.csv"
            df.to_csv(cache_path, index=False)
            print(f"[INFO] Cached {sheet_name} to {cache_path}", flush=True)

def load_cached_financial_data():
    """
    Load financial data from cache.
    """
    financial_cache_dir = CACHE_DIR / "financial_data"
    financial_data = {}
    
    if financial_cache_dir.exists():
        for csv_file in financial_cache_dir.glob("*.csv"):
            sheet_name = csv_file.stem
            df = pd.read_csv(csv_file)
            financial_data[sheet_name] = df
            print(f"[INFO] Loaded {sheet_name} from cache", flush=True)
    
    return financial_data

def calculate_inflation_metrics(all_df, historical_data_path=None):
    """
    Calculate inflation-like metrics based on price changes over time.
    
    Args:
        all_df: current market data
        historical_data_path: path to historical price data (optional)
    
    Returns:
        dict: inflation metrics by category and overall
    """
    inflation_metrics = {}
    
    # If we have historical data, calculate period-over-period changes
    if historical_data_path and Path(historical_data_path).exists():
        try:
            historical_df = pd.read_csv(historical_data_path)
            # Calculate price index changes for major commodity categories
            # This would need timestamp data in the historical file
            pass
        except Exception as e:
            print(f"[WARN] Could not load historical data for inflation calc: {e}")
    
    # Calculate current price volatility as inflation proxy
    if 'Category' in all_df.columns and 'Ask_Price' in all_df.columns:
        for category in all_df['Category'].unique():
            cat_data = all_df[all_df['Category'] == category]
            if len(cat_data) > 0:
                avg_price = cat_data['Ask_Price'].mean()
                std_price = cat_data['Ask_Price'].std()
                volatility = (std_price / avg_price * 100) if avg_price > 0 else 0
                inflation_metrics[category] = {
                    'avg_price': avg_price,
                    'volatility': volatility,
                    'sample_size': len(cat_data)
                }
    
    return inflation_metrics

def get_material_to_profession_map():
    """
    Build a map of material ticker to profession(s) based on building expertise.
    
    For materials that can be produced by multiple professions (e.g., tier 0 resources
    like oxygen that can be extracted OR produced by TNP), this returns a dict where
    each material maps to a list of professions.
    """
    material_to_professions = {}
    
    try:
        buildings_path = CACHE_DIR / "buildings.csv"
        recipe_outputs_path = CACHE_DIR / "recipe_outputs.csv"
        buildingrecipes_path = CACHE_DIR / "buildingrecipes.csv"
        
        if not all([buildings_path.exists(), recipe_outputs_path.exists(), buildingrecipes_path.exists()]):
            return material_to_professions
        
        buildings = pd.read_csv(buildings_path)
        recipe_outputs = pd.read_csv(recipe_outputs_path)
        buildingrecipes = pd.read_csv(buildingrecipes_path)
        
        # Map building to expertise
        building_expertise = buildings.set_index('Ticker')['Expertise'].to_dict()
        
        # Map recipe key to building
        recipe_to_building = buildingrecipes.set_index('Key')['Building'].to_dict()
        
        # Map materials to professions based on what building produces them
        # A material can have multiple professions (e.g., O can be extracted or produced by TNP)
        for recipe_key, material in recipe_outputs[['Key', 'Material']].values:
            building = recipe_to_building.get(recipe_key)
            if building:
                expertise = building_expertise.get(building, '')
                if expertise:
                    if material not in material_to_professions:
                        material_to_professions[material] = []
                    if expertise not in material_to_professions[material]:
                        material_to_professions[material].append(expertise)
        
    except Exception as e:
        print(f"[WARN] Error building material-profession map: {e}")
    
    return material_to_professions

def calculate_gdp_metrics(all_df, professions):
    """
    Calculate GDP-like metrics (Gross Domestic Product proxy) based on production value.
    
    In PrUn context:
    - GDP = Sum of (Production Volume × Market Price) across all materials
    - Per-profession GDP shows sector contributions
    
    Args:
        all_df: market data with profit/production info
        professions: list of profession names
    
    Returns:
        dict: GDP metrics overall, per exchange, per profession, per product, per faction
    """
    gdp_metrics = {
        'total_market_value': 0,
        'by_profession': {},
        'by_exchange': {},
        'by_product': {},
        'by_faction': {}
    }
    
    # Build material to profession mapping (materials can have multiple professions)
    material_to_professions = get_material_to_profession_map()
    
    # Add tier 0 resources to RESOURCE_EXTRACTION if they don't have other production methods
    # If they do have production methods (like O via TNP), they'll appear in both professions
    if 'Tier' in all_df.columns:
        tier_0_materials = all_df[all_df['Tier'] == 0.0]['Ticker'].unique()
        for material in tier_0_materials:
            if material not in material_to_professions:
                material_to_professions[material] = ['RESOURCE_EXTRACTION']
            elif 'RESOURCE_EXTRACTION' not in material_to_professions[material]:
                # Add RESOURCE_EXTRACTION as an additional way to obtain this material
                material_to_professions[material].append('RESOURCE_EXTRACTION')
    
    # Calculate total market value (proxy for GDP)
    if 'Ask_Price' in all_df.columns:
        # Total market capitalization of all tracked materials
        gdp_metrics['total_market_value'] = all_df['Ask_Price'].sum()
        
        # Per exchange
        if 'Exchange' in all_df.columns:
            for exch in all_df['Exchange'].unique():
                exch_data = all_df[all_df['Exchange'] == exch]
                gdp_metrics['by_exchange'][exch] = exch_data['Ask_Price'].sum()
        
        # Per product (ticker)
        if 'Ticker' in all_df.columns:
            product_gdp = all_df.groupby('Ticker')['Ask_Price'].sum().to_dict()
            gdp_metrics['by_product'] = product_gdp
        
        # Per faction (based on exchange)
        faction_map = {
            'AI1': 'AIC (Antares)',
            'CI1': 'CIS (Castillo)',
            'CI2': 'CIS (Castillo)',
            'IC1': 'ICA (Insitor)',
            'NC1': 'NCC (Neo Brasilia)',
            'NC2': 'NCC (Neo Brasilia)'
        }
        
        if 'Exchange' in all_df.columns:
            for exch, faction in faction_map.items():
                exch_data = all_df[all_df['Exchange'] == exch]
                if not exch_data.empty:
                    faction_value = exch_data['Ask_Price'].sum()
                    if faction in gdp_metrics['by_faction']:
                        gdp_metrics['by_faction'][faction] += faction_value
                    else:
                        gdp_metrics['by_faction'][faction] = faction_value
        
        # Per profession - materials can belong to multiple professions
        # For GDP calculation, we split the value proportionally
        if 'Ticker' in all_df.columns:
            for profession in professions:
                profession_gdp = 0
                for ticker in all_df['Ticker'].unique():
                    mat_professions = material_to_professions.get(ticker, [])
                    # If this material can be produced by this profession
                    if profession in mat_professions:
                        ticker_data = all_df[all_df['Ticker'] == ticker]
                        ticker_value = ticker_data['Ask_Price'].sum()
                        # Split value equally among all professions that can produce it
                        profession_gdp += ticker_value / len(mat_professions)
                
                if profession_gdp > 0:
                    gdp_metrics['by_profession'][profession] = profession_gdp
    
    # Calculate profit generation (economic activity indicator)
    profit_col = 'Profit per Unit' if 'Profit per Unit' in all_df.columns else 'Profit_Ask'
    if profit_col in all_df.columns:
        gdp_metrics['total_profit_potential'] = all_df[profit_col].sum()
    
    return gdp_metrics

def calculate_ppp_metrics(all_df):
    """
    Calculate Purchasing Power Parity (PPP) metrics between exchanges.
    
    PPP measures relative cost of same goods across different markets.
    Lower PPP = higher purchasing power (goods are cheaper there)
    
    Args:
        all_df: market data with prices per exchange
    
    Returns:
        dict: PPP indices with base exchange normalized to 1.0
    """
    ppp_metrics = {}
    
    if 'Exchange' not in all_df.columns or 'Ticker' not in all_df.columns:
        return ppp_metrics
    
    # Use AI1 as base exchange (index = 1.0)
    base_exchange = 'AI1'
    
    # Calculate average price per ticker across all exchanges
    avg_prices = all_df.groupby('Ticker')['Ask_Price'].mean().to_dict()
    
    # For each exchange, calculate average price relative to base
    for exch in EXCHANGES:
        exch_data = all_df[all_df['Exchange'] == exch]
        if exch_data.empty:
            continue
        
        # Calculate exchange's average price for common goods
        exch_avg = exch_data['Ask_Price'].mean()
        
        # Get base exchange average for same tickers
        common_tickers = exch_data['Ticker'].unique()
        base_data = all_df[(all_df['Exchange'] == base_exchange) & (all_df['Ticker'].isin(common_tickers))]
        base_avg = base_data['Ask_Price'].mean() if not base_data.empty else exch_avg
        
        # PPP Index: ratio of exchange price to base price
        # >1.0 = more expensive (weaker purchasing power)
        # <1.0 = cheaper (stronger purchasing power)
        ppp_index = (exch_avg / base_avg) if base_avg > 0 else 1.0
        
        ppp_metrics[exch] = {
            'ppp_index': ppp_index,
            'avg_price': exch_avg,
            'relative_to_base': f"{((ppp_index - 1) * 100):+.2f}%"
        }
    
    return ppp_metrics

def calculate_exchange_competitiveness(all_df):
    """
    Calculate exchange competitiveness index based on:
    - Price competitiveness (lower prices = more competitive)
    - Profit opportunities (higher profits = more attractive)
    - Market depth (more materials = more liquid)
    
    Args:
        all_df: market data
    
    Returns:
        dict: competitiveness scores per exchange
    """
    competitiveness = {}
    
    profit_col = 'Profit per Unit' if 'Profit per Unit' in all_df.columns else 'Profit_Ask'
    
    for exch in EXCHANGES:
        exch_data = all_df[all_df['Exchange'] == exch]
        if exch_data.empty:
            continue
        
        # Metrics
        avg_profit = exch_data[profit_col].mean() if profit_col in exch_data.columns else 0
        median_profit = exch_data[profit_col].median() if profit_col in exch_data.columns else 0
        material_count = len(exch_data['Ticker'].unique()) if 'Ticker' in exch_data.columns else 0
        avg_price = exch_data['Ask_Price'].mean() if 'Ask_Price' in exch_data.columns else 0
        
        # Competitiveness score (normalized)
        # Higher profit + more materials + lower prices = more competitive
        competitiveness[exch] = {
            'avg_profit': avg_profit,
            'median_profit': median_profit,
            'material_diversity': material_count,
            'avg_price': avg_price,
            'profit_per_material': avg_profit / material_count if material_count > 0 else 0
        }
    
    return competitiveness

def build_financial_overview(financial_data, all_df):
    """
    Create Financial Overview tab combining external financial data with calculated economic indicators.
    
    Args:
        financial_data: dict of DataFrames from external spreadsheet
        all_df: our enhanced analysis data
    
    Returns:
        DataFrame for the Financial Overview tab
    """
    print("[STEP] Building Financial Overview...", flush=True)
    
    all_rows = []
    
    # Add title
    all_rows.append(["FINANCIAL OVERVIEW"])
    all_rows.append(["Economic & Monetary Data"])
    all_rows.append([])
    
    # SECTION I: CALCULATED ECONOMIC INDICATORS
    all_rows.append(["═" * 50])
    all_rows.append(["SECTION I: ECONOMIC INDICATORS"])
    all_rows.append(["═" * 50])
    all_rows.append([])
    
    # 1A. GDP-LIKE METRICS - OVERVIEW
    all_rows.append(["GDP METRICS (Production Value)"])
    all_rows.append(["-" * 40])
    all_rows.append([])
    
    gdp = calculate_gdp_metrics(all_df, PROFESSION_ORDER)
    
    all_rows.append(["Metric", "Value (ICA)"])
    all_rows.append(["Total Universe GDP", gdp['total_market_value']])
    if 'total_profit_potential' in gdp:
        all_rows.append(["Total Profit Potential", gdp['total_profit_potential']])
    all_rows.append([])
    all_rows.append([])
    
    # 1B. GDP BY FACTION
    all_rows.append(["GDP BY FACTION"])
    all_rows.append(["-" * 40])
    all_rows.append([])
    
    all_rows.append(["Faction", "GDP", "% of Total GDP"])
    for faction, value in sorted(gdp['by_faction'].items(), key=lambda x: x[1], reverse=True):
        pct_economy = (value / gdp['total_market_value'] * 100) if gdp['total_market_value'] > 0 else 0
        all_rows.append([faction, value, pct_economy / 100])
    all_rows.append([])
    all_rows.append([])
    
    # 1C. GDP BY EXCHANGE
    all_rows.append(["GDP BY EXCHANGE"])
    all_rows.append(["-" * 40])
    all_rows.append([])
    
    all_rows.append(["Exchange", "GDP", "% of Total GDP"])
    faction_map = {
        'AI1': 'AIC (Antares)',
        'CI1': 'CIS (Castillo)',
        'CI2': 'CIS (Castillo)',
        'IC1': 'ICA (Insitor)',
        'NC1': 'NCC (Neo Brasilia)',
        'NC2': 'NCC (Neo Brasilia)'
    }
    
    for exch, value in sorted(gdp['by_exchange'].items(), key=lambda x: x[1], reverse=True):
        pct_economy = (value / gdp['total_market_value'] * 100) if gdp['total_market_value'] > 0 else 0
        all_rows.append([exch, value, pct_economy / 100])
    all_rows.append([])
    all_rows.append([])
    
    # 1D. GDP BY PROFESSION/SECTOR WITH FACTION BREAKDOWN
    all_rows.append(["GDP BY PROFESSION/SECTOR"])
    all_rows.append(["-" * 40])
    all_rows.append([])
    
    # Calculate profession GDP by faction
    profession_by_faction = {}
    material_to_professions = get_material_to_profession_map()
    
    for faction in ['AIC (Antares)', 'CIS (Castillo)', 'ICA (Insitor)', 'NCC (Neo Brasilia)']:
        profession_by_faction[faction] = {}
        faction_exch = [exch for exch, f in faction_map.items() if f == faction]
        
        for exch in faction_exch:
            exch_data = all_df[all_df['Exchange'] == exch] if 'Exchange' in all_df.columns else pd.DataFrame()
            
            for _, row in exch_data.iterrows():
                ticker = row.get('Ticker', '')
                value = row.get('Ask_Price', 0)
                
                mat_professions = material_to_professions.get(ticker, ['UNKNOWN'])
                for profession in mat_professions:
                    profession_value = value / len(mat_professions)
                    if profession in profession_by_faction[faction]:
                        profession_by_faction[faction][profession] += profession_value
                    else:
                        profession_by_faction[faction][profession] = profession_value
    
    all_rows.append(["Profession/Sector", "Total GDP", 
                     "AIC GDP", "AIC % of GDP", "CIS GDP", "CIS % of GDP", 
                     "ICA GDP", "ICA % of GDP", "NCC GDP", "NCC % of GDP"])
    
    # Calculate total GDP for each faction
    aic_total_gdp = gdp['by_faction'].get('AIC (Antares)', 0)
    cis_total_gdp = gdp['by_faction'].get('CIS (Castillo)', 0)
    ica_total_gdp = gdp['by_faction'].get('ICA (Insitor)', 0)
    ncc_total_gdp = gdp['by_faction'].get('NCC (Neo Brasilia)', 0)
    
    for profession, value in sorted(gdp['by_profession'].items(), key=lambda x: x[1], reverse=True):
        aic_val = profession_by_faction.get('AIC (Antares)', {}).get(profession, 0)
        aic_pct_of_faction = (aic_val / aic_total_gdp * 100) if aic_total_gdp > 0 else 0
        
        cis_val = profession_by_faction.get('CIS (Castillo)', {}).get(profession, 0)
        cis_pct_of_faction = (cis_val / cis_total_gdp * 100) if cis_total_gdp > 0 else 0
        
        ica_val = profession_by_faction.get('ICA (Insitor)', {}).get(profession, 0)
        ica_pct_of_faction = (ica_val / ica_total_gdp * 100) if ica_total_gdp > 0 else 0
        
        ncc_val = profession_by_faction.get('NCC (Neo Brasilia)', {}).get(profession, 0)
        ncc_pct_of_faction = (ncc_val / ncc_total_gdp * 100) if ncc_total_gdp > 0 else 0
        
        all_rows.append([profession, value,
                        aic_val, aic_pct_of_faction / 100,
                        cis_val, cis_pct_of_faction / 100,
                        ica_val, ica_pct_of_faction / 100,
                        ncc_val, ncc_pct_of_faction / 100])
    all_rows.append([])
    all_rows.append([])
    
    # 1E. TOP 50 PRODUCTS BY GDP - HORIZONTAL LAYOUT (UNIVERSE + ALL FACTIONS)
    all_rows.append(["TOP 50 PRODUCTS BY GDP"])
    all_rows.append(["Universe & Faction Breakdown"])
    all_rows.append(["-" * 80])
    all_rows.append([])
    
    # Calculate products by faction
    faction_products = {}
    
    if 'Exchange' in all_df.columns and 'Ticker' in all_df.columns and 'Ask_Price' in all_df.columns:
        for exch, faction in faction_map.items():
            exch_data = all_df[all_df['Exchange'] == exch]
            if not exch_data.empty:
                product_values = exch_data.groupby('Ticker')['Ask_Price'].sum().to_dict()
                
                if faction not in faction_products:
                    faction_products[faction] = {}
                
                for ticker, value in product_values.items():
                    if ticker in faction_products[faction]:
                        faction_products[faction][ticker] += value
                    else:
                        faction_products[faction][ticker] = value
    
    # Get top 50 for universe and each faction
    sorted_products = sorted(gdp['by_product'].items(), key=lambda x: x[1], reverse=True)[:50]
    
    faction_order = ['AIC (Antares)', 'CIS (Castillo)', 'ICA (Insitor)', 'NCC (Neo Brasilia)']
    faction_top_products = {}
    for faction in faction_order:
        if faction in faction_products:
            faction_top_products[faction] = sorted(faction_products[faction].items(), key=lambda x: x[1], reverse=True)[:50]
        else:
            faction_top_products[faction] = []
    
    # Create header row
    header = ["Rank", "Universe", "Universe GDP", "Universe % GDP",
              "AIC", "AIC GDP", "AIC % GDP",
              "CIS", "CIS GDP", "CIS % GDP",
              "ICA", "ICA GDP", "ICA % GDP",
              "NCC", "NCC GDP", "NCC % GDP"]
    all_rows.append(header)
    
    # Create data rows (50 rows for top 50)
    for rank in range(1, 51):
        row = [f"{rank}"]
        
        # Universe product
        if rank - 1 < len(sorted_products):
            ticker, value = sorted_products[rank - 1]
            pct_economy = (value / gdp['total_market_value'] * 100) if gdp['total_market_value'] > 0 else 0
            row.extend([ticker, f"{value:,.0f}", f"{pct_economy:.2f}%"])
        else:
            row.extend(["", "", ""])
        
        # Each faction's product
        for faction in faction_order:
            faction_gdp = gdp['by_faction'].get(faction, 1)
            faction_list = faction_top_products.get(faction, [])
            
            if rank - 1 < len(faction_list):
                ticker, value = faction_list[rank - 1]
                pct_of_total_gdp = (value / gdp['total_market_value'] * 100) if gdp['total_market_value'] > 0 else 0
                row.extend([ticker, f"{value:,.0f}", f"{pct_of_total_gdp:.2f}%"])
            else:
                row.extend(["", "", ""])
        
        all_rows.append(row)
    
    all_rows.append([])
    all_rows.append([])
    
    # 2. PURCHASING POWER PARITY (PPP)
    all_rows.append(["PURCHASING POWER PARITY BY EXCHANGE"])
    all_rows.append(["Base: AI1 = 1.00"])
    all_rows.append(["-" * 50])
    all_rows.append([])
    
    ppp = calculate_ppp_metrics(all_df)
    
    all_rows.append(["Exchange", "PPP Index", "Avg Price (ICA)", "vs AI1", "Interpretation"])
    for exch in EXCHANGES:
        if exch in ppp:
            idx = ppp[exch]['ppp_index']
            interpretation = "EXPENSIVE (weak)" if idx > 1.05 else "CHEAP (strong)" if idx < 0.95 else "NEUTRAL"
            all_rows.append([
                exch,
                f"{idx:.4f}",
                f"{ppp[exch]['avg_price']:,.2f}",
                ppp[exch]['relative_to_base'],
                interpretation
            ])
    all_rows.append([])
    all_rows.append(["Note: PPP > 1.0 means goods cost more than AI1 (weaker purchasing power)"])
    all_rows.append(["      PPP < 1.0 means goods cost less than AI1 (stronger purchasing power)"])
    all_rows.append([])
    all_rows.append([])
    
    # 3. EXCHANGE COMPETITIVENESS INDEX
    all_rows.append(["EXCHANGE COMPETITIVENESS ANALYSIS"])
    all_rows.append(["-" * 50])
    all_rows.append([])
    
    comp = calculate_exchange_competitiveness(all_df)
    
    all_rows.append(["Exchange", "Avg Profit", "Median Profit", "Materials", "Avg Price", "Profit/Material"])
    for exch in EXCHANGES:
        if exch in comp:
            c = comp[exch]
            all_rows.append([
                exch,
                f"{c['avg_profit']:,.2f}",
                f"{c['median_profit']:,.2f}",
                f"{c['material_diversity']}",
                f"{c['avg_price']:,.2f}",
                f"{c['profit_per_material']:,.2f}"
            ])
    all_rows.append([])
    all_rows.append([])
    
    # 4. INFLATION PROXY (Price Volatility by Category)
    all_rows.append(["INFLATION PROXY - Price Volatility by Category"])
    all_rows.append(["-" * 50])
    all_rows.append([])
    
    inflation = calculate_inflation_metrics(all_df)
    
    all_rows.append(["Category", "Avg Price (ICA)", "Volatility %", "Sample Size"])
    for cat, metrics in sorted(inflation.items(), key=lambda x: x[1]['volatility'], reverse=True):
        all_rows.append([
            cat,
            metrics['avg_price'],
            metrics['volatility'] / 100,
            metrics['sample_size']
        ])
    all_rows.append([])
    all_rows.append(["Note: Higher volatility suggests more price instability (inflation-like pressure)"])
    all_rows.append([])
    all_rows.append([])
    
    # ═══════════════════════════════════════════════════════
    # SECTION II: CALCULATED MARKET STATISTICS
    # ═══════════════════════════════════════════════════════
    all_rows.append(["═══════════════════════════════════════════════════════"])
    all_rows.append(["═══ II. CALCULATED MARKET STATISTICS ═══"])
    all_rows.append(["═══════════════════════════════════════════════════════"])
    all_rows.append([])
    
    # Calculate overall market metrics
    market_stats = []
    market_stats.append(["Metric", "Value"])
    market_stats.append(["Total Materials Tracked", len(all_df['Ticker'].unique())])
    market_stats.append(["Total Data Points", len(all_df)])
    market_stats.append(["Total Exchanges", len(all_df['Exchange'].unique()) if 'Exchange' in all_df.columns else 0])
    
    profit_col = 'Profit per Unit' if 'Profit per Unit' in all_df.columns else 'Profit_Ask'
    if profit_col in all_df.columns:
        market_stats.append(["Average Market Profit", all_df[profit_col].mean()])
        market_stats.append(["Median Market Profit", all_df[profit_col].median()])
        market_stats.append(["Max Market Profit", all_df[profit_col].max()])
        market_stats.append(["Min Market Profit", all_df[profit_col].min()])
    
    roi_col = 'ROI Ask %' if 'ROI Ask %' in all_df.columns else 'ROI_Ask'
    if roi_col in all_df.columns:
        market_stats.append(["Average Market ROI", all_df[roi_col].mean() / 100])
        market_stats.append(["Median Market ROI", all_df[roi_col].median() / 100])
    
    all_rows.extend(market_stats)
    
    # Convert to DataFrame
    max_cols = max(len(row) for row in all_rows)
    padded_rows = [row + [""] * (max_cols - len(row)) for row in all_rows]
    
    return pd.DataFrame(padded_rows)

def apply_financial_overview_formatting(sheets_manager, sheet_name, df):
    """
    Apply comprehensive formatting to the Financial Overview tab with colors, borders, and number formatting.
    """
    from googleapiclient.errors import HttpError
    
    sheet_id = sheets_manager._get_sheet_id(sheet_name)
    requests = []
    
    # 0. Clear all formatting
    requests.append({
        "updateCells": {
            "range": {"sheetId": sheet_id},
            "fields": "userEnteredFormat"
        }
    })
    
    # 0.5. Unhide all columns (in case any were previously hidden)
    requests.append({
        "updateDimensionProperties": {
            "range": {
                "sheetId": sheet_id,
                "dimension": "COLUMNS",
                "startIndex": 0,
                "endIndex": len(df.columns)
            },
            "properties": {
                "hiddenByUser": False
            },
            "fields": "hiddenByUser"
        }
    })
    
    # 1. Center all text
    requests.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": len(df) + 1,
                "startColumnIndex": 0,
                "endColumnIndex": len(df.columns)
            },
            "cell": {
                "userEnteredFormat": {
                    "horizontalAlignment": "CENTER"
                }
            },
            "fields": "userEnteredFormat(horizontalAlignment)"
        }
    })
    
    # 2. Format section headers (rows starting with "===" or main sections)
    header_color = {"red": 0.2, "green": 0.4, "blue": 0.8}
    subheader_color = {"red": 0.85, "green": 0.85, "blue": 0.85}
    
    for row_idx in range(len(df)):
        first_cell = str(df.iloc[row_idx, 0]).strip()
        
        # Main section headers (===)
        if first_cell.startswith("===") or "FINANCIAL OVERVIEW" in first_cell or "SECTION" in first_cell:
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": row_idx + 1,
                        "endRowIndex": row_idx + 2,
                        "startColumnIndex": 0,
                        "endColumnIndex": len(df.columns)
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": header_color,
                            "textFormat": {"bold": True, "fontSize": 14, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                            "horizontalAlignment": "CENTER"
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
                }
            })
        
        # Subsection headers (GDP BY, Faction, Exchange, etc.)
        elif any(keyword in first_cell for keyword in ["GDP BY", "TOP 50", "Metric", "Faction", "Exchange", "Profession/Sector"]):
            # Check if this is a header row (contains column names)
            is_header = first_cell in ["Metric", "Faction", "Exchange", "Profession/Sector"]
            
            if is_header or first_cell.startswith("GDP BY") or first_cell.startswith("TOP 50"):
                requests.append({
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": row_idx + 1,
                            "endRowIndex": row_idx + 2,
                            "startColumnIndex": 0,
                            "endColumnIndex": len(df.columns)
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": subheader_color,
                                "textFormat": {"bold": True, "fontSize": 11},
                                "horizontalAlignment": "CENTER",
                                "borders": {
                                    "top": {"style": "SOLID", "width": 2},
                                    "bottom": {"style": "SOLID", "width": 2}
                                }
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,borders)"
                    }
                })
    
    # 3. Apply number formatting - scan for data sections and apply formatting by column
    gdp_sections = []
    
    # Find all data sections (GDP BY FACTION, GDP BY EXCHANGE, GDP BY PROFESSION)
    for row_idx in range(len(df)):
        first_cell = str(df.iloc[row_idx, 0]).strip()
        
        # GDP BY FACTION section
        if first_cell == "Faction":
            # Find end of this section
            end_row = row_idx + 1
            for i in range(row_idx + 1, len(df)):
                if pd.isna(df.iloc[i, 0]) or str(df.iloc[i, 0]).strip() == "":
                    end_row = i
                    break
            gdp_sections.append({
                'name': 'GDP BY FACTION',
                'header_row': row_idx,
                'start_row': row_idx + 1,
                'end_row': end_row,
                'columns': {
                    1: 'currency',  # GDP column
                    2: 'percent'    # % of Total GDP column
                }
            })
        
        # GDP BY EXCHANGE section
        elif first_cell == "Exchange":
            end_row = row_idx + 1
            for i in range(row_idx + 1, len(df)):
                if pd.isna(df.iloc[i, 0]) or str(df.iloc[i, 0]).strip() == "":
                    end_row = i
                    break
            gdp_sections.append({
                'name': 'GDP BY EXCHANGE',
                'header_row': row_idx,
                'start_row': row_idx + 1,
                'end_row': end_row,
                'columns': {
                    1: 'currency',  # GDP column
                    2: 'percent'    # % of Total GDP column
                }
            })
        
        # GDP BY PROFESSION/SECTOR section
        elif first_cell == "Profession/Sector":
            end_row = row_idx + 1
            for i in range(row_idx + 1, len(df)):
                if pd.isna(df.iloc[i, 0]) or str(df.iloc[i, 0]).strip() == "":
                    end_row = i
                    break
            gdp_sections.append({
                'name': 'GDP BY PROFESSION/SECTOR',
                'header_row': row_idx,
                'start_row': row_idx + 1,
                'end_row': end_row,
                'columns': {
                    1: 'currency',  # Total GDP
                    2: 'currency',  # AIC GDP
                    3: 'percent',   # AIC % of GDP
                    4: 'currency',  # CIS GDP
                    5: 'percent',   # CIS % of GDP
                    6: 'currency',  # ICA GDP
                    7: 'percent',   # ICA % of GDP
                    8: 'currency',  # NCC GDP
                    9: 'percent'    # NCC % of GDP
                }
            })
        
        # GDP METRICS section
        elif first_cell == "Metric":
            end_row = row_idx + 1
            for i in range(row_idx + 1, len(df)):
                if pd.isna(df.iloc[i, 0]) or str(df.iloc[i, 0]).strip() == "":
                    end_row = i
                    break
            gdp_sections.append({
                'name': 'GDP METRICS',
                'header_row': row_idx,
                'start_row': row_idx + 1,
                'end_row': end_row,
                'columns': {
                    1: 'currency'  # Value column
                }
            })
        
        # INFLATION PROXY section
        elif first_cell == "Category":
            # Check if this is the inflation section by looking at nearby rows
            if row_idx > 0 and "INFLATION" in str(df.iloc[row_idx - 2, 0]).upper():
                end_row = row_idx + 1
                for i in range(row_idx + 1, len(df)):
                    cell_val = str(df.iloc[i, 0]).strip()
                    if pd.isna(df.iloc[i, 0]) or cell_val == "" or cell_val.startswith("Note:"):
                        end_row = i
                        break
                gdp_sections.append({
                    'name': 'INFLATION PROXY',
                    'header_row': row_idx,
                    'start_row': row_idx + 1,
                    'end_row': end_row,
                    'columns': {
                        1: 'currency',  # Avg Price
                        2: 'percent',   # Volatility %
                        3: 'number'     # Sample Size
                    }
                })
        
        # MARKET STATISTICS section (look for second "Metric" header)
        elif first_cell == "Metric" and any("MARKET STATISTICS" in str(df.iloc[i, 0]).upper() for i in range(max(0, row_idx - 5), row_idx)):
            end_row = row_idx + 1
            for i in range(row_idx + 1, len(df)):
                if pd.isna(df.iloc[i, 0]) or str(df.iloc[i, 0]).strip() == "":
                    end_row = i
                    break
            # Determine format based on row content
            for i in range(row_idx + 1, end_row):
                metric_name = str(df.iloc[i, 0]).strip()
                if "ROI" in metric_name:
                    # Format as percentage
                    requests.append({
                        "repeatCell": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": i + 1,
                                "endRowIndex": i + 2,
                                "startColumnIndex": 1,
                                "endColumnIndex": 2
                            },
                            "cell": {
                                "userEnteredFormat": {
                                    "numberFormat": {
                                        "type": "PERCENT",
                                        "pattern": "0.00%"
                                    }
                                }
                            },
                            "fields": "userEnteredFormat(numberFormat)"
                        }
                    })
                elif "Profit" in metric_name:
                    # Format as currency
                    requests.append({
                        "repeatCell": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": i + 1,
                                "endRowIndex": i + 2,
                                "startColumnIndex": 1,
                                "endColumnIndex": 2
                            },
                            "cell": {
                                "userEnteredFormat": {
                                    "numberFormat": {
                                        "type": "CURRENCY",
                                        "pattern": "#,##0.00 [$ICA]"
                                    }
                                }
                            },
                            "fields": "userEnteredFormat(numberFormat)"
                        }
                    })
    
    # Apply formatting to each section
    for section in gdp_sections:
        for col_idx, format_type in section['columns'].items():
            if format_type == 'currency':
                # Apply currency format with thousands separator
                requests.append({
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": section['start_row'] + 1,
                            "endRowIndex": section['end_row'] + 1,
                            "startColumnIndex": col_idx,
                            "endColumnIndex": col_idx + 1
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "numberFormat": {
                                    "type": "CURRENCY",
                                    "pattern": "#,##0.00 [$ICA]"
                                }
                            }
                        },
                        "fields": "userEnteredFormat(numberFormat)"
                    }
                })
            elif format_type == 'percent':
                # Apply percentage format
                requests.append({
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": section['start_row'] + 1,
                            "endRowIndex": section['end_row'] + 1,
                            "startColumnIndex": col_idx,
                            "endColumnIndex": col_idx + 1
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "numberFormat": {
                                    "type": "PERCENT",
                                    "pattern": "0.00%"
                                }
                            }
                        },
                        "fields": "userEnteredFormat(numberFormat)"
                    }
                })
            elif format_type == 'number':
                # Apply number format (no decimals for counts)
                requests.append({
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": section['start_row'] + 1,
                            "endRowIndex": section['end_row'] + 1,
                            "startColumnIndex": col_idx,
                            "endColumnIndex": col_idx + 1
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "numberFormat": {
                                    "type": "NUMBER",
                                    "pattern": "#,##0"
                                }
                            }
                        },
                        "fields": "userEnteredFormat(numberFormat)"
                    }
                })
    
    # 4. Add alternating row colors for data sections
    data_row_color_1 = {"red": 0.95, "green": 0.95, "blue": 0.95}
    data_row_color_2 = {"red": 1, "green": 1, "blue": 1}
    
    in_data_section = False
    data_row_counter = 0
    
    for row_idx in range(len(df)):
        first_cell = str(df.iloc[row_idx, 0]).strip()
        
        # Start of data section (after header row)
        if first_cell in ["Faction", "Exchange", "Profession/Sector"]:
            in_data_section = True
            data_row_counter = 0
            continue
        
        # End of data section (empty row)
        if in_data_section and (not first_cell or first_cell == ""):
            in_data_section = False
            continue
        
        # Apply alternating colors to data rows
        if in_data_section:
            color = data_row_color_1 if data_row_counter % 2 == 0 else data_row_color_2
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": row_idx + 1,
                        "endRowIndex": row_idx + 2,
                        "startColumnIndex": 0,
                        "endColumnIndex": len(df.columns)
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": color
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor)"
                }
            })
            data_row_counter += 1
    
    # 5. Auto-resize all columns
    requests.append({
        "autoResizeDimensions": {
            "dimensions": {
                "sheetId": sheet_id,
                "dimension": "COLUMNS",
                "startIndex": 0,
                "endIndex": len(df.columns)
            }
        }
    })
    
    # 6. Freeze first row
    requests.append({
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id,
                "gridProperties": {
                    "frozenRowCount": 1
                }
            },
            "fields": "gridProperties.frozenRowCount"
        }
    })
    
    # Send batchUpdate request
    if requests:
        try:
            sheets_manager.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=sheets_manager.spreadsheet_id,
                body={"requests": requests}
            ).execute()
            print(f"[SUCCESS] Enhanced formatting applied to {sheet_name}")
        except HttpError as e:
            print(f"✗ Formatting failed for {sheet_name}: {e}")

def add_financial_overview_charts(sheets_manager, sheet_name, df):
    """
    Add pie charts to Financial Overview for GDP breakdowns.
    Charts are positioned to the right of their respective data tables.
    Creates 9 charts: 5 main analysis + 4 faction-specific product charts.
    """
    print(f"[STEP] Adding pie charts to {sheet_name}...", flush=True)
    
    try:
        # First, delete all existing charts to avoid duplicates
        sheets_manager.delete_all_charts(sheet_name)
        
        # Find data sections by scanning the dataframe
        chart_configs = []
        
        # 1. GDP by Faction
        for row_idx in range(len(df)):
            if "GDP BY FACTION" in str(df.iloc[row_idx, 0]).upper():
                header_row = None
                for i in range(row_idx, min(row_idx + 10, len(df))):
                    if str(df.iloc[i, 0]).strip() == "Faction":
                        header_row = i
                        break
                
                if header_row is not None:
                    data_start = header_row + 1  # Skip header
                    data_end = data_start
                    for i in range(data_start, len(df)):
                        if pd.isna(df.iloc[i, 0]) or str(df.iloc[i, 0]).strip() == "":
                            data_end = i
                            break
                        data_end = i + 1
                    
                    if data_end > data_start:
                        chart_configs.append({
                            'title': 'GDP by Faction',
                            'data_range': {
                                'startRowIndex': data_start + 1,
                                'endRowIndex': data_end + 1,
                                'startColumnIndex': 0,  # Faction names (column A)
                                'endColumnIndex': 2     # GDP (ICA) only (column B)
                            },
                            'position': {
                                'rowIndex': header_row + 1,  # Position at header row
                                'columnIndex': 6,  # Column G
                                'offsetYPixels': -20  # Slight offset up
                            }
                        })
                break
        
        # 2. GDP by Exchange
        for row_idx in range(len(df)):
            if "GDP BY EXCHANGE" in str(df.iloc[row_idx, 0]).upper():
                header_row = None
                for i in range(row_idx, min(row_idx + 10, len(df))):
                    if str(df.iloc[i, 0]).strip() == "Exchange":
                        header_row = i
                        break
                
                if header_row is not None:
                    data_start = header_row + 1  # Skip header
                    data_end = data_start
                    for i in range(data_start, len(df)):
                        if pd.isna(df.iloc[i, 0]) or str(df.iloc[i, 0]).strip() == "":
                            data_end = i
                            break
                        data_end = i + 1
                    
                    if data_end > data_start:
                        chart_configs.append({
                            'title': 'GDP by Exchange',
                            'data_range': {
                                'startRowIndex': data_start + 1,
                                'endRowIndex': data_end + 1,
                                'startColumnIndex': 0,  # Exchange names
                                'endColumnIndex': 2     # GDP (ICA) only (column B)
                            },
                            'position': {
                                'rowIndex': header_row + 1,  # Position at header row
                                'columnIndex': 6,  # Column G
                                'offsetYPixels': -20  # Slight offset up
                            }
                        })
                break
        
        # 3. GDP by Profession/Sector
        for row_idx in range(len(df)):
            if "GDP BY PROFESSION" in str(df.iloc[row_idx, 0]).upper():
                header_row = None
                for i in range(row_idx, min(row_idx + 10, len(df))):
                    if str(df.iloc[i, 0]).strip() == "Profession/Sector":
                        header_row = i
                        break
                
                if header_row is not None:
                    data_start = header_row + 1  # Skip header
                    data_end = data_start
                    for i in range(data_start, len(df)):
                        if pd.isna(df.iloc[i, 0]) or str(df.iloc[i, 0]).strip() == "":
                            data_end = i
                            break
                        data_end = i + 1
                    
                    if data_end > data_start:
                        chart_configs.append({
                            'title': 'GDP by Profession/Sector',
                            'data_range': {
                                'startRowIndex': data_start + 1,
                                'endRowIndex': data_end + 1,
                                'startColumnIndex': 0,  # Profession names
                                'endColumnIndex': 2     # GDP (ICA) only (column B)
                            },
                            'position': {
                                'rowIndex': header_row + 1,  # Position at header row
                                'columnIndex': 6,  # Column G
                                'offsetYPixels': -20  # Slight offset up
                            }
                        })
                break
        
        # 4. Top Products Universe (show only top 10 in chart for clarity)
        for row_idx in range(len(df)):
            if "TOP 50 PRODUCTS BY GDP" in str(df.iloc[row_idx, 0]).upper() and "UNIVERSE" in str(df.iloc[row_idx, 0]).upper():
                header_row = None
                for i in range(row_idx, min(row_idx + 10, len(df))):
                    if str(df.iloc[i, 0]).strip() == "Rank":
                        header_row = i
                        break
                
                if header_row is not None:
                    data_start = header_row + 1  # Skip header
                    # Only use top 10 for the chart
                    data_end = min(data_start + 10, len(df))
                    
                    chart_configs.append({
                        'title': 'Top 10 Products Universe',
                        'data_range': {
                            'startRowIndex': data_start + 1,
                            'endRowIndex': data_end + 1,
                            'startColumnIndex': 1,  # Ticker names (skip Rank column)
                            'endColumnIndex': 3     # GDP (ICA) only (column C)
                        },
                        'position': {
                            'rowIndex': header_row + 1,  # Position at header row
                            'columnIndex': 6,  # Column G
                            'offsetYPixels': -20  # Slight offset up
                        }
                    })
                break
        
        # 5-8. Top Products by Faction (one chart per faction)
        factions = ['AIC (Antares)', 'CIS (Castillo)', 'ICA (Insitor)', 'NCC (Neo Brasilia)']
        for faction in factions:
            for row_idx in range(len(df)):
                row_str = str(df.iloc[row_idx, 0]).upper()
                if f"TOP 50 PRODUCTS - {faction.upper()}" in row_str:
                    header_row = None
                    for i in range(row_idx, min(row_idx + 10, len(df))):
                        if str(df.iloc[i, 0]).strip() == "Rank":
                            header_row = i
                            break
                    
                    if header_row is not None:
                        data_start = header_row + 1  # Skip header
                        # Only use top 10 for the chart
                        data_end = min(data_start + 10, len(df))
                        
                        chart_configs.append({
                            'title': f'Top 10 Products - {faction}',
                            'data_range': {
                                'startRowIndex': data_start + 1,
                                'endRowIndex': data_end + 1,
                                'startColumnIndex': 1,  # Ticker names (skip Rank column)
                                'endColumnIndex': 3     # GDP (ICA) only (column C)
                            },
                            'position': {
                                'rowIndex': header_row + 1,  # Position at header row
                                'columnIndex': 6,  # Column G
                                'offsetYPixels': -20  # Slight offset up
                            }
                        })
                    break
        
        # Create all charts
        for config in chart_configs:
            success = sheets_manager.add_pie_chart(
                sheet_name=sheet_name,
                title=config['title'],
                data_range=config['data_range'],
                position=config['position']
            )
            if success:
                print(f"  [SUCCESS] Added chart: {config['title']}")
            else:
                print(f"  ✗ Failed to add chart: {config['title']}")
        
        print(f"[SUCCESS] Added {len(chart_configs)} charts to {sheet_name}")
        
    except Exception as e:
        print(f"[ERROR] Failed to add charts: {e}")
        import traceback
        traceback.print_exc()

def create_price_analyser_tab(sheets_manager, all_df):
    """
    Create an interactive Price Analyser tab with dropdowns for material and exchange selection.
    Shows detailed cost breakdown, pricing, ROI, and breakeven analysis.
    """
    from googleapiclient.errors import HttpError
    
    print("[INFO] Building Price Analyser tab...")
    
    # Filter out rows with missing Ticker or Exchange (empty rows, section breaks, etc.)
    clean_df = all_df.dropna(subset=['Ticker', 'Exchange']).copy()
    print(f"[INFO] Filtered data: {len(all_df)} -> {len(clean_df)} rows (removed {len(all_df) - len(clean_df)} rows with missing Ticker/Exchange)")
    
    # Add workforce cost columns if not present
    if 'Input Cost Ask' not in clean_df.columns:
        print("[INFO] Calculating separate Ask/Bid input and workforce costs...")
        from data_analyzer import UnifiedAnalysisProcessor
        analyzer = UnifiedAnalysisProcessor()
        
        # Build price dictionaries per exchange - reuse for efficiency
        exchange_prices_cache = {}
        
        def calculate_costs_for_row(row):
            ticker = row['Ticker']
            exchange = row['Exchange']
            recipe = row.get('Recipe', None)  # Get the specific recipe for this row
            
            # Cache prices per exchange to avoid recalculating
            if exchange not in exchange_prices_cache:
                exchange_rows = all_df[(all_df['Ticker'].notna()) & (all_df['Exchange'] == exchange)]
                ask_prices = dict(zip(exchange_rows['Ticker'], exchange_rows['Ask_Price'].fillna(0)))
                bid_prices = dict(zip(exchange_rows['Ticker'], exchange_rows['Bid_Price'].fillna(0)))
                exchange_prices_cache[exchange] = (ask_prices, bid_prices)
            else:
                ask_prices, bid_prices = exchange_prices_cache[exchange]
            
            # Use the standalone function from calculators module with specific recipe
            costs = calculate_detailed_costs(
                ticker, 
                analyzer.recipe_inputs, 
                analyzer.recipe_outputs, 
                analyzer.buildingrecipes_df,
                analyzer.workforceneeds, 
                ask_prices, 
                bid_prices,
                specific_recipe=recipe  # Pass the specific recipe
            )
            return pd.Series(costs)
        
        try:
            cost_cols = clean_df.apply(calculate_costs_for_row, axis=1)
            clean_df['Input Cost Ask'] = cost_cols['input_cost_ask']
            clean_df['Input Cost Bid'] = cost_cols['input_cost_bid']
            clean_df['Workforce Cost Ask'] = cost_cols['workforce_cost_ask']
            clean_df['Workforce Cost Bid'] = cost_cols['workforce_cost_bid']
            
            # Debug: Show sample workforce costs
            wf_ask_nonzero = clean_df[clean_df['Workforce Cost Ask'] > 0]
            wf_bid_nonzero = clean_df[clean_df['Workforce Cost Bid'] > 0]
            print(f"[SUCCESS] Calculated Ask/Bid costs for all materials")
            print(f"[DEBUG] Materials with workforce costs: {len(wf_ask_nonzero)} (Ask), {len(wf_bid_nonzero)} (Bid)")
            if len(wf_ask_nonzero) > 0:
                sample = wf_ask_nonzero.head(3)[['Ticker', 'Exchange', 'Input Cost Ask', 'Workforce Cost Ask']]
                print(f"[DEBUG] Sample workforce costs:\n{sample.to_string()}")
        except Exception as e:
            print(f"[WARN] Could not calculate detailed costs: {e}")
            import traceback
            traceback.print_exc()
            # Fallback: use Input Cost per Unit for both, estimate workforce as 10%
            clean_df['Input Cost Ask'] = clean_df.get('Input Cost per Unit', 0)
            clean_df['Input Cost Bid'] = clean_df.get('Input Cost per Unit', 0)
            clean_df['Workforce Cost Ask'] = clean_df['Input Cost Ask'] * 0.10
            clean_df['Workforce Cost Bid'] = clean_df['Input Cost Bid'] * 0.10
    
    # Create the reference data tab first (hidden sheet with all data for lookups)
    # Include Recipe column for multi-recipe selection capability
    reference_df = clean_df[['Ticker', 'Recipe', 'Material Name', 'Exchange', 'Ask_Price', 'Bid_Price', 
                           'Input Cost Ask', 'Input Cost Bid', 
                           'Workforce Cost Ask', 'Workforce Cost Bid',
                           'Amount per Recipe', 'Supply', 'Demand']].copy()
    
    # Fill NaN values with 0 for numeric columns
    numeric_cols = ['Ask_Price', 'Bid_Price', 'Input Cost Ask', 'Input Cost Bid', 
                    'Workforce Cost Ask', 'Workforce Cost Bid', 'Amount per Recipe', 'Supply', 'Demand']
    for col in numeric_cols:
        reference_df[col] = reference_df[col].fillna(0)
    
    # Fill NaN in Recipe column with 'N/A'
    if 'Recipe' in reference_df.columns:
        reference_df['Recipe'] = reference_df['Recipe'].fillna('N/A')
    
    # Add lookup key (Ticker+Exchange concatenation for VLOOKUP)
    reference_df.insert(0, 'LookupKey', reference_df['Ticker'].astype(str) + reference_df['Exchange'].astype(str))
    
    # Debug: Show column structure and sample data
    print(f"[DEBUG] Reference DataFrame columns: {list(reference_df.columns)}")
    print(f"[DEBUG] Sample row with workforce costs:")
    wf_sample = reference_df[reference_df['Workforce Cost Ask'] > 0].head(1)
    if not wf_sample.empty:
        for col in reference_df.columns:
            print(f"  {col}: {wf_sample[col].values[0]}")
    
    # Upload reference data to a hidden sheet
    try:
        sheets_manager.upload_dataframe_to_sheet("Price Analyser Data", reference_df)
        print("[INFO] Uploaded reference data with workforce cost breakdown")
    except:
        print("[WARN] Could not upload reference data sheet")
    
    # Upload bids data for breakeven calculations
    try:
        base_dir = Path(__file__).parent.parent / "cache"
        bids_path = base_dir / "bids.csv"
        if bids_path.exists():
            bids_df = pd.read_csv(bids_path)
            sheets_manager.upload_dataframe_to_sheet("Bids", bids_df)
            print(f"[INFO] Uploaded {len(bids_df)} bids for order book analysis")
        else:
            print("[WARN] bids.csv not found, skipping bids upload")
    except Exception as e:
        print(f"[WARN] Could not upload bids data: {e}")
    
    # Get unique materials and exchanges from clean data
    materials = sorted(clean_df['Ticker'].unique().tolist())
    exchanges = sorted(clean_df['Exchange'].unique().tolist())
    print(f"[INFO] Found {len(materials)} materials and {len(exchanges)} exchanges")
    
    # Build the Price Analyser interface
    sheet_name = "Price Analyser"
    
    # Create the sheet structure with formulas
    rows = []
    
    # Title
    rows.append(["PRICE ANALYSER - Material Cost & ROI Calculator"])
    rows.append([])
    
    # Selection area with instructions
    rows.append(["SELECT MATERIAL:", "← Click cell A4 and use dropdown", "", ""])
    rows.append(["SELECT EXCHANGE:", "← Click cell A5 and use dropdown", "", ""])
    rows.append([])
    rows.append(["Note: Dropdowns work in Google Sheets. For GitHub Pages, use Google Sheets Embed or iframe.", "", ""])
    rows.append([])
    
    # Material info section
    rows.append(["═══ MATERIAL INFORMATION ═══"])
    rows.append(["Material Name:", "=IFERROR(VLOOKUP(A4&A5,'Price Analyser Data'!A:C,3,FALSE),\"\")"])
    rows.append(["Exchange:", "=A5"])
    rows.append(["Amount per Recipe:", "=IFERROR(VLOOKUP(A4&A5,'Price Analyser Data'!A:I,9,FALSE),1)"])
    rows.append([])
    
    # Cost breakdown section
    rows.append(["═══ COST BREAKDOWN ═══"])
    rows.append(["Input Cost per Unit:", "=IFERROR(VLOOKUP(A4&A5,'Price Analyser Data'!A:G,7,FALSE),0)"])
    rows.append(["Input Cost per Stack:", "=B15*B12"])
    rows.append(["Stack Size:", "=B12"])
    rows.append([])
    
    # Pricing section
    rows.append(["═══ MARKET PRICING ═══"])
    rows.append(["Ask Price (Sell to Buy Orders):", "=IFERROR(VLOOKUP(A4&A5,'Price Analyser Data'!A:E,5,FALSE),0)"])
    rows.append(["Bid Price (Sell to Market):", "=IFERROR(VLOOKUP(A4&A5,'Price Analyser Data'!A:F,6,FALSE),0)"])
    rows.append([])
    
    # Revenue section
    rows.append(["═══ REVENUE ANALYSIS ═══"])
    rows.append(["Revenue per Unit (Ask):", "=B20"])
    rows.append(["Revenue per Unit (Bid):", "=B21"])
    rows.append(["Revenue per Stack (Ask):", "=B20*B12"])
    rows.append(["Revenue per Stack (Bid):", "=B21*B12"])
    rows.append([])
    
    # Profit section
    rows.append(["═══ PROFIT ANALYSIS ═══"])
    rows.append(["Profit per Unit (Ask):", "=B20-B15"])
    rows.append(["Profit per Unit (Bid):", "=B21-B15"])
    rows.append(["Profit per Stack (Ask):", "=B30*B12"])
    rows.append(["Profit per Stack (Bid):", "=B31*B12"])
    rows.append([])
    
    # ROI section
    rows.append(["═══ ROI (Return on Investment) ═══"])
    rows.append(["ROI % (Ask):", "=IF(B15>0,(B30/B15),0)"])
    rows.append(["ROI % (Bid):", "=IF(B15>0,(B31/B15),0)"])
    rows.append([])
    
    # Breakeven section
    rows.append(["═══ BREAKEVEN ANALYSIS ═══"])
    rows.append(["Supply Available:", "=IFERROR(VLOOKUP(A4&A5,'Price Analyser Data'!A:J,10,FALSE),0)"])
    rows.append(["Demand Available:", "=IFERROR(VLOOKUP(A4&A5,'Price Analyser Data'!A:K,11,FALSE),0)"])
    rows.append(["Units to Breakeven (if loss):", "=IF(B30<0,ABS(B15/B30),\"Profitable\")"])
    rows.append(["Stacks to Breakeven (if loss):", "=IF(B30<0,B44/B12,\"Profitable\")"])
    rows.append([])
    
    # Market capacity
    rows.append(["═══ MARKET CAPACITY ═══"])
    rows.append(["Can Sell (Supply):", "=B42"])
    rows.append(["Market Wants (Demand):", "=B43"])
    rows.append(["Max Profitable Units:", "=MIN(B42,B43)"])
    rows.append(["Max Profitable Stacks:", "=B50/B12"])
    rows.append([])
    
    # Notes
    rows.append(["═══ NOTES ═══"])
    rows.append(["- Ask Price: Selling to existing buy orders (immediate sale)"])
    rows.append(["- Bid Price: Creating sell orders (wait for buyers)"])
    rows.append(["- ROI: Percentage return on your input cost investment"])
    rows.append(["- Breakeven: How many units needed to recover losses (if unprofitable)"])
    
    # Convert to DataFrame
    analyser_df = pd.DataFrame(rows)
    
    # Upload to Google Sheets
    try:
        sheets_manager.upload_dataframe_to_sheet(sheet_name, analyser_df)
        print(f"[SUCCESS] Created {sheet_name} tab")
    except Exception as e:
        print(f"[ERROR] Failed to create {sheet_name}: {e}")
        return
    
    # Apply formatting and dropdowns
    apply_price_analyser_formatting(sheets_manager, sheet_name, materials, exchanges, all_df)

def apply_price_analyser_formatting(sheets_manager, sheet_name, materials, exchanges, all_df):
    """
    Apply formatting and data validation dropdowns to the Price Analyser tab.
    """
    from googleapiclient.errors import HttpError
    
    try:
        sheet_id = sheets_manager._get_sheet_id(sheet_name)
        requests = []
        
        # 1. Add data validation dropdown for Material (A4)
        material_list = [[m] for m in materials]
        requests.append({
            "setDataValidation": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 3,
                    "endRowIndex": 4,
                    "startColumnIndex": 0,
                    "endColumnIndex": 1
                },
                "rule": {
                    "condition": {
                        "type": "ONE_OF_LIST",
                        "values": [{"userEnteredValue": m} for m in materials]
                    },
                    "showCustomUi": True,
                    "strict": True
                }
            }
        })
        
        # 2. Add data validation dropdown for Exchange (A5)
        requests.append({
            "setDataValidation": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 4,
                    "endRowIndex": 5,
                    "startColumnIndex": 0,
                    "endColumnIndex": 1
                },
                "rule": {
                    "condition": {
                        "type": "ONE_OF_LIST",
                        "values": [{"userEnteredValue": e} for e in exchanges]
                    },
                    "showCustomUi": True,
                    "strict": True
                }
            }
        })
        
        # 3. Format title (row 1)
        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 4
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.8},
                        "textFormat": {"bold": True, "fontSize": 14, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                        "horizontalAlignment": "CENTER"
                    }
                },
                "fields": "userEnteredFormat"
            }
        })
        
        # 4. Format section headers (rows with ═══)
        section_rows = [8, 13, 18, 23, 29, 35, 40, 47, 52]
        for row_idx in section_rows:
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": row_idx,
                        "endRowIndex": row_idx + 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": 2
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0.85, "green": 0.85, "blue": 0.85},
                            "textFormat": {"bold": True, "fontSize": 11},
                            "horizontalAlignment": "LEFT"
                        }
                    },
                    "fields": "userEnteredFormat"
                }
            })
        
        # 5. Format currency cells (column B for values)
        currency_rows = [14, 15, 19, 20, 21, 24, 25, 26, 27, 30, 31, 32, 33]
        for row_idx in currency_rows:
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": row_idx,
                        "endRowIndex": row_idx + 1,
                        "startColumnIndex": 1,
                        "endColumnIndex": 2
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "numberFormat": {
                                "type": "CURRENCY",
                                "pattern": "#,##0.00 [$ICA]"
                            }
                        }
                    },
                    "fields": "userEnteredFormat(numberFormat)"
                }
            })
        
        # 6. Format percentage cells (ROI rows)
        percent_rows = [36, 37]
        for row_idx in percent_rows:
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": row_idx,
                        "endRowIndex": row_idx + 1,
                        "startColumnIndex": 1,
                        "endColumnIndex": 2
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "numberFormat": {
                                "type": "PERCENT",
                                "pattern": "0.00%"
                            }
                        }
                    },
                    "fields": "userEnteredFormat(numberFormat)"
                }
            })
        
        # 7. Format number cells (supply, demand, units)
        number_rows = [11, 16, 41, 42, 43, 44, 45, 48, 49, 50, 51]
        for row_idx in number_rows:
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": row_idx,
                        "endRowIndex": row_idx + 1,
                        "startColumnIndex": 1,
                        "endColumnIndex": 2
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "numberFormat": {
                                "type": "NUMBER",
                                "pattern": "#,##0"
                            }
                        }
                    },
                    "fields": "userEnteredFormat(numberFormat)"
                }
            })
        
        # 8. Auto-resize columns
        requests.append({
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": 4
                }
            }
        })
        
        # 9. Freeze first row
        requests.append({
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {
                        "frozenRowCount": 1
                    }
                },
                "fields": "gridProperties.frozenRowCount"
            }
        })
        
        # Send all requests
        if requests:
            sheets_manager.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=sheets_manager.spreadsheet_id,
                body={"requests": requests}
            ).execute()
            print(f"[SUCCESS] Applied formatting to {sheet_name}")
        
        # 10. Hide the reference sheets (Price Analyser Data and Bids)
        try:
            hide_requests = []
            
            # Hide Price Analyser Data sheet
            data_sheet_id = sheets_manager._get_sheet_id("Price Analyser Data")
            hide_requests.append({
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": data_sheet_id,
                        "hidden": True
                    },
                    "fields": "hidden"
                }
            })
            
            # Hide Bids sheet if it exists
            try:
                bids_sheet_id = sheets_manager._get_sheet_id("Bids")
                hide_requests.append({
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": bids_sheet_id,
                            "hidden": True
                        },
                        "fields": "hidden"
                    }
                })
            except:
                pass  # Bids sheet might not exist
            
            # Hide Planet Resources sheet if it exists
            try:
                planet_sheet_id = sheets_manager._get_sheet_id("Planet Resources")
                hide_requests.append({
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": planet_sheet_id,
                            "hidden": True
                        },
                        "fields": "hidden"
                    }
                })
            except:
                pass  # Planet Resources sheet might not exist
            
            # Hide Report View sheet if it exists
            try:
                report_view_sheet_id = sheets_manager._get_sheet_id("Report View")
                hide_requests.append({
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": report_view_sheet_id,
                            "hidden": True
                        },
                        "fields": "hidden"
                    }
                })
            except:
                pass  # Report View sheet might not exist
            
            sheets_manager.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=sheets_manager.spreadsheet_id,
                body={"requests": hide_requests}
            ).execute()
            print("[SUCCESS] Hidden reference data sheets")
        except Exception as e:
            print(f"[WARN] Could not hide reference sheet: {e}")
        
    except HttpError as e:
        print(f"[ERROR] Failed to format {sheet_name}: {e}")

def main():
    print("[STEP] Starting report tab generation...", flush=True)
    if not ENHANCED_FILE.exists():
        print(f"[FATAL] Enhanced analysis file not found: {ENHANCED_FILE}")
        return

    all_df = pd.read_csv(ENHANCED_FILE)
    orders_df = load_and_prepare_orders()
    arbitrage_df = compute_arbitrage_opportunities(all_df, orders_df=orders_df)
    if not arbitrage_df.empty:
        arbitrage_df = assign_opportunity_level(arbitrage_df)
    else:
        print("[WARN] No arbitrage opportunities found.")

    # Load and prepare orders with Side column
    orders_df = load_and_prepare_orders()
    print(orders_df.head(20))
    print(orders_df['Side'].value_counts())

    market_data_path = CACHE_DIR / "market_data.csv"
    sheets = SheetsManager()
    
    # Generate exchange-specific reports
    for exch, tab in zip(EXCHANGES, REPORT_TABS):
        exch_df = all_df[all_df['Exchange'] == exch] if 'Exchange' in all_df.columns else all_df
        print(f"[DEBUG] {tab}: {len(exch_df)} rows")
        report_df = build_report_tab(
            exch_df, exch, arbitrage_df, all_df,
            orders_df=orders_df,
            market_data_path=market_data_path
        )
        print(f"[DEBUG] {tab} report_df: {len(report_df)} rows")
        upload_df_method = getattr(sheets, "upload_dataframe_to_sheet", None)
        upload_sheet_method = getattr(sheets, "upload_to_sheet", None)
        if callable(upload_df_method):
            upload_df_method(tab, report_df)
        elif callable(upload_sheet_method):
            upload_sheet_method(SPREADSHEET_ID, tab, report_df)
        else:
            print(" No valid upload method found in SheetsManager")
        apply_report_tab_formatting(sheets, tab, report_df)
        time.sleep(2)
    
    # Generate Overall Report
    print("[STEP] Generating Overall Report...", flush=True)
    overall_df = build_overall_report(all_df)
    print(f"[DEBUG] Overall Report: {len(overall_df)} rows, {len(overall_df.columns)} cols")
    
    # Upload Overall Report
    if callable(upload_df_method):
        upload_df_method("Overall Report", overall_df)
    elif callable(upload_sheet_method):
        upload_sheet_method(SPREADSHEET_ID, "Overall Report", overall_df)
    else:
        print(" No valid upload method found in SheetsManager")
    
    # Apply formatting to Overall Report
    apply_overall_report_formatting(sheets, "Overall Report", overall_df)
    
    # Generate Financial Overview
    print("[STEP] Generating Financial Overview...", flush=True)
    # External financial data spreadsheet ID
    FINANCIAL_SPREADSHEET_ID = "17MvM86qR-mN7fSPX86L7TbvDXLBYRCT5IlCd5zfXddA"
    
    # Fetch financial data from external spreadsheet
    financial_data = fetch_financial_data(sheets, FINANCIAL_SPREADSHEET_ID)
    
    # Build Financial Overview tab
    financial_overview_df = build_financial_overview(financial_data, all_df)
    print(f"[DEBUG] Financial Overview: {len(financial_overview_df)} rows, {len(financial_overview_df.columns)} cols")
    
    # Upload Financial Overview
    if callable(upload_df_method):
        upload_df_method("Financial Overview", financial_overview_df)
    elif callable(upload_sheet_method):
        upload_sheet_method(SPREADSHEET_ID, "Financial Overview", financial_overview_df)
    else:
        print(" No valid upload method found in SheetsManager")
    
    # Apply formatting to Financial Overview
    apply_financial_overview_formatting(sheets, "Financial Overview", financial_overview_df)
    
    # Charts commented out for now - will add later
    # add_financial_overview_charts(sheets, "Financial Overview", financial_overview_df)
    
    # Generate Price Analyser
    print("[STEP] Generating Price Analyser...", flush=True)
    create_price_analyser_tab(sheets, all_df)
    
    print("[SUCCESS] All reports generated successfully!")
    print(f"[DEBUG] Arbitrage DataFrame rows: {len(arbitrage_df)}")
    print(arbitrage_df.head())
    print(arbitrage_df[['Ticker', 'Buy Exchange', 'Sell Exchange', 'Opportunity Size']].sort_values('Opportunity Size', ascending=False).head(20))

def input_bottleneck_section(df, recipe_inputs_path, top_n=20):
    # Load recipe inputs
    recipe_inputs = pd.read_csv(recipe_inputs_path)
    # Count how many recipes use each material as input
    input_counts = recipe_inputs['Material'].value_counts().to_dict()
    df['InputCount'] = df['Ticker'].map(input_counts).fillna(0)
    # Filter for low supply and high input count
    bottlenecks = df[(df['Supply'] < 100) & (df['InputCount'] > 2)].sort_values("InputCount", ascending=False).head(top_n)
    subheader = ["Ticker", "Name", "Supply", "InputCount", "Chokepoint Type"]
    rows = []
    for _, row in bottlenecks.iterrows():
        rows.append([
            row.get('Ticker', ''),
            row.get('Material Name', ''),
            f"{row.get('Supply', 0):,.0f}",
            int(row.get('InputCount', 0)),
            "Input Bottleneck"
        ])
    return section_header("Input Bottlenecks", len(subheader)) + [subheader] + rows + [[""] * len(subheader)]

def find_arbitrage_bottom_border_rows(df, arb_start_col, arb_width):
    """
    Returns the row indices (in the report DataFrame) where a bottom border should be applied
    (i.e., the last row of each Sell Exchange group in the arbitrage section).
    """
    # Subheader is row 2, data starts at row 3 (index 2)
    sell_ex_col = None
    subheader = df.iloc[1, arb_start_col:arb_start_col+arb_width]
    for i, col_name in enumerate(subheader):
        if str(col_name).strip().lower() == "sell exchange":
            sell_ex_col = arb_start_col + i
            break
    if sell_ex_col is None:
        return []

    # Data rows start at row 3 (index 2)
    data_rows = []
    prev_val = None
    last_row_idx = None
    for row_idx in range(3, len(df)):
        val = df.iloc[row_idx, sell_ex_col]
        if prev_val is not None and val != prev_val:
            # The previous row was the last of its group
            data_rows.append(row_idx - 1)
        prev_val = val
        last_row_idx = row_idx
    if last_row_idx is not None:
        data_rows.append(last_row_idx)  # Always add the last row
    return data_rows

def apply_overall_report_formatting(sheets_manager, sheet_name, df):
    """
    Apply formatting to the Overall Report tab.
    """
    from googleapiclient.errors import HttpError
    
    sheet_id = sheets_manager._get_sheet_id(sheet_name)
    requests = []
    
    # 0. Clear all formatting
    requests.append({
        "updateCells": {
            "range": {"sheetId": sheet_id},
            "fields": "userEnteredFormat"
        }
    })
    
    # 1. Center all text
    requests.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": len(df) + 1,
                "startColumnIndex": 0,
                "endColumnIndex": len(df.columns)
            },
            "cell": {
                "userEnteredFormat": {
                    "horizontalAlignment": "CENTER"
                }
            },
            "fields": "userEnteredFormat(horizontalAlignment)"
        }
    })
    
    # 2. Find section headers and format them
    section_colors = {
        "EXCHANGE COMPARISON BY PROFESSION": {"red": 0.2, "green": 0.5, "blue": 0.8},
        "MOST PROFITABLE EXCHANGE COUNT": {"red": 0.3, "green": 0.7, "blue": 0.5},
        "BEST & WORST EXCHANGES PER TICKER": {"red": 0.8, "green": 0.4, "blue": 0.2}
    }
    
    for row_idx in range(len(df)):
        first_cell = str(df.iloc[row_idx, 0]).strip().upper()
        if first_cell in section_colors:
            color = section_colors[first_cell]
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": row_idx + 1,
                        "endRowIndex": row_idx + 2,
                        "startColumnIndex": 0,
                        "endColumnIndex": len(df.columns)
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": color,
                            "textFormat": {"bold": True, "fontSize": 14, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                            "horizontalAlignment": "CENTER"
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
                }
            })
    
    # 3. Format column headers (find rows with "Profession", "Ticker", etc.)
    for row_idx in range(len(df)):
        first_cell = str(df.iloc[row_idx, 0]).strip()
        if first_cell in ["Profession", "Ticker"]:
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": row_idx + 1,
                        "endRowIndex": row_idx + 2,
                        "startColumnIndex": 0,
                        "endColumnIndex": len(df.columns)
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
                            "textFormat": {"bold": True, "fontSize": 11},
                            "horizontalAlignment": "CENTER"
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
                }
            })
    
    # 4. Auto-resize all columns
    requests.append({
        "autoResizeDimensions": {
            "dimensions": {
                "sheetId": sheet_id,
                "dimension": "COLUMNS",
                "startIndex": 0,
                "endIndex": len(df.columns)
            }
        }
    })
    
    # 5. Add gradient formatting for numeric columns
    # Find "Avg Profit" column
    for row_idx in range(len(df)):
        first_cell = str(df.iloc[row_idx, 0]).strip()
        if first_cell == "Profession":
            # This is the header row for Exchange Comparison
            header_row = df.iloc[row_idx].tolist()
            try:
                avg_profit_idx = header_row.index("Avg Profit")
                # Add gradient to Avg Profit column
                requests.append({
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{
                                "sheetId": sheet_id,
                                "startRowIndex": row_idx + 2,
                                "endRowIndex": len(df) + 1,
                                "startColumnIndex": avg_profit_idx,
                                "endColumnIndex": avg_profit_idx + 1
                            }],
                            "gradientRule": {
                                "minpoint": {"color": {"red": 1, "green": 0.8, "blue": 0.2}, "type": "NUMBER", "value": "0"},
                                "maxpoint": {"color": {"red": 0.2, "green": 0.8, "blue": 0.2}, "type": "NUMBER", "value": "500"}
                            }
                        },
                        "index": 0
                    }
                })
            except ValueError:
                pass
            
            # Format Median Profit column in frequency section
            try:
                median_profit_idx = header_row.index("Median Profit")
                # Add gradient to Median Profit column
                requests.append({
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{
                                "sheetId": sheet_id,
                                "startRowIndex": row_idx + 2,
                                "endRowIndex": len(df) + 1,
                                "startColumnIndex": median_profit_idx,
                                "endColumnIndex": median_profit_idx + 1
                            }],
                            "gradientRule": {
                                "minpoint": {"color": {"red": 1, "green": 0.8, "blue": 0.2}, "type": "NUMBER", "value": "0"},
                                "maxpoint": {"color": {"red": 0.2, "green": 0.8, "blue": 0.2}, "type": "NUMBER", "value": "500"}
                            }
                        },
                        "index": 0
                    }
                })
            except ValueError:
                pass
            
            try:
                avg_roi_idx = header_row.index("Avg ROI")
                # Add gradient to Avg ROI column (remove % sign for comparison)
                requests.append({
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{
                                "sheetId": sheet_id,
                                "startRowIndex": row_idx + 2,
                                "endRowIndex": len(df) + 1,
                                "startColumnIndex": avg_roi_idx,
                                "endColumnIndex": avg_roi_idx + 1
                            }],
                            "gradientRule": {
                                "minpoint": {"color": {"red": 1, "green": 1, "blue": 0.2}, "type": "NUMBER", "value": "0"},
                                "maxpoint": {"color": {"red": 0.2, "green": 1, "blue": 0.2}, "type": "NUMBER", "value": "50"}
                            }
                        },
                        "index": 0
                    }
                })
            except ValueError:
                pass
            break
    
    # 6. Find and format Best/Worst Exchanges section
    for row_idx in range(len(df)):
        first_cell = str(df.iloc[row_idx, 0]).strip()
        if first_cell == "Ticker":
            # Check if this is the Best/Worst section by looking at adjacent columns
            if row_idx < len(df) - 1:
                header_row = df.iloc[row_idx].tolist()
                try:
                    diff_idx = header_row.index("Difference")
                    # Add gradient to Difference column
                    requests.append({
                        "addConditionalFormatRule": {
                            "rule": {
                                "ranges": [{
                                    "sheetId": sheet_id,
                                    "startRowIndex": row_idx + 2,
                                    "endRowIndex": len(df) + 1,
                                    "startColumnIndex": diff_idx,
                                    "endColumnIndex": diff_idx + 1
                                }],
                                "gradientRule": {
                                    "minpoint": {"color": {"red": 1, "green": 0.2, "blue": 0.2}, "type": "NUMBER", "value": "0"},
                                    "midpoint": {"color": {"red": 1, "green": 1, "blue": 0.4}, "type": "NUMBER", "value": "250"},
                                    "maxpoint": {"color": {"red": 0.2, "green": 0.8, "blue": 0.2}, "type": "NUMBER", "value": "500"}
                                }
                            },
                            "index": 0
                        }
                    })
                except ValueError:
                    pass
    
    # 7. Color code exchange names throughout the report
    # Define distinct colors for each exchange
    exchange_colors = {
        "AI1": {"red": 0.2, "green": 0.6, "blue": 1.0},      # Light Blue
        "CI1": {"red": 1.0, "green": 0.4, "blue": 0.4},      # Coral Red
        "CI2": {"red": 1.0, "green": 0.6, "blue": 0.2},      # Orange
        "IC1": {"red": 0.4, "green": 0.8, "blue": 0.4},      # Light Green
        "NC1": {"red": 0.8, "green": 0.4, "blue": 0.8},      # Purple
        "NC2": {"red": 1.0, "green": 0.8, "blue": 0.2}       # Yellow
    }
    
    # Scan all cells and apply colors to exchange names
    for row_idx in range(len(df)):
        for col_idx in range(len(df.columns)):
            cell_value = str(df.iloc[row_idx, col_idx]).strip().upper()
            if cell_value in exchange_colors:
                requests.append({
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": row_idx + 1,
                            "endRowIndex": row_idx + 2,
                            "startColumnIndex": col_idx,
                            "endColumnIndex": col_idx + 1
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": exchange_colors[cell_value],
                                "textFormat": {
                                    "bold": True,
                                    "fontSize": 11,
                                    "foregroundColor": {"red": 0, "green": 0, "blue": 0}
                                },
                                "horizontalAlignment": "CENTER"
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
                    }
                })
    
    # 8. Highlight most frequent exchanges in "MOST PROFITABLE EXCHANGE COUNT" section
    # Find the frequency section header and data rows
    frequency_section_start = None
    frequency_header_row = None
    
    for row_idx in range(len(df)):
        first_cell = str(df.iloc[row_idx, 0]).strip().upper()
        if "MOST PROFITABLE EXCHANGE COUNT" in first_cell:
            frequency_section_start = row_idx
            frequency_header_row = row_idx + 1
            break
    
    if frequency_section_start is not None and frequency_header_row is not None:
        # Get header to find exchange column indices
        header_row = df.iloc[frequency_header_row].tolist()
        exchange_col_indices = {}
        for i, col_name in enumerate(header_row):
            col_str = str(col_name).strip().upper()
            if col_str in EXCHANGES:
                exchange_col_indices[col_str] = i
        
        # Process each profession row (data starts at frequency_header_row + 1)
        data_start_row = frequency_header_row + 1
        for row_idx in range(data_start_row, len(df)):
            # Check if we've left the frequency section
            first_cell = str(df.iloc[row_idx, 0]).strip()
            if not first_cell or first_cell.upper() in ["BEST & WORST EXCHANGES PER TICKER", ""]:
                break
            
            # Get counts for each exchange in this row
            counts = {}
            for exch, col_idx in exchange_col_indices.items():
                try:
                    count_str = str(df.iloc[row_idx, col_idx]).strip()
                    counts[exch] = int(count_str) if count_str.isdigit() else 0
                except (ValueError, IndexError):
                    counts[exch] = 0
            
            if not counts or max(counts.values()) == 0:
                continue
            
            # Find max count and close runners-up (within 20% of max)
            max_count = max(counts.values())
            threshold = max_count * 0.8  # 80% of max = "close"
            
            for exch, count in counts.items():
                col_idx = exchange_col_indices[exch]
                if count == max_count:
                    # Highest count - full color (darker)
                    bg_color = {"red": 0.2, "green": 0.8, "blue": 0.2}  # Bright green
                    requests.append({
                        "repeatCell": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": row_idx + 1,
                                "endRowIndex": row_idx + 2,
                                "startColumnIndex": col_idx,
                                "endColumnIndex": col_idx + 1
                            },
                            "cell": {
                                "userEnteredFormat": {
                                    "backgroundColor": bg_color,
                                    "textFormat": {
                                        "bold": True,
                                        "fontSize": 11,
                                        "foregroundColor": {"red": 0, "green": 0, "blue": 0}
                                    },
                                    "horizontalAlignment": "CENTER"
                                }
                            },
                            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
                        }
                    })
                elif count >= threshold and count > 0:
                    # Close runner-up - lighter color
                    bg_color = {"red": 0.6, "green": 0.95, "blue": 0.6}  # Light green
                    requests.append({
                        "repeatCell": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": row_idx + 1,
                                "endRowIndex": row_idx + 2,
                                "startColumnIndex": col_idx,
                                "endColumnIndex": col_idx + 1
                            },
                            "cell": {
                                "userEnteredFormat": {
                                    "backgroundColor": bg_color,
                                    "textFormat": {
                                        "fontSize": 11,
                                        "foregroundColor": {"red": 0, "green": 0, "blue": 0}
                                    },
                                    "horizontalAlignment": "CENTER"
                                }
                            },
                            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
                        }
                    })
    
    # Send batchUpdate request
    if requests:
        try:
            sheets_manager.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=sheets_manager.spreadsheet_id,
                body={"requests": requests}
            ).execute()
            print(f" Formatting applied to {sheet_name}")
        except HttpError as e:
            print(f" Formatting failed for {sheet_name}: {e}")

def assign_opportunity_level(arbitrage_df):
    """
    Assigns an Opportunity Level based on ROI and Opportunity Size (amount you can sell for profit).
    Higher ROI and higher Opportunity Size yield higher levels.
    """
    def level(row):
        roi = row.get('ROI', 0)
        size = row.get('Opportunity Size', 0)
        # Require at least 100 units to consider "High" or above, and at least 10 for "Medium"
        if roi > 100 and size >= 1000:
            return "Very High"
        elif roi > 50 and size >= 500:
            return "High"
        elif roi > 20 and size >= 100:
            return "Medium"
        elif roi > 5 and size >= 10:
            return "Low"
        else:
            return "Very Low"
    arbitrage_df['Opportunity Level'] = arbitrage_df.apply(level, axis=1)
    return arbitrage_df

def build_overall_report(all_df):
    """
    Creates an Overall Report tab with:
    1. Exchange comparison by sector/profession (side-by-side sections)
       - Section 1A: Average metrics per profession/exchange
       - Section 1B: Exchange frequency and median profit per profession
    2. Best/worst exchanges for each ticker
    Returns a properly structured DataFrame for upload.
    """
    
    # Section 1: Exchange Comparison by Profession (building-based)
    professions = ["METALLURGY", "MANUFACTURING", "CONSTRUCTION", "CHEMISTRY", "FOOD_INDUSTRIES", "AGRICULTURE", "FUEL_REFINING", "ELECTRONICS", "RESOURCE_EXTRACTION"]
    
    # Load buildings and recipes for profession mapping
    buildings_path = CACHE_DIR / "buildings.csv"
    recipe_outputs_path = CACHE_DIR / "recipe_outputs.csv"
    buildingrecipes_path = CACHE_DIR / "buildingrecipes.csv"
    
    section1a_rows = []
    section1b_rows = []
    
    if buildings_path.exists() and recipe_outputs_path.exists() and buildingrecipes_path.exists():
        buildings = pd.read_csv(buildings_path)
        recipe_outputs = pd.read_csv(recipe_outputs_path)
        buildingrecipes = pd.read_csv(buildingrecipes_path)
        
        building_expertise = buildings.set_index('Ticker')['Expertise'].to_dict()
        recipe_to_building = buildingrecipes.set_index('Key')['Building'].to_dict()
        
        # Section 1A: Build profession comparison (avg metrics per exchange)
        comparison_data = []
        
        # Section 1B: Build profession exchange frequency and median profit
        frequency_data = []
        
        for profession in professions:
            # PRIMARY: Get materials for this profession based on building expertise
            relevant_tickers = set()
            for recipe_key, material in recipe_outputs[['Key', 'Material']].values:
                building = recipe_to_building.get(recipe_key)
                if building and building_expertise.get(building, '') == profession:
                    relevant_tickers.add(material)
            
            # SECONDARY: Category-based fallback ONLY for tier 0 resources (no buildings produce these)
            if profession == "RESOURCE_EXTRACTION":
                tier_0_materials = all_df[all_df.get('Tier', 999) == 0.0]['Ticker'].unique()
                relevant_tickers.update(tier_0_materials)
            
            if not relevant_tickers:
                continue
            
            # For Section 1A: Calculate avg profit and ROI per exchange
            for exch in EXCHANGES:
                exch_data = all_df[(all_df['Exchange'] == exch) & (all_df['Ticker'].isin(relevant_tickers))]
                if exch_data.empty:
                    continue
                
                avg_profit = exch_data.get('Profit per Unit', exch_data.get('Profit_Ask', pd.Series([0]))).mean()
                avg_roi = exch_data.get('ROI Ask %', exch_data.get('ROI_Ask', pd.Series([0]))).mean()
                material_count = len(exch_data)
                
                comparison_data.append([
                    profession,
                    exch,
                    material_count,
                    f"{avg_profit:,.2f}",
                    f"{avg_roi:,.2f}%"
                ])
            
            # For Section 1B: Count which exchange is most profitable for each material
            prof_data = all_df[all_df['Ticker'].isin(relevant_tickers)]
            if not prof_data.empty:
                # For each material, find which exchange has the highest profit
                profit_col = 'Profit per Unit' if 'Profit per Unit' in prof_data.columns else 'Profit_Ask'
                most_profitable_counts = {exch: 0 for exch in EXCHANGES}
                
                for ticker in relevant_tickers:
                    ticker_data = prof_data[prof_data['Ticker'] == ticker]
                    if not ticker_data.empty and profit_col in ticker_data.columns:
                        # Find exchange with highest profit for this ticker
                        max_profit_idx = ticker_data[profit_col].idxmax()
                        best_exchange = ticker_data.loc[max_profit_idx, 'Exchange']
                        if best_exchange in most_profitable_counts:
                            most_profitable_counts[best_exchange] += 1
                
                # Calculate median profit for the entire profession
                all_profits = prof_data.get('Profit per Unit', prof_data.get('Profit_Ask', pd.Series([0])))
                median_profit = all_profits.median()
                
                # Create row showing which exchange is most profitable most often
                frequency_row = [profession]
                for exch in EXCHANGES:
                    count = most_profitable_counts.get(exch, 0)
                    frequency_row.append(str(count))
                frequency_row.append(f"{median_profit:,.2f}")
                
                frequency_data.append(frequency_row)
        
        # Build Section 1A
        comparison_header = ["Profession", "Exchange", "Material Count", "Avg Profit", "Avg ROI"]
        section1a_rows.append(["EXCHANGE COMPARISON BY PROFESSION", "", "", "", ""])
        section1a_rows.append(comparison_header)
        section1a_rows.extend(comparison_data)
        
        # Build Section 1B
        frequency_header = ["Profession"] + EXCHANGES + ["Median Profit"]
        section1b_rows.append(["MOST PROFITABLE EXCHANGE COUNT", "", "", "", "", "", ""])
        section1b_rows.append(frequency_header)
        section1b_rows.extend(frequency_data)
    
    # Combine sections side by side
    max_rows = max(len(section1a_rows), len(section1b_rows))
    
    # Pad sections to same height
    while len(section1a_rows) < max_rows:
        section1a_rows.append([""] * 5)
    while len(section1b_rows) < max_rows:
        section1b_rows.append([""] * 8)  # 1 profession + 6 exchanges + 1 median
    
    # Combine horizontally with a blank column separator
    combined_rows = []
    for i in range(max_rows):
        combined_rows.append(section1a_rows[i] + [""] + section1b_rows[i])
    
    combined_rows.append([""] * (5 + 1 + 8))  # Blank row separator
    
    # Section 2: Best & Worst Exchanges per Ticker
    ticker_comparison = []
    for ticker in all_df['Ticker'].unique():
        ticker_data = all_df[all_df['Ticker'] == ticker]
        if ticker_data.empty:
            continue
        
        # Get material name
        material_name = ticker_data.iloc[0].get('Material Name', ticker_data.iloc[0].get('Name', ticker))
        
        # Find best and worst exchanges by profit
        profits = {}
        for exch in EXCHANGES:
            exch_data = ticker_data[ticker_data['Exchange'] == exch]
            if not exch_data.empty:
                profit = exch_data.get('Profit per Unit', exch_data.get('Profit_Ask', pd.Series([0]))).mean()
                profits[exch] = profit
        
        if not profits:
            continue
        
        best_exch = max(profits, key=profits.get)
        worst_exch = min(profits, key=profits.get)
        best_profit = profits[best_exch]
        worst_profit = profits[worst_exch]
        profit_diff = best_profit - worst_profit
        
        ticker_comparison.append([
            ticker,
            material_name,
            best_exch,
            f"{best_profit:,.2f}",
            worst_exch,
            f"{worst_profit:,.2f}",
            f"{profit_diff:,.2f}"
        ])
    
    # Sort by profit difference descending
    ticker_comparison.sort(key=lambda x: float(x[6].replace(',', '')), reverse=True)
    
    ticker_header = ["Ticker", "Name", "Best Exchange", "Best Profit", "Worst Exchange", "Worst Profit", "Difference"]
    # Add section header
    combined_rows.append(["BEST & WORST EXCHANGES PER TICKER", "", "", "", "", "", ""])
    combined_rows.append(ticker_header)
    combined_rows.extend(ticker_comparison)
    
    # Convert to DataFrame with proper structure
    max_cols = max(len(row) for row in combined_rows)
    # Pad all rows to same length
    padded_rows = [row + [""] * (max_cols - len(row)) for row in combined_rows]
    
    return pd.DataFrame(padded_rows)

def profession_section(df, exch, profession_name, top_n=None):
    """
    Creates a section for a specific profession showing ALL materials by profit and ROI.
    Materials are assigned based on the building type that produces them (building expertise).
    
    profession_name: METALLURGY, MANUFACTURING, CONSTRUCTION, CHEMISTRY, FOOD_INDUSTRIES, 
                    AGRICULTURE, FUEL_REFINING, ELECTRONICS, RESOURCE_EXTRACTION
    top_n: Ignored (kept for backwards compatibility) - now shows all materials
    """
    # Load buildings to map Ticker to Expertise
    buildings_path = CACHE_DIR / "buildings.csv"
    if not buildings_path.exists():
        return section_header(f"{profession_name} - DATA NOT AVAILABLE", 8) + [[""]*8]
    
    buildings = pd.read_csv(buildings_path)
    recipe_outputs_path = CACHE_DIR / "recipe_outputs.csv"
    buildingrecipes_path = CACHE_DIR / "buildingrecipes.csv"
    
    if not recipe_outputs_path.exists() or not buildingrecipes_path.exists():
        return section_header(f"{profession_name} - DATA NOT AVAILABLE", 8) + [[""]*8]
    
    recipe_outputs = pd.read_csv(recipe_outputs_path)
    buildingrecipes = pd.read_csv(buildingrecipes_path)
    
    # Map building to expertise
    building_expertise = buildings.set_index('Ticker')['Expertise'].to_dict()
    
    # Map recipe key to building
    recipe_to_building = buildingrecipes.set_index('Key')['Building'].to_dict()
    
    # Use the comprehensive material-to-profession mapping that handles multi-profession materials
    material_to_professions = get_material_to_profession_map()
    
    # Add tier 0 resources to RESOURCE_EXTRACTION (they can be extracted)
    if 'Tier' in df.columns:
        tier_0_materials = df[df['Tier'] == 0.0]['Ticker'].unique()
        for material in tier_0_materials:
            if material not in material_to_professions:
                material_to_professions[material] = ['RESOURCE_EXTRACTION']
            elif 'RESOURCE_EXTRACTION' not in material_to_professions[material]:
                material_to_professions[material].append('RESOURCE_EXTRACTION')
    
    # Get materials for this profession (materials can belong to multiple professions)
    relevant_tickers = {
        material for material, professions in material_to_professions.items()
        if profession_name in professions
    }
    
    # Filter dataframe to only these materials
    prof_df = df[df['Ticker'].isin(relevant_tickers)].copy()
    
    if prof_df.empty:
        return section_header(f"{profession_name} - NO DATA", 8) + [[""]*8]
    
    # Sort by profit or ROI
    if 'Profit per Unit' in prof_df.columns:
        prof_df['SortProfit'] = pd.to_numeric(prof_df['Profit per Unit'], errors='coerce').fillna(0)
    elif 'Profit_Ask' in prof_df.columns:
        prof_df['SortProfit'] = pd.to_numeric(prof_df['Profit_Ask'], errors='coerce').fillna(0)
    else:
        prof_df['SortProfit'] = 0
    
    # Show ALL materials (sorted by profit), not just top N
    prof_df = prof_df.sort_values('SortProfit', ascending=False)
    
    subheader = ["Ticker", "Name", "Recipe", "Building", "Buy Price", "Input Cost", "Profit", "ROI %", "Investment Score"]
    rows = []
    for _, row in prof_df.iterrows():
        ticker = row.get('Ticker', '')
        recipe = row.get('Recipe', 'N/A')
        building = row.get('Building', 'N/A')
        
        # Convert to string and handle NaN
        if pd.isna(recipe) or recipe is None or recipe == '':
            recipe = 'N/A'
        else:
            recipe = str(recipe)
        
        if pd.isna(building) or building is None or building == '':
            building = 'N/A'
        else:
            building = str(building)
        
        profit = row.get('Profit per Unit', row.get('Profit_Ask', 0))
        roi = row.get('ROI Ask %', row.get('ROI_Ask', 0))
        
        rows.append([
            ticker,
            row.get('Material Name', row.get('Name', ticker)),
            recipe[:30] if len(recipe) > 30 else recipe,
            building,
            f"{row.get('Ask_Price', row.get('Ask Price', 0)):,.2f}",
            f"{row.get('Input Cost per Unit', 0):,.2f}",
            f"{profit:,.2f}",
            f"{roi:,.2f}",
            f"{row.get('Investment Score', row.get('Investment_Score', 0)):,.2f}"
        ])
    
    return section_header(profession_name, len(subheader)) + [subheader] + rows + [[""] * len(subheader)]

if __name__ == "__main__":
    main()