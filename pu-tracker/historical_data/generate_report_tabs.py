import pandas as pd
from pathlib import Path
import sys
import time
import concurrent.futures

try:
    from sheets_manager import UnifiedSheetsManager as SheetsManager
except ImportError:
    from sheets_manager import SheetsManager

EXCHANGES = ['AI1', 'CI1', 'CI2', 'IC1', 'NC1', 'NC2']
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
        ["Average Profit", f"{df[profit_col].mean():,.2f}" if profit_col in df else "", "", ""],
        ["Average ROI", f"{df[roi_col].mean():.2f}%" if roi_col in df else "", "", ""],
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
    all_tickers = df['Ticker'].unique()
    rows = []
    subheader = ["Name", "Ticker", "Buy Price", "Produce Cost", "Difference", "Recommendation", "Level", "Trend"]
    for ticker in all_tickers:
        ticker_rows = df[df['Ticker'] == ticker]
        if ticker_rows.empty:
            continue  # <-- skip if no rows for this ticker
        exch_rows = ticker_rows[ticker_rows['Exchange'] == exch] if 'Exchange' in ticker_rows.columns else ticker_rows
        if not exch_rows.empty:
            row = exch_rows.iloc[0]
        else:
            row = ticker_rows.iloc[0]
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
        # Optionally, comment out this filter to show all tickers:
        # if not buy_price or buy_price == 0:
        #     continue
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
        trend = "Unknown"
        rows.append([
            row.get('Material Name', ticker),
            ticker,
            f"{buy_price:,.2f}" if buy_price else "0",
            f"{produce_cost:,.2f}" if produce_cost else "0",
            f"{diff:,.2f}" if not pd.isna(diff) else "0",
            rec,
            level,
            trend
        ])
    def sort_key(x):
        rec_order = {"Buy": 0, "Produce": 1, "Neutral": 2, "Depends": 3}
        rec = x[5]
        try:
            diff_val = abs(float(x[4].replace(',', ''))) if x[4] != "N/A" else 0
        except Exception:
            diff_val = 0
        return (rec_order.get(rec, 99), -diff_val)
    rows = sorted(rows, key=sort_key)
    return section_header("Buy vs Produce", len(subheader)) + [subheader] + rows + [[""] * len(subheader)]

def top_invest_section(df, exch, top_n=20):
    df = df.copy()
    # Use Bid/Ask for profit if available
    if "Buy Price" not in df.columns and "Ask_Price" in df.columns:
        df["Buy Price"] = df["Ask_Price"]
    if "Sell Price" not in df.columns and "Bid_Price" in df.columns:
        df["Sell Price"] = df["Bid_Price"]
    # Use Bid/Ask profit if possible
    if "Bid_Price" in df.columns and "Ask_Price" in df.columns:
        df["Profit"] = df["Bid_Price"] - df["Ask_Price"]
    elif "Sell Price" in df.columns and "Buy Price" in df.columns:
        df["Profit"] = df["Sell Price"] - df["Buy Price"]
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

    if filtered.empty:
        return section_header("CHOKEPOINTS/BOTTLENECKS", 10) + [[""] * 10]

    # Compute Chokepoint Type and Level
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

    # Sort by Chokepoint Type, then Level (High > Medium > Low)
    level_order = {"High": 0, "Medium": 1, "Low": 2}
    filtered["LevelSort"] = filtered["Level"].map(level_order)
    filtered = filtered.sort_values(["Chokepoint Type", "LevelSort"])
    subheader = [
        "Ticker", "Name", "Product", "Buy Price", "Sell Price", "Profit",
        "Supply", "Demand", "Chokepoint Type", "Level"
    ]
    rows = []
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

    max_rows = max(len(summary), len(arbitrage), len(buy_vs_produce), len(top_invest), len(bottleneck), len(top_traded))

    summary = pad_section(summary, max_rows, len(summary[0]))
    arbitrage = pad_section(arbitrage, max_rows, len(arbitrage[0]))
    buy_vs_produce = pad_section(buy_vs_produce, max_rows, len(buy_vs_produce[0]))
    top_invest = pad_section(top_invest, max_rows, len(top_invest[0]))
    bottleneck = pad_section(bottleneck, max_rows, len(bottleneck[0]))
    top_traded = pad_section(top_traded, max_rows, len(top_traded[0]))

    # Debug: print section shapes
    print("Section shapes:")
    print("  summary:", len(summary[0]), "cols")
    print("  arbitrage:", len(arbitrage[0]), "cols")
    print("  buy_vs_produce:", len(buy_vs_produce[0]), "cols")
    print("  top_invest:", len(top_invest[0]), "cols")
    print("  bottleneck:", len(bottleneck[0]), "cols")
    print("  top_traded:", len(top_traded[0]), "cols")

    summary_df = pd.DataFrame(summary)
    arbitrage_df = pd.DataFrame(arbitrage)
    buy_vs_produce_df = pd.DataFrame(buy_vs_produce)
    top_invest_df = pd.DataFrame(top_invest)
    bottleneck_df = pd.DataFrame(bottleneck)
    top_traded_df = pd.DataFrame(top_traded)

    report_df = pd.concat(
        [summary_df, arbitrage_df, buy_vs_produce_df, top_invest_df, bottleneck_df, top_traded_df],
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
        ("BUY VS PRODUCE", {"red": 1.0, "green": 0.8, "blue": 0.2}, 8),
        ("TOP MATERIALS TO INVEST IN", {"red": 0.85, "green": 0.6, "blue": 0.15}, 7),
        ("CHOKEPOINTS/BOTTLENECKS", {"red": 0.8, "green": 0.2, "blue": 0.2}, 10),  # <-- was 9
        ("TOP TRADED PRODUCTS", {"red": 0.5, "green": 0.2, "blue": 0.7}, 2),
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
        for val, color in [("High", {"red": 0.8, "green": 0.2, "blue": 0.2}),
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
                            "format": {"backgroundColor": color, "textFormat": {"bold": True}}
                        }
                    },
                    "index": 0
                }
            })

    # Chokepoints: Chokepoint Type (distinct color for each type)
    bottleneck_type_col = find_col_idx(section_starts, "CHOKEPOINTS/BOTTLENECKS", "Chokepoint Type")
    if bottleneck_type_col is not None:
        type_colors = {
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
                            "format": {"backgroundColor": color, "textFormat": {"bold": True}}
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

    print(f"[DEBUG] Arbitrage DataFrame rows: {len(arbitrage_df)}")
    print(arbitrage_df.head())
    print(arbitrage_df[['Ticker', 'Buy Exchange', 'Sell Exchange', 'Opportunity Size']].sort_values('Opportunity Size', ascending=False).head(20))
    print(arbitrage_df[['Ticker', 'Buy Exchange', 'Sell Exchange', 'Opportunity Size']].sort_values('Opportunity Size', ascending=False).head(20))
    # After generating the main report and before finishing, add the new section:

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

if __name__ == "__main__":
    main()