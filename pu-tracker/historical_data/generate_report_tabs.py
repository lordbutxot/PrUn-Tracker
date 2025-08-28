import pandas as pd
from pathlib import Path
import sys
import time
import math

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

def section_header(title):
    return [[title.upper()] + [""] * (len(REPORT_COLUMNS) - 1)]

def summary_section(df):
    total_arbitrage = len(df[df['Profit per Unit'] > 0])
    avg_profit = df['Profit per Unit'].mean()
    avg_roi = df['ROI Ask %'].mean()
    high_risk = (df['Risk Level'] == 'High').sum()
    rows = [
        ["Key", "Value"] + [""] * (len(REPORT_COLUMNS) - 2),
        ["Total Arbitrage Opportunities", total_arbitrage] + [""] * (len(REPORT_COLUMNS) - 2),
        ["Avg Profit", f"${avg_profit:,.2f}"] + [""] * (len(REPORT_COLUMNS) - 2),
        ["Avg ROI", f"{avg_roi:.2f}%"] + [""] * (len(REPORT_COLUMNS) - 2),
        ["High Risk Products", high_risk] + [""] * (len(REPORT_COLUMNS) - 2),
        [""] * len(REPORT_COLUMNS)
    ]
    return section_header("Summary") + rows

def arbitrage_section(arbitrage_df, exch, top_n=None, orders_df=None):
    """
    List all arbitrage opportunities for the given exchange.
    Includes all opportunities with profit > 0, sorted by level and size.
    Adds a subheader row.
    """
    df = arbitrage_df[arbitrage_df['Buy Exchange'] == exch].copy()
    df = df[df['Profit'] > 0]
    level_order = {'Very High': 0, 'High': 1, 'Medium': 2, 'Low': 3, 'Very Low': 4}
    df['LevelSort'] = df['Opportunity Level'].map(level_order).fillna(99)
    df = df.sort_values(['LevelSort', 'Opportunity Size'], ascending=[True, False])
    df = df.drop(columns=['LevelSort'])
    # Format numeric columns for display, but leave ROI as number for conditional formatting
    for col in ["Buy Price", "Sell Price", "Profit"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: f"{x:,.2f}" if pd.notna(x) else "0")
    # Do NOT format ROI as string; keep as float
    subheader = REPORT_COLUMNS
    rows = df[REPORT_COLUMNS].values.tolist()
    return section_header("Arbitrage Opportunities") + [subheader] + rows + [[""] * len(subheader)]

def buy_vs_produce_section(df, exch, top_n=None):
    all_tickers = df['Ticker'].unique()
    rows = []
    subheader = ["Name", "Ticker", "Buy Price", "Produce Cost", "Difference", "Recommendation", "Level", "Trend"]
    for ticker in all_tickers:
        ticker_rows = df[df['Ticker'] == ticker]
        row = ticker_rows[ticker_rows['Exchange'] == exch].iloc[0] if 'Exchange' in ticker_rows.columns and not ticker_rows[ticker_rows['Exchange'] == exch].empty else ticker_rows.iloc[0]
        buy_price = row.get('Ask Price', 0) if not pd.isna(row.get('Ask Price', 0)) else 0
        produce_cost = row.get('Input Cost per Unit', 0) if not pd.isna(row.get('Input Cost per Unit', 0)) else 0
        diff = buy_price - produce_cost
        # Recommendation logic
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
    # Custom sort: Buy (by abs(diff) desc), then Produce (by abs(diff) desc), then Neutral, then Depends
    def sort_key(x):
        rec_order = {"Buy": 0, "Produce": 1, "Neutral": 2, "Depends": 3}
        rec = x[5]
        try:
            diff_val = abs(float(x[4].replace(',', ''))) if x[4] != "N/A" else 0
        except Exception:
            diff_val = 0
        return (rec_order.get(rec, 99), -diff_val)
    rows = sorted(rows, key=sort_key)
    return section_header("Buy vs Produce") + [subheader] + rows + [[""] * len(subheader)]

def top_invest_section(df, exch, top_n=20):
    top_invest = df.sort_values("Investment Score", ascending=False).head(top_n)
    subheader = ["Ticker", "Name", "Product", "Buy Price", "Sell Price", "Profit", "Buy Exchange", "Sell Exchange", "Investment Score"]
    rows = []
    for _, row in top_invest.iterrows():
        rows.append([
            row['Ticker'],
            row['Material Name'],
            row.get('Product', ''),
            f"{row['Ask Price']:,.2f}",
            f"{row['Bid Price']:,.2f}",
            f"{row['Profit per Unit']:,.2f}",
            exch, exch,
            f"{row['Investment Score']:,.2f}"
        ])
    return section_header("Top 20 Materials to Invest In") + [subheader] + rows + [[""] * len(REPORT_COLUMNS)]

def bottleneck_section(df, exch, top_n=20):
    bottlenecks = df[(df['Supply'] < 100) & (df['Demand'] > 500)].sort_values("Demand", ascending=False).head(top_n)
    subheader = ["Ticker", "Name", "Product", "Buy Price", "Sell Price", "Profit", "Buy Exchange", "Sell Exchange", "Demand"]
    rows = []
    for _, row in bottlenecks.iterrows():
        rows.append([
            row['Ticker'],
            row['Material Name'],
            row.get('Product', ''),
            f"{row['Ask Price']:,.2f}",
            f"{row['Bid Price']:,.2f}",
            f"{row['Profit per Unit']:,.2f}",
            exch, exch,
            f"{row['Demand']:,.0f}"
        ])
    return section_header("Chokepoints/Bottlenecks") + [subheader] + rows + [[""] * len(REPORT_COLUMNS)]

def pad_section(section, n_rows):
    """Pad section (list of lists) to n_rows with empty rows."""
    width = len(section[0])
    while len(section) < n_rows:
        section.append([""] * width)
    return section

def build_report_tab(df, exch, arbitrage_df, all_df, orders_df=None):
    # Build each section as a list of lists
    summary = summary_section(df)
    arbitrage = arbitrage_section(arbitrage_df, exch, orders_df=orders_df)
    buy_vs_produce = buy_vs_produce_section(all_df, exch)
    top_invest = top_invest_section(df, exch)
    bottleneck = bottleneck_section(df, exch)

    # Find the max number of rows among all sections
    max_rows = max(len(summary), len(arbitrage), len(buy_vs_produce), len(top_invest), len(bottleneck))

    # Pad each section to the same number of rows
    summary = pad_section(summary, max_rows)
    arbitrage = pad_section(arbitrage, max_rows)
    buy_vs_produce = pad_section(buy_vs_produce, max_rows)
    top_invest = pad_section(top_invest, max_rows)
    bottleneck = pad_section(bottleneck, max_rows)

    # Convert each to DataFrame
    summary_df = pd.DataFrame(summary)
    arbitrage_df = pd.DataFrame(arbitrage)
    buy_vs_produce_df = pd.DataFrame(buy_vs_produce)
    top_invest_df = pd.DataFrame(top_invest)
    bottleneck_df = pd.DataFrame(bottleneck)

    # Concatenate horizontally
    report_df = pd.concat(
        [summary_df, arbitrage_df, buy_vs_produce_df, top_invest_df, bottleneck_df],
        axis=1
    )
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
        ("SUMMARY", {"red": 0.2, "green": 0.4, "blue": 0.8}, len(REPORT_COLUMNS)),
        ("ARBITRAGE OPPORTUNITIES", {"red": 0.2, "green": 0.7, "blue": 0.2}, len(REPORT_COLUMNS)),
        ("BUY VS PRODUCE", {"red": 1.0, "green": 0.8, "blue": 0.2}, 8),
        ("TOP 20 MATERIALS TO INVEST IN", {"red": 0.85, "green": 0.6, "blue": 0.15}, len(REPORT_COLUMNS)),
        ("CHOKEPOINTS/BOTTLENECKS", {"red": 0.8, "green": 0.2, "blue": 0.2}, len(REPORT_COLUMNS)),
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
        print(f"⚠️  'Recommendation' column not found in Buy vs Produce section for {sheet_name}, skipping recommendation formatting.")

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

    # 5. Top 20 Materials: Investment Score (yellow to green gradient)
    invest_score_col = find_col_idx(section_starts, "TOP 20 MATERIALS TO INVEST IN", "Investment Score")
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

    # Send batchUpdate request
    if requests:
        try:
            sheets_manager.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=sheets_manager.spreadsheet_id,
                body={"requests": requests}
            ).execute()
            print(f"🎨 Formatting applied to {sheet_name}")
        except HttpError as e:
            print(f"⚠️ Formatting failed for {sheet_name}: {e}")

def compute_arbitrage_opportunities(df, orders_df=None):
    arbitrage_rows = []
    exchanges = df['Exchange'].unique()
    for ticker in df['Ticker'].unique():
        mat_rows = df[df['Ticker'] == ticker]
        for buy_ex in exchanges:
            buy_row = mat_rows[mat_rows['Exchange'] == buy_ex]
            if buy_row.empty:
                continue
            buy_price = buy_row.iloc[0].get('Ask Price', None)
            buy_supply = buy_row.iloc[0].get('Supply', 0)
            name = buy_row.iloc[0].get('Material Name', ticker)
            product = buy_row.iloc[0].get('Product', '')
            if pd.isna(buy_price) or buy_price == 0:
                continue
            for sell_ex in exchanges:
                if sell_ex == buy_ex:
                    continue
                sell_row = mat_rows[mat_rows['Exchange'] == sell_ex]
                if sell_row.empty:
                    continue
                sell_price = sell_row.iloc[0].get('Bid Price', None)
                sell_demand = sell_row.iloc[0].get('Demand', 0)
                if pd.isna(sell_price) or sell_price == 0:
                    continue
                profit = sell_price - buy_price
                if profit > 0:
                    roi = (profit / buy_price) * 100 if buy_price else 0
                    # Use order book if available
                    if orders_df is not None:
                        opportunity_size = get_arbitrage_opportunity_size(
                            ticker, buy_ex, sell_ex, orders_df
                        )
                    else:
                        try:
                            opportunity_size = int(min(float(buy_supply), float(sell_demand)))
                        except Exception:
                            opportunity_size = 0
                    if opportunity_size > 0:
                        # Simple opportunity level
                        if profit > 10000:
                            level = "Very High"
                        elif profit > 1000:
                            level = "High"
                        elif profit > 100:
                            level = "Medium"
                        elif profit > 10:
                            level = "Low"
                        else:
                            level = "Very Low"
                        arbitrage_rows.append([
                            ticker, name, product,
                            buy_price, sell_price, profit,
                            buy_ex, sell_ex, roi, opportunity_size, level
                        ])
    columns = [
        "Ticker", "Name", "Product", "Buy Price", "Sell Price", "Profit",
        "Buy Exchange", "Sell Exchange", "ROI", "Opportunity Size", "Opportunity Level"
    ]
    return pd.DataFrame(arbitrage_rows, columns=columns)

def get_arbitrage_opportunity_size(ticker, buy_ex, sell_ex, orders_df, min_profit_per_unit=0):
    """
    Simulate order book: buy at asks, sell at bids, stop when profit per unit <= min_profit_per_unit.
    Only count units where bid > ask (after fees if needed).
    """
    print(f"Calculating opportunity size for {ticker} from {buy_ex} to {sell_ex}")
    asks = orders_df[(orders_df['Ticker'] == ticker) & (orders_df['Exchange'] == buy_ex) & (orders_df['Side'] == 'ask')].copy()
    bids = orders_df[(orders_df['Ticker'] == ticker) & (orders_df['Exchange'] == sell_ex) & (orders_df['Side'] == 'bid')].copy()
    asks = asks.sort_values('Price').reset_index(drop=True)
    bids = bids.sort_values('Price', ascending=False).reset_index(drop=True)
    ask_idx, bid_idx = 0, 0
    total_size = 0

    print("Asks:", asks)
    print("Bids:", bids)

    while ask_idx < len(asks) and bid_idx < len(bids):
        ask_price = asks.at[ask_idx, 'Price']
        bid_price = bids.at[bid_idx, 'Price']
        # Only trade if profitable
        profit_per_unit = bid_price - ask_price
        if profit_per_unit < min_profit_per_unit:
            break
        # Trade up to the minimum available
        trade_qty = min(asks.at[ask_idx, 'Quantity'], bids.at[bid_idx, 'Quantity'])
        total_size += trade_qty
        # Decrement quantities
        asks.at[ask_idx, 'Quantity'] -= trade_qty
        bids.at[bid_idx, 'Quantity'] -= trade_qty
        # Move to next order if depleted
        if asks.at[asks.index[ask_idx], 'Quantity'] == 0:
            ask_idx += 1
        if bids.at[bids.index[bid_idx], 'Quantity'] == 0:
            bid_idx += 1
    return total_size

