import pandas as pd
from pathlib import Path
import sys
import time

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

def arbitrage_section(all_df, exch, top_n=20, orders_df=None):
    rows = []
    subheader = [
        "Ticker", "Name", "Product", "Buy Price", "Sell Price", "Profit",
        "Buy Exchange", "Sell Exchange", "ROI", "Opportunity Size", "Opportunity Level"
    ]
    if orders_df is not None:
        for ticker in orders_df['Ticker'].unique():
            ticker_orders = orders_df[orders_df['Ticker'] == ticker]
            for buy_exch in ticker_orders['Exchange'].unique():
                buy_orders = ticker_orders[(ticker_orders['Exchange'] == buy_exch) & (ticker_orders['Type'] == 'Ask')]
                if buy_orders.empty:
                    continue
                for sell_exch in ticker_orders['Exchange'].unique():
                    if sell_exch == buy_exch:
                        continue
                    sell_orders = ticker_orders[(ticker_orders['Exchange'] == sell_exch) & (ticker_orders['Type'] == 'Bid')]
                    if sell_orders.empty:
                        continue
                    # Sort buy asks ascending, sell bids descending
                    buy_orders_sorted = buy_orders.sort_values('Price')
                    sell_orders_sorted = sell_orders.sort_values('Price', ascending=False)
                    buy_idx, sell_idx = 0, 0
                    total_units = 0
                    total_profit = 0
                    total_cost = 0
                    while buy_idx < len(buy_orders_sorted) and sell_idx < len(sell_orders_sorted):
                        buy_row = buy_orders_sorted.iloc[buy_idx]
                        sell_row = sell_orders_sorted.iloc[sell_idx]
                        buy_price = buy_row['Price']
                        sell_price = sell_row['Price']
                        if sell_price <= buy_price:
                            break
                        units = min(buy_row['Available'], sell_row['Available'])
                        profit = (sell_price - buy_price) * units
                        total_units += units
                        total_profit += profit
                        total_cost += buy_price * units
                        buy_orders_sorted.at[buy_row.name, 'Available'] -= units
                        sell_orders_sorted.at[sell_row.name, 'Available'] -= units
                        if buy_orders_sorted.at[buy_row.name, 'Available'] == 0:
                            buy_idx += 1
                        if sell_orders_sorted.at[sell_row.name, 'Available'] == 0:
                            sell_idx += 1
                    if total_units > 0 and (buy_exch == exch or sell_exch == exch):
                        avg_buy = total_cost / total_units if total_units else 0
                        avg_sell = (total_profit + total_cost) / total_units if total_units else 0
                        avg_roi = (avg_sell - avg_buy) / avg_buy * 100 if avg_buy else 0
                        opp_level = "High" if total_units > 1000 else "Medium" if total_units > 100 else "Low"
                        rows.append([
                            ticker,
                            buy_row.get('Material Name', ticker),
                            buy_row.get('Product', ''),
                            f"{avg_buy:,.2f}",
                            f"{avg_sell:,.2f}",
                            f"{total_profit:,.2f}",
                            buy_exch,
                            sell_exch,
                            f"{avg_roi:.2f}%",
                            int(total_units),
                            opp_level
                        ])
    else:
        # fallback to summary data (current logic)
        tickers = all_df['Ticker'].unique()
        for ticker in tickers:
            ticker_rows = all_df[all_df['Ticker'] == ticker]
            valid_rows = ticker_rows.dropna(subset=['Ask Price', 'Bid Price', 'Exchange', 'Supply', 'Demand'])
            if valid_rows.empty:
                continue
            for buy_exch in valid_rows['Exchange'].unique():
                buy_row = valid_rows[valid_rows['Exchange'] == buy_exch].iloc[0]
                buy_price = buy_row['Ask Price']
                buy_available = buy_row['Supply'] if 'Supply' in buy_row else 0
                if pd.isna(buy_price) or buy_price <= 0 or pd.isna(buy_available) or buy_available <= 0:
                    continue
                for sell_exch in valid_rows['Exchange'].unique():
                    if sell_exch == buy_exch:
                        continue
                    sell_row = valid_rows[valid_rows['Exchange'] == sell_exch].iloc[0]
                    sell_price = sell_row['Bid Price']
                    sell_available = sell_row['Demand'] if 'Demand' in sell_row else 0
                    if pd.isna(sell_price) or sell_price <= 0 or pd.isna(sell_available) or sell_available <= 0:
                        continue
                    profit = sell_price - buy_price
                    roi = (profit / buy_price) * 100 if buy_price else 0
                    # Only require profit > 0, remove ROI filter
                    if profit > 0 and (buy_exch == exch or sell_exch == exch):
                        opportunity_size = min(buy_available, sell_available)
                        if opportunity_size > 1000:
                            opp_level = "High"
                        elif opportunity_size > 100:
                            opp_level = "Medium"
                        else:
                            opp_level = "Low"
                        rows.append([
                            ticker,
                            buy_row['Material Name'],
                            buy_row.get('Product', ''),
                            f"{buy_price:,.2f}",
                            f"{sell_price:,.2f}",
                            f"{profit:,.2f}",
                            buy_exch,
                            sell_exch,
                            f"{roi:.2f}%",
                            int(opportunity_size),
                            opp_level
                        ])
                        print(f"Checking {ticker} buy@{buy_exch} {buy_price} (supply={buy_available}) sell@{sell_exch} {sell_price} (demand={sell_available}) profit={profit}")
    print(f"[DEBUG] Arbitrage rows for {exch}: {len(rows)}")
    # Sort by profit descending and limit to top_n
    rows = sorted(rows, key=lambda x: float(x[5].replace(',', '')), reverse=True)[:top_n]
    while len(subheader) < len(REPORT_COLUMNS):
        subheader.append("")
    return section_header("Arbitrage Opportunities") + [subheader] + rows + [[""] * len(subheader)]

def buy_vs_produce_section(df, exch, top_n=20):
    rows = []
    subheader = ["Name", "Ticker", "Buy Price", "Produce Cost", "Difference", "Recommendation", "Level", "Trend"]
    for _, row in df.iterrows():
        buy_price = row['Ask Price']
        produce_cost = row['Input Cost per Unit']
        diff = buy_price - produce_cost
        # Recommendation logic
        if diff < -100:  # Buy is much cheaper
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
        trend = "Unknown"  # You can add logic for trend if you have historical data
        rows.append([
            row['Material Name'],
            row['Ticker'],
            f"{buy_price:,.2f}",
            f"{produce_cost:,.2f}",
            f"{diff:,.2f}",
            rec,
            level,
            trend
        ])
    # Sort by abs(diff) descending and take top_n
    rows = sorted(rows, key=lambda x: abs(float(x[4].replace(',', ''))), reverse=True)[:top_n]
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

def build_report_tab(df, exch, all_df, orders_df=None):
    report_rows = []
    report_rows += summary_section(df)
    report_rows += arbitrage_section(all_df, exch, orders_df=orders_df)
    report_rows += buy_vs_produce_section(all_df, exch)
    report_rows += top_invest_section(df, exch)
    report_rows += bottleneck_section(df, exch)
    return pd.DataFrame(report_rows, columns=REPORT_COLUMNS)

def apply_report_tab_formatting(sheets_manager, sheet_name, df):
    """
    Apply color formatting to section headers and recommendation cells in the report tab.
    Also clears all formatting before applying new formatting to avoid legacy/stray formats.
    """
    from googleapiclient.errors import HttpError

    # Get sheet ID
    sheet_id = sheets_manager._get_sheet_id(sheet_name)
    requests = []

    # --- 0. Clear all formatting first ---
    requests.append({
        "updateCells": {
            "range": {
                "sheetId": sheet_id
            },
            "fields": "userEnteredFormat"
        }
    })

    # Define section header colors (RGB 0-1)
    section_colors = [
        {"red": 0.2, "green": 0.4, "blue": 0.8},   # Summary - blue
        {"red": 0.2, "green": 0.7, "blue": 0.2},   # Arbitrage - green
        {"red": 1.0, "green": 0.8, "blue": 0.2},   # Buy vs Produce - yellow
        {"red": 0.85, "green": 0.6, "blue": 0.15}, # Top Invest - orange
        {"red": 0.8, "green": 0.2, "blue": 0.2},   # Bottlenecks - red
    ]
    section_names = [
        "SUMMARY", "ARBITRAGE OPPORTUNITIES", "BUY VS PRODUCE",
        "TOP 20 MATERIALS TO INVEST IN", "CHOKEPOINTS/BOTTLENECKS"
    ]
    section_rows = []
    for idx, row in enumerate(df.values):
        val = str(row[0]).strip().upper()
        if val in section_names:
            section_rows.append((idx, section_names.index(val)))

    # Only format the first cell of the section header row (not the whole row)
    for row_idx, color_idx in section_rows:
        color = section_colors[color_idx]
        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": row_idx + 1,  # +1 for 1-based index in Sheets
                    "endRowIndex": row_idx + 2,
                    "startColumnIndex": 0,
                    "endColumnIndex": 1  # Only the first column
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": color,
                        "textFormat": {"bold": True, "fontSize": 12, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                        "horizontalAlignment": "LEFT"
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
            }
        })

    # Find "Recommendation" column for Buy vs Produce section
    rec_col = None
    subheader_row = None
    for idx, row in enumerate(df.values):
        if str(row[0]).strip().upper() == "BUY VS PRODUCE":
            subheader_row = idx + 1
            for col_idx, col_name in enumerate(df.iloc[subheader_row]):
                if str(col_name).strip().lower() == "recommendation":
                    rec_col = col_idx
            break

    # Find rows with recommendations to color
    rec_rows = []
    if rec_col is not None and subheader_row is not None:
        for idx, row in enumerate(df.values):
            if idx > subheader_row and row[rec_col] in ("Buy", "Produce", "Neutral", "Depends"):
                rec_rows.append((idx, row[rec_col]))

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

def main():
    if not ENHANCED_FILE.exists():
        print(f"❌ Enhanced analysis file missing: {ENHANCED_FILE}")
        sys.exit(1)
    all_df = pd.read_csv(ENHANCED_FILE)
    ORDERS_FILE = CACHE_DIR / "orders.csv"
    orders_df = None
    if ORDERS_FILE.exists():
        orders_df = pd.read_csv(ORDERS_FILE)
        # Ensure correct column names
        orders_df = orders_df.rename(columns={
            'materialTicker': 'Ticker',
            'exchangeCode': 'Exchange',
            'orderType': 'Type',
            'price': 'Price',
            'available': 'Available'
        })
    else:
        print(f"⚠️ orders.csv not found at {ORDERS_FILE}")
    sheets = SheetsManager()
    for exch, tab in zip(EXCHANGES, REPORT_TABS):
        exch_df = all_df[all_df['Exchange'] == exch] if 'Exchange' in all_df.columns else all_df
        print(f"[DEBUG] {tab}: {len(exch_df)} rows")
        report_df = build_report_tab(exch_df, exch, all_df, orders_df=orders_df)
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