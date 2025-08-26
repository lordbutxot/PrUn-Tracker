"""
Ultra-optimized upload system for ALL exchanges
Extends the optimization to handle AI1, CI1, CI2, NC1, NC2, IC1 efficiently
Uses minimal API calls and smart batching to avoid 429 errors
"""
import time
import pandas as pd
import gspread
from gspread.utils import rowcol_to_a1

class UltraOptimizedUploader:
    def __init__(self, credentials_file, spreadsheet_id):
        self.gc = gspread.service_account(filename=credentials_file)
        self.spreadsheet = self.gc.open_by_key(spreadsheet_id)
        self.total_api_calls = 0
        self.upload_stats = {}
        
        # Define numeric columns that should be rounded to 3 decimals
        # NOTE: Weight and Volume are excluded to preserve precision for calculations
        self.numeric_columns = [
            'Current Price', 'Input Cost per Unit', 'Input Cost per Stack',
            'Profit per Unit', 'Profit per Stack', 'ROI %', 'Supply', 'Demand',
            'Traded Volume', 'Market Cap', 'Liquidity Ratio', 'Investment Score',
            'Volatility', 'Max Arbitrage Profit', 'Arbitrage ROI %', 'Confidence %',
            'Break-even Quantity', 'Production Time (hrs)', 'Total Production Cost'
        ]
        
        print(f"[Ultra] Connected to spreadsheet: {self.spreadsheet.title}")
    
    def format_numeric_value(self, value, column_name):
        """Format numeric values to 3 decimals for Google Sheets display"""
        try:
            if column_name in self.numeric_columns and value != '' and not pd.isna(value):
                # Convert to float and round to 3 decimals
                numeric_value = float(value)
                return round(numeric_value, 3)
            return value
        except (ValueError, TypeError):
            # If conversion fails, return original value
            return value
    
    def format_headers(self, worksheet, num_columns):
        """Format header row with bold text and background color"""
        try:
            # Format header row (row 1)
            end_col = chr(ord('A') + num_columns - 1)
            header_range = f"A1:{end_col}1"
            
            worksheet.format(header_range, {
                "backgroundColor": {"red": 0.8, "green": 0.8, "blue": 0.9},
                "textFormat": {"bold": True, "fontSize": 11},
                "horizontalAlignment": "CENTER"
            })
            
            self.total_api_calls += 1
            print(f"[Ultra] ✨ Header formatting applied")
            
        except Exception as e:
            print(f"[Ultra] ⚠️  Header formatting failed: {e}")
    
    def apply_simple_formatting(self, worksheet, available_columns, data_rows):
        """Apply simplified but reliable formatting to key columns"""
        try:
            print(f"[Ultra] 🎨 Applying simplified formatting...")
            print(f"[Ultra] Available columns: {available_columns}")
            
            # Find key columns and apply basic background colors
            for i, col in enumerate(available_columns):
                col_letter = chr(ord('A') + i)
                range_name = f"{col_letter}2:{col_letter}{data_rows + 1}"
                
                # More precise column matching
                if col.strip() == 'ROI %':
                    print(f"[Ultra] 🎯 Formatting ROI % column ({col_letter})")
                    worksheet.format(range_name, {
                        "backgroundColor": {"red": 0.9, "green": 1.0, "blue": 0.9},
                        "textFormat": {"bold": True}
                    })
                    self.total_api_calls += 1
                elif col.strip() == 'Profit per Unit':
                    print(f"[Ultra] 💰 Formatting Profit per Unit column ({col_letter})")
                    worksheet.format(range_name, {
                        "backgroundColor": {"red": 0.9, "green": 0.95, "blue": 1.0},
                        "textFormat": {"bold": True}
                    })
                    self.total_api_calls += 1
                elif col.strip() == 'Profit per Stack':
                    print(f"[Ultra] 💰 Formatting Profit per Stack column ({col_letter})")
                    worksheet.format(range_name, {
                        "backgroundColor": {"red": 0.9, "green": 0.95, "blue": 1.0},
                        "textFormat": {"bold": True}
                    })
                    self.total_api_calls += 1
                elif col.strip() == 'Investment Score':
                    print(f"[Ultra] 📊 Formatting Investment Score column ({col_letter})")
                    worksheet.format(range_name, {
                        "backgroundColor": {"red": 1.0, "green": 1.0, "blue": 0.9},
                        "textFormat": {"bold": True}
                    })
                    self.total_api_calls += 1
                elif col.strip() == 'Risk Level':
                    print(f"[Ultra] ⚠️ Formatting Risk Level column ({col_letter})")
                    worksheet.format(range_name, {
                        "backgroundColor": {"red": 1.0, "green": 0.95, "blue": 0.9},
                        "textFormat": {"bold": True}
                    })
                    self.total_api_calls += 1
            
            print(f"[Ultra] ✅ Simplified formatting applied successfully")
            
        except Exception as e:
            print(f"[Ultra] ⚠️  Simplified formatting failed: {e}")
            import traceback
            traceback.print_exc()
    
    def apply_conditional_formatting(self, worksheet, available_columns, data_rows):
        """Apply conditional formatting to DATA sheet columns"""
        try:
            print(f"[Ultra] 🎨 Applying conditional formatting...")
            
            # Find column indices for formatting
            formatting_columns = {}
            for i, col in enumerate(available_columns):
                col_letter = chr(ord('A') + i)
                if 'ROI %' in col:
                    formatting_columns['roi'] = col_letter
                elif 'Profit per Unit' in col:
                    formatting_columns['profit_unit'] = col_letter
                elif 'Profit per Stack' in col:
                    formatting_columns['profit_stack'] = col_letter
                elif 'Investment Score' in col:
                    formatting_columns['investment'] = col_letter
                elif 'Risk Level' in col:
                    formatting_columns['risk'] = col_letter
            
            # ROI % Formatting (4 levels)
            if 'roi' in formatting_columns:
                col = formatting_columns['roi']
                range_name = f"{col}2:{col}{data_rows + 1}"  # Skip header row
                
                # Negative ROI - Red
                worksheet.format(range_name, {
                    "backgroundColor": {"red": 1.0, "green": 0.8, "blue": 0.8},
                    "textFormat": {"bold": True}
                })
                
            # Apply conditional formatting rules
            requests = [
                {
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{"sheetId": worksheet.id, "startRowIndex": 1, "endRowIndex": data_rows + 1,
                                      "startColumnIndex": ord(col) - ord('A'), "endColumnIndex": ord(col) - ord('A') + 1}],
                            "booleanRule": {
                                "condition": {"type": "NUMBER_GREATER", "values": [{"userEnteredValue": "20"}]},
                                "format": {"backgroundColor": {"red": 0.7, "green": 1.0, "blue": 0.7}}  # High ROI - Green
                            }
                        },
                        "index": 0
                    }
                },
                {
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{"sheetId": worksheet.id, "startRowIndex": 1, "endRowIndex": data_rows + 1,
                                      "startColumnIndex": ord(col) - ord('A'), "endColumnIndex": ord(col) - ord('A') + 1}],
                            "booleanRule": {
                                "condition": {"type": "NUMBER_BETWEEN", "values": [{"userEnteredValue": "5"}, {"userEnteredValue": "20"}]},
                                "format": {"backgroundColor": {"red": 1.0, "green": 1.0, "blue": 0.7}}  # Medium ROI - Yellow
                            }
                        },
                        "index": 1
                    }
                },
                {
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{"sheetId": worksheet.id, "startRowIndex": 1, "endRowIndex": data_rows + 1,
                                      "startColumnIndex": ord(col) - ord('A'), "endColumnIndex": ord(col) - ord('A') + 1}],
                            "booleanRule": {
                                "condition": {"type": "NUMBER_LESS", "values": [{"userEnteredValue": "0"}]},
                                "format": {"backgroundColor": {"red": 1.0, "green": 0.6, "blue": 0.6}}  # Negative ROI - Red
                            }
                        },
                        "index": 2
                    }
                }
            ]
            
            # Apply the formatting
            self.spreadsheet.batch_update({"requests": requests})
            self.total_api_calls += 1            # Profit per Unit Formatting
            if 'profit_unit' in formatting_columns:
                col = formatting_columns['profit_unit']
                self._apply_profit_formatting(worksheet, col, data_rows)
            
            # Profit per Stack Formatting
            if 'profit_stack' in formatting_columns:
                col = formatting_columns['profit_stack']
                self._apply_profit_formatting(worksheet, col, data_rows)
            
            # Investment Score Formatting (Green to Red scale)
            if 'investment' in formatting_columns:
                col = formatting_columns['investment']
                self._apply_investment_score_formatting(worksheet, col, data_rows)
            
            # Risk Level Formatting
            if 'risk' in formatting_columns:
                col = formatting_columns['risk']
                self._apply_risk_level_formatting(worksheet, col, data_rows)
            
            print(f"[Ultra] ✅ Conditional formatting applied successfully")
            
        except Exception as e:
            print(f"[Ultra] ⚠️  Formatting failed: {e}")
            # Don't fail the entire upload if formatting fails
    
    def _apply_profit_formatting(self, worksheet, col, data_rows):
        """Apply profit-based conditional formatting (Red to Green)"""
        try:
            requests = [
                {
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{"sheetId": worksheet.id, "startRowIndex": 1, "endRowIndex": data_rows + 1,
                                      "startColumnIndex": ord(col) - ord('A'), "endColumnIndex": ord(col) - ord('A') + 1}],
                            "booleanRule": {
                                "condition": {"type": "NUMBER_GREATER", "values": [{"userEnteredValue": "100"}]},
                                "format": {"backgroundColor": {"red": 0.6, "green": 1.0, "blue": 0.6}}  # High profit - Green
                            }
                        },
                        "index": 0
                    }
                },
                {
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{"sheetId": worksheet.id, "startRowIndex": 1, "endRowIndex": data_rows + 1,
                                      "startColumnIndex": ord(col) - ord('A'), "endColumnIndex": ord(col) - ord('A') + 1}],
                            "booleanRule": {
                                "condition": {"type": "NUMBER_BETWEEN", "values": [{"userEnteredValue": "10"}, {"userEnteredValue": "100"}]},
                                "format": {"backgroundColor": {"red": 1.0, "green": 1.0, "blue": 0.7}}  # Medium profit - Yellow
                            }
                        },
                        "index": 1
                    }
                },
                {
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{"sheetId": worksheet.id, "startRowIndex": 1, "endRowIndex": data_rows + 1,
                                      "startColumnIndex": ord(col) - ord('A'), "endColumnIndex": ord(col) - ord('A') + 1}],
                            "booleanRule": {
                                "condition": {"type": "NUMBER_LESS", "values": [{"userEnteredValue": "0"}]},
                                "format": {"backgroundColor": {"red": 1.0, "green": 0.6, "blue": 0.6}}  # Negative profit - Red
                            }
                        },
                        "index": 2
                    }
                }
            ]
            
            self.spreadsheet.batch_update({"requests": requests})
            self.total_api_calls += 1
            
        except Exception as e:
            print(f"[Ultra] ⚠️  Profit formatting failed: {e}")
    
    def _apply_investment_score_formatting(self, worksheet, col, data_rows):
        """Apply Investment Score formatting (Green = Good, Red = Bad)"""
        try:
            requests = [
                {
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{"sheetId": worksheet.id, "startRowIndex": 1, "endRowIndex": data_rows + 1,
                                      "startColumnIndex": ord(col) - ord('A'), "endColumnIndex": ord(col) - ord('A') + 1}],
                            "booleanRule": {
                                "condition": {"type": "NUMBER_GREATER", "values": [{"userEnteredValue": "70"}]},
                                "format": {"backgroundColor": {"red": 0.6, "green": 1.0, "blue": 0.6}}  # High score - Green
                            }
                        },
                        "index": 0
                    }
                },
                {
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{"sheetId": worksheet.id, "startRowIndex": 1, "endRowIndex": data_rows + 1,
                                      "startColumnIndex": ord(col) - ord('A'), "endColumnIndex": ord(col) - ord('A') + 1}],
                            "booleanRule": {
                                "condition": {"type": "NUMBER_BETWEEN", "values": [{"userEnteredValue": "40"}, {"userEnteredValue": "70"}]},
                                "format": {"backgroundColor": {"red": 1.0, "green": 1.0, "blue": 0.7}}  # Medium score - Yellow
                            }
                        },
                        "index": 1
                    }
                },
                {
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{"sheetId": worksheet.id, "startRowIndex": 1, "endRowIndex": data_rows + 1,
                                      "startColumnIndex": ord(col) - ord('A'), "endColumnIndex": ord(col) - ord('A') + 1}],
                            "booleanRule": {
                                "condition": {"type": "NUMBER_LESS", "values": [{"userEnteredValue": "40"}]},
                                "format": {"backgroundColor": {"red": 1.0, "green": 0.6, "blue": 0.6}}  # Low score - Red
                            }
                        },
                        "index": 2
                    }
                }
            ]
            
            self.spreadsheet.batch_update({"requests": requests})
            self.total_api_calls += 1
            
        except Exception as e:
            print(f"[Ultra] ⚠️  Investment score formatting failed: {e}")
    
    def _apply_risk_level_formatting(self, worksheet, col, data_rows):
        """Apply Risk Level formatting based on text values"""
        try:
            requests = [
                {
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{"sheetId": worksheet.id, "startRowIndex": 1, "endRowIndex": data_rows + 1,
                                      "startColumnIndex": ord(col) - ord('A'), "endColumnIndex": ord(col) - ord('A') + 1}],
                            "booleanRule": {
                                "condition": {"type": "TEXT_CONTAINS", "values": [{"userEnteredValue": "Low"}]},
                                "format": {"backgroundColor": {"red": 0.6, "green": 1.0, "blue": 0.6}}  # Low risk - Green
                            }
                        },
                        "index": 0
                    }
                },
                {
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{"sheetId": worksheet.id, "startRowIndex": 1, "endRowIndex": data_rows + 1,
                                      "startColumnIndex": ord(col) - ord('A'), "endColumnIndex": ord(col) - ord('A') + 1}],
                            "booleanRule": {
                                "condition": {"type": "TEXT_CONTAINS", "values": [{"userEnteredValue": "Medium"}]},
                                "format": {"backgroundColor": {"red": 1.0, "green": 1.0, "blue": 0.7}}  # Medium risk - Yellow
                            }
                        },
                        "index": 1
                    }
                },
                {
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{"sheetId": worksheet.id, "startRowIndex": 1, "endRowIndex": data_rows + 1,
                                      "startColumnIndex": ord(col) - ord('A'), "endColumnIndex": ord(col) - ord('A') + 1}],
                            "booleanRule": {
                                "condition": {"type": "TEXT_CONTAINS", "values": [{"userEnteredValue": "High"}]},
                                "format": {"backgroundColor": {"red": 1.0, "green": 0.6, "blue": 0.6}}  # High risk - Red
                            }
                        },
                        "index": 2
                    }
                }
            ]
            
            self.spreadsheet.batch_update({"requests": requests})
            self.total_api_calls += 1
            
        except Exception as e:
            print(f"[Ultra] ⚠️  Risk level formatting failed: {e}")
    
    def upload_single_exchange_optimized(self, exchange_data, exchange, sheet_type="DATA"):
        """Upload a single exchange with ultra-optimization (2-3 API calls only)"""
        
        worksheet_name = f'{sheet_type} {exchange}'
        self.upload_stats[worksheet_name] = {'rows': len(exchange_data), 'api_calls': 0}
        
        try:
            print(f"[Ultra] 🔄 Processing {worksheet_name} ({len(exchange_data)} rows)")
            
            # Get or create worksheet (1 API call)
            try:
                worksheet = self.spreadsheet.worksheet(worksheet_name)
                print(f"[Ultra] ✅ Found existing worksheet: {worksheet_name}")
            except:
                worksheet = self.spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=25)
                print(f"[Ultra] ✅ Created new worksheet: {worksheet_name}")
                time.sleep(1)
            
            self.upload_stats[worksheet_name]['api_calls'] += 1
            self.total_api_calls += 1
            
            # Define complete column set based on sheet type
            if sheet_type == "DATA":
                all_required_columns = [
                    'Material Name', 'ticker', 'category', 'tier', 'Recipe', 'Amount per Recipe', 
                    'Weight', 'Volume', 'Current Price', 'Input Cost per Unit', 'Input Cost per Stack',
                    'Profit per Unit', 'Profit per Stack', 'ROI %', 'Supply', 'Demand', 
                    'Traded Volume', 'Market Cap', 'Liquidity Ratio', 'Investment Score', 
                    'Risk Level', 'Volatility'
                ]
                
                display_headers = [
                    'Material Name', 'Ticker', 'Category', 'Tier', 'Recipe', 'Amount per Recipe', 
                    'Weight', 'Volume', 'Current Price', 'Input Cost per Unit', 'Input Cost per Stack',
                    'Profit per Unit', 'Profit per Stack', 'ROI %', 'Supply', 'Demand', 
                    'Traded Volume', 'Market Cap', 'Liquidity Ratio', 'Investment Score', 
                    'Risk Level', 'Volatility'
                ]
            else:  # Report sheets
                all_required_columns = [
                    'Material Name', 'ticker', 'category', 'tier', 'Current Price', 'Supply', 'Demand',
                    'Input Cost per Unit', 'Profit per Unit', 'ROI %',
                    'Best Buy Exchange', 'Best Sell Exchange', 'Max Arbitrage Profit', 'Arbitrage ROI %',
                    'Bottleneck Type', 'Bottleneck Severity', 'Market Opportunity',
                    'Recommendation', 'Confidence %', 'Break-even Quantity', 'Production Time (hrs)',
                    'Total Production Cost', 'Investment Score', 'Risk Level', 'Volatility'
                ]
                
                display_headers = [
                    'Material Name', 'Ticker', 'Category', 'Tier', 'Current Price', 'Supply', 'Demand',
                    'Input Cost per Unit', 'Profit per Unit', 'ROI %',
                    'Best Buy Exchange', 'Best Sell Exchange', 'Max Arbitrage Profit', 'Arbitrage ROI %',
                    'Bottleneck Type', 'Bottleneck Severity', 'Market Opportunity',
                    'Recommendation', 'Confidence %', 'Break-even Quantity', 'Production Time (hrs)',
                    'Total Production Cost', 'Investment Score', 'Risk Level', 'Volatility'
                ]
            
            # Filter to available columns
            available_columns = []
            final_headers = []
            
            for i, col in enumerate(all_required_columns):
                if col in exchange_data.columns:
                    available_columns.append(col)
                    final_headers.append(display_headers[i])
            
            print(f"[Ultra] Using {len(available_columns)} columns (numeric values rounded to 3 decimals)")
            
            # Prepare ALL data in memory (headers + all rows)
            all_data = [final_headers]  # Headers first
            
            # Add all data rows with numeric formatting
            for _, row in exchange_data.iterrows():
                row_data = []
                for i, col in enumerate(available_columns):
                    value = row.get(col, '')
                    if pd.isna(value):
                        value = ''
                    else:
                        # Apply formatting to numeric columns for Google Sheets display
                        value = self.format_numeric_value(value, col)
                    row_data.append(str(value))
                all_data.append(row_data)
            
            # SINGLE BATCH OPERATION - Clear and upload everything
            print(f"[Ultra] Clearing and uploading {len(all_data)} rows in single batch...")
            
            # Clear worksheet (1 API call)
            worksheet.clear()
            self.upload_stats[worksheet_name]['api_calls'] += 1
            self.total_api_calls += 1
            time.sleep(0.5)
            
            # Calculate range for all data
            end_col = chr(ord('A') + len(available_columns) - 1)
            range_name = f"A1:{end_col}{len(all_data)}"
            
            # Single batch upload (1 API call)
            worksheet.update(range_name, all_data)
            self.upload_stats[worksheet_name]['api_calls'] += 1
            self.total_api_calls += 1
            
            # Apply conditional formatting for DATA sheets only
            if sheet_type == "DATA":
                # Format headers first
                self.format_headers(worksheet, len(available_columns))
                # Then apply simple conditional formatting (simplified for reliability)
                self.apply_simple_formatting(worksheet, available_columns, len(exchange_data))
            
            print(f"[Ultra] ✅ {worksheet_name} completed: {len(exchange_data)} rows, {self.upload_stats[worksheet_name]['api_calls']} API calls")
            
            # Small delay between exchanges to be safe
            time.sleep(1)
            
            return True
            
        except Exception as e:
            print(f"[Ultra] ❌ {worksheet_name} failed: {e}")
            if "429" in str(e):
                print(f"[Ultra] Rate limit hit for {worksheet_name} - waiting 60 seconds...")
                time.sleep(60)
            return False
    
    def upload_all_data_sheets(self, merged_df, priority_exchanges=None):
        """Upload DATA sheets for all exchanges with smart prioritization"""
        
        exchanges = merged_df['exchange'].unique()
        
        # Apply priority order if specified
        if priority_exchanges:
            ordered_exchanges = []
            # Add priority exchanges first
            for ex in priority_exchanges:
                if ex in exchanges:
                    ordered_exchanges.append(ex)
            # Add remaining exchanges
            for ex in exchanges:
                if ex not in ordered_exchanges:
                    ordered_exchanges.append(ex)
            exchanges = ordered_exchanges
        
        print(f"[Ultra] 🚀 Processing {len(exchanges)} exchanges: {list(exchanges)}")
        
        success_count = 0
        failed_exchanges = []
        
        for i, exchange in enumerate(exchanges):
            exchange_data = merged_df[merged_df['exchange'] == exchange].copy()
            
            if len(exchange_data) > 0:
                print(f"\\n[Ultra] --- Exchange {i+1}/{len(exchanges)}: {exchange} ---")
                
                # Attempt upload with retry logic
                max_retries = 2
                for attempt in range(max_retries):
                    try:
                        success = self.upload_single_exchange_optimized(exchange_data, exchange, "DATA")
                        
                        if success:
                            success_count += 1
                            break
                        else:
                            if attempt < max_retries - 1:
                                print(f"[Ultra] Retry {attempt + 1}/{max_retries} for {exchange}")
                                time.sleep(30)
                            else:
                                failed_exchanges.append(exchange)
                                print(f"[Ultra] ❌ {exchange} failed after {max_retries} attempts")
                    
                    except Exception as e:
                        print(f"[Ultra] ❌ {exchange} error: {e}")
                        if "429" in str(e) and attempt < max_retries - 1:
                            print(f"[Ultra] Rate limit for {exchange}, waiting...")
                            time.sleep(60)
                        elif attempt == max_retries - 1:
                            failed_exchanges.append(exchange)
            else:
                print(f"[Ultra] ⚠️  No data for {exchange}")
        
        # Print summary
        print(f"\\n[Ultra] 📊 DATA SHEETS SUMMARY:")
        print(f"   ✅ Successful: {success_count}/{len(exchanges)} exchanges")
        print(f"   📈 Total API calls: {self.total_api_calls}")
        print(f"   🕐 Estimated time savings: {((success_count * 350) - self.total_api_calls) / 350 * 100:.1f}% fewer API calls")
        
        if failed_exchanges:
            print(f"   ❌ Failed: {failed_exchanges}")
        
        return success_count, failed_exchanges
    
    def upload_all_report_sheets(self, analysis_df, priority_exchanges=None):
        """Upload Report sheets for all exchanges (optional advanced analysis)"""
        
        exchanges = analysis_df['exchange'].unique()
        
        # Apply priority order if specified
        if priority_exchanges:
            ordered_exchanges = []
            for ex in priority_exchanges:
                if ex in exchanges:
                    ordered_exchanges.append(ex)
            for ex in exchanges:
                if ex not in ordered_exchanges:
                    ordered_exchanges.append(ex)
            exchanges = ordered_exchanges
        
        print(f"[Ultra] 📊 Processing {len(exchanges)} Report sheets: {list(exchanges)}")
        
        success_count = 0
        
        for exchange in exchanges:
            exchange_data = analysis_df[analysis_df['exchange'] == exchange].copy()
            
            if len(exchange_data) > 0:
                try:
                    success = self.upload_single_exchange_optimized(exchange_data, exchange, "Report")
                    if success:
                        success_count += 1
                    
                    # Add extra delay for Report sheets (they're larger)
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"[Ultra] ❌ Report {exchange} failed: {e}")
                    if "429" in str(e):
                        print("[Ultra] Rate limit hit - stopping Report uploads to preserve quota")
                        break
        
        return success_count
    
    def print_performance_stats(self):
        """Print detailed performance statistics"""
        print(f"\\n[Ultra] 📈 PERFORMANCE STATISTICS:")
        print(f"   🔥 Total API calls: {self.total_api_calls}")
        
        total_rows = sum(stats['rows'] for stats in self.upload_stats.values())
        traditional_calls = total_rows + (len(self.upload_stats) * 25)  # Estimate for traditional method
        
        print(f"   📊 Total rows uploaded: {total_rows}")
        print(f"   ⚡ Traditional method would need: ~{traditional_calls} API calls")
        print(f"   🚀 Optimization efficiency: {((traditional_calls - self.total_api_calls) / traditional_calls * 100):.1f}% fewer calls")
        
        print(f"\\n[Ultra] 📋 Per-sheet breakdown:")
        for sheet, stats in self.upload_stats.items():
            print(f"   {sheet}: {stats['rows']} rows, {stats['api_calls']} API calls")

def main_ultra_all_exchanges():
    """Main function for ultra-optimized upload of ALL exchanges"""
    import os
    import sys
    
    print("=" * 60)
    print("🚀 ULTRA-OPTIMIZED ALL-EXCHANGES UPLOAD")
    print("=" * 60)
    
    # Setup
    os.chdir(r"c:\Users\Usuario\Documents\GitHub\PrUn-Tracker - copia\pu-tracker")
    sys.path.insert(0, os.getcwd())
    
    try:
        from historical_data.config import CONFIG
        import pandas as pd
        
        print("[Ultra] 📂 Loading data files...")
        
        # Load data files separately for different sheet types
        daily_report_df = pd.read_csv("cache/daily_report.csv")
        daily_analysis_df = pd.read_csv("cache/daily_analysis.csv")
        
        print(f"[Ultra] ✅ Loaded report data (for DATA sheets): {len(daily_report_df)} rows")
        print(f"[Ultra] ✅ Loaded analysis data (for Report sheets): {len(daily_analysis_df)} rows")
        
        # Merge datasets ONLY for DATA sheets to get complete column coverage
        print("[Ultra] 🔄 Preparing DATA sheets data (merging report + analysis)...")
        data_sheets_df = daily_report_df.merge(
            daily_analysis_df[['ticker', 'exchange', 'Investment Score', 'Risk Level']], 
            on=['ticker', 'exchange'], 
            how='left'
        )
        print(f"[Ultra] ✅ DATA sheets data ready: {len(data_sheets_df)} records")
        
        # Keep analysis data separate for Report sheets
        print("[Ultra] 🔄 Preparing Report sheets data (pure analysis data)...")
        report_sheets_df = daily_analysis_df.copy()
        print(f"[Ultra] ✅ Report sheets data ready: {len(report_sheets_df)} records")
        
        # Show column differences
        print(f"\\n[Ultra] 📋 Column comparison:")
        print(f"   DATA sheets columns: {len(data_sheets_df.columns)} total")
        data_key_cols = [col for col in data_sheets_df.columns if any(x in col for x in ['Price', 'Cost', 'Profit', 'ROI', 'Supply', 'Demand', 'Recipe', 'Weight', 'Volume'])]
        print(f"     Key DATA columns: {data_key_cols[:10]}...")
        print(f"   Report sheets columns: {len(report_sheets_df.columns)} total") 
        report_key_cols = [col for col in report_sheets_df.columns if any(x in col for x in ['Arbitrage', 'Bottleneck', 'Opportunity', 'Confidence', 'Break-even', 'Best Buy', 'Best Sell'])]
        print(f"     Key Report columns: {report_key_cols}")
        
        # Verify different data content
        print(f"\\n[Ultra] 🔍 Data content verification:")
        if 'Ask Price' in data_sheets_df.columns and 'Ask Price' not in report_sheets_df.columns:
            print(f"   ✅ DATA sheets have Ask Price (market data)")
        if 'Best Buy Exchange' in report_sheets_df.columns and 'Best Buy Exchange' not in data_sheets_df.columns:
            print(f"   ✅ Report sheets have Best Buy Exchange (analysis data)")
        else:
            print(f"   ⚠️  Report sheets might not have unique analysis columns!")
        
        # Show exchange breakdown for both data types
        data_exchange_counts = data_sheets_df['exchange'].value_counts()
        report_exchange_counts = report_sheets_df['exchange'].value_counts()
        print(f"\\n[Ultra] 📊 DATA sheets exchange breakdown:")
        for exchange, count in data_exchange_counts.items():
            print(f"   {exchange}: {count} materials")
        print(f"\\n[Ultra] 📊 Report sheets exchange breakdown:")
        for exchange, count in report_exchange_counts.items():
            print(f"   {exchange}: {count} materials")
        
        # Initialize uploader
        uploader = UltraOptimizedUploader(
            CONFIG['GOOGLE_SERVICE_ACCOUNT_FILE'],
            CONFIG['TARGET_SPREADSHEET_ID']
        )
        
        # Upload DATA sheets with AI1 priority (using merged data for complete columns)
        print(f"\\n[Ultra] 🎯 Starting DATA sheets upload...")
        success_count, failed = uploader.upload_all_data_sheets(
            data_sheets_df, 
            priority_exchanges=['AI1', 'CI1', 'CI2', 'NC1', 'NC2', 'IC1']
        )
        
        # Upload Report sheets (using pure analysis data)
        if success_count >= 3:  # If at least 3 DATA sheets succeeded
            print(f"\\n[Ultra] 📊 Starting Report sheets upload...")
            report_success = uploader.upload_all_report_sheets(
                report_sheets_df,
                priority_exchanges=['AI1']  # Only prioritize AI1 for reports
            )
            print(f"[Ultra] ✅ Report sheets completed: {report_success} sheets")
        else:
            print(f"\\n[Ultra] ⚠️  Skipping Report sheets due to DATA sheet issues")
        
        # Print final statistics
        uploader.print_performance_stats()
        
        if success_count > 0:
            print(f"\\n🎉 ULTRA-OPTIMIZED UPLOAD COMPLETED!")
            print(f"✅ Successfully uploaded {success_count} DATA sheets")
            print(f"📊 Check your Google Sheets - all exchange tabs should be populated")
        else:
            print(f"\\n❌ Upload failed for all exchanges")
        
        return success_count > 0
        
    except Exception as e:
        print(f"❌ Critical error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main_ultra_all_exchanges()