def get_weighted_avg_price(orders_df, ticker, exchange, side, quantity):
    """
    Simulate buying/selling up to 'quantity' units at best available prices.
    side: 'ask' for buying, 'bid' for selling
    """
    book = orders_df[(orders_df['Ticker'] == ticker) & (orders_df['Exchange'] == exchange)]
    book = book[book['Side'] == side].sort_values('Price', ascending=(side == 'ask'))
    total_qty = 0
    total_cost = 0
    for _, row in book.iterrows():
        avail = min(row['Quantity'], quantity - total_qty)
        total_cost += avail * row['Price']
        total_qty += avail
        if total_qty >= quantity:
            break
    return total_cost / total_qty if total_qty else None

def assign_opportunity_level(df):
    """
    Assigns opportunity level based on composite score of ROI, size, volatility, and risk.
    """
    # Normalize columns (min-max scaling)
    df['ROI_norm'] = (df['ROI'] - df['ROI'].min()) / (df['ROI'].max() - df['ROI'].min())
    df['Size_norm'] = (df['Opportunity Size'] - df['Opportunity Size'].min()) / (df['Opportunity Size'].max() - df['Opportunity Size'].min())
    df['Volatility_norm'] = 1 - ((df['Volatility'] - df['Volatility'].min()) / (df['Volatility'].max() - df['Volatility'].min()))
    df['Risk_norm'] = df['Risk Level'].map({'Low': 1, 'Medium': 0.5, 'High': 0}).fillna(0.5)
    # Composite score (adjust weights as needed)
    df['Score'] = 0.5 * df['ROI_norm'] + 0.3 * df['Size_norm'] + 0.1 * df['Volatility_norm'] + 0.1 * df['Risk_norm']
    # Assign levels by percentiles
    df['Opportunity Level'] = pd.qcut(df['Score'], q=5, labels=['Very Low', 'Low', 'Medium', 'High', 'Very High'])
    return df

def main():
    if not ENHANCED_FILE.exists():
        print(f"[FATAL] Enhanced analysis file not found: {ENHANCED_FILE}")
        return
    all_df = pd.read_csv(ENHANCED_FILE)
    # Compute arbitrage DataFrame
    arbitrage_df = compute_arbitrage_opportunities(all_df)
    ORDERS_FILE = CACHE_DIR / "orders.csv"
    orders_df = None
    if ORDERS_FILE.exists():
        orders_df = pd.read_csv(ORDERS_FILE)
    else:
        print(f"⚠️ orders.csv not found at {ORDERS_FILE}")
    sheets = SheetsManager()
    for exch, tab in zip(EXCHANGES, REPORT_TABS):
        exch_df = all_df[all_df['Exchange'] == exch] if 'Exchange' in all_df.columns else all_df
        print(f"[DEBUG] {tab}: {len(exch_df)} rows")
        report_df = build_report_tab(exch_df, exch, arbitrage_df, all_df, orders_df=orders_df)
        print(f"[DEBUG] {tab} report_df: {len(report_df)} rows")
        upload_df_method = getattr(sheets, "upload_dataframe_to_sheet", None)
        upload_sheet_method = getattr(sheets, "upload_to_sheet", None)
        if callable(upload_df_method):
            upload_df_method(tab, report_df)
        elif callable(upload_sheet_method):
            upload_sheet_method(SPREADSHEET_ID, tab, report_df)
        else:
            print("❌ No valid upload method found in SheetsManager")
        apply_report_tab_formatting(sheets, tab, report_df)
        time.sleep(2)

if __name__ == "__main__":
    main()