import time
import logging
from typing import List, Dict, Any, Optional
import pandas as pd

logger = logging.getLogger(__name__)

class SheetsOptimizer:
    """Optimized Google Sheets operations with batch processing and rate limiting."""
    
    def __init__(self, spreadsheet):
        self.spreadsheet = spreadsheet
        self.logger = logging.getLogger(__name__)
    
    def clear_and_update_worksheet(self, worksheet_name: str, data_values: List[List], header_format: Optional[Dict] = None) -> bool:
        """Clear worksheet and update with new data in one optimized operation."""
        try:
            # Get or create worksheet
            try:
                worksheet = self.spreadsheet.worksheet(worksheet_name)
            except Exception:
                # Create worksheet if it doesn't exist
                worksheet = self.spreadsheet.add_worksheet(
                    title=worksheet_name, 
                    rows=max(1000, len(data_values) + 100), 
                    cols=max(26, len(data_values[0]) if data_values else 26)
                )
                self.logger.info(f"Created new worksheet: {worksheet_name}")
            
            # Clear existing content
            worksheet.clear()
            self.logger.info(f"Cleared worksheet: {worksheet_name}")
            
            # Update with new data if we have any
            if data_values and len(data_values) > 0:
                # Determine the range for the data
                num_rows = len(data_values)
                num_cols = len(data_values[0]) if data_values else 1
                
                # Convert range to A1 notation
                end_col = chr(ord('A') + num_cols - 1) if num_cols <= 26 else f"A{num_cols}"
                range_name = f"A1:{end_col}{num_rows}"
                
                # Clean data before uploading
                if isinstance(data_values, list) and len(data_values) > 1:
                    # Convert to DataFrame for easier cleaning
                    df = pd.DataFrame(data_values[1:], columns=data_values[0])
                    df = df.fillna(0)  # Replace NaN with 0
                    # Convert back to list format
                    data_values = [list(df.columns)] + df.values.tolist()
                
                # Update all data at once
                worksheet.update(range_name, data_values, value_input_option='RAW')
                self.logger.info(f"Updated {worksheet_name} with {num_rows} rows, {num_cols} columns")
                
                # Apply header formatting if provided
                if header_format and num_rows > 0:
                    try:
                        header_range = f"A1:{end_col}1"
                        worksheet.format(header_range, header_format)
                        self.logger.info(f"Applied header formatting to {header_range}")
                    except Exception as e:
                        self.logger.warning(f"Failed to apply header formatting: {e}")
                
                return True
            else:
                self.logger.warning(f"No data to upload to {worksheet_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error in clear_and_update_worksheet for {worksheet_name}: {e}")
            return False
    
    def batch_update_worksheets(self, worksheets_data: Dict[str, List[List]], header_format: Optional[Dict] = None) -> Dict[str, bool]:
        """Update multiple worksheets in batch with rate limiting."""
        results = {}
        
        for worksheet_name, data_values in worksheets_data.items():
            try:
                self.logger.info(f"Updating worksheet: {worksheet_name} ({len(data_values)} rows)")
                success = self.clear_and_update_worksheet(worksheet_name, data_values, header_format)
                results[worksheet_name] = success
                
                # Rate limiting - pause between worksheets
                time.sleep(2)
                
            except Exception as e:
                self.logger.error(f"Failed to update {worksheet_name}: {e}")
                results[worksheet_name] = False
        
        return results
    
    def get_worksheet_or_create(self, worksheet_name: str, rows: int = 1000, cols: int = 26):
        """Get existing worksheet or create new one."""
        try:
            return self.spreadsheet.worksheet(worksheet_name)
        except Exception:
            return self.spreadsheet.add_worksheet(title=worksheet_name, rows=rows, cols=cols)
    
    def optimize_worksheet_size(self, worksheet_name: str, data_rows: int, data_cols: int):
        """Optimize worksheet size based on data dimensions."""
        try:
            worksheet = self.spreadsheet.worksheet(worksheet_name)
            
            # Add some buffer to the actual data size
            target_rows = max(data_rows + 50, 100)
            target_cols = max(data_cols + 5, 10)
            
            # Resize if needed
            if worksheet.row_count != target_rows or worksheet.col_count != target_cols:
                worksheet.resize(rows=target_rows, cols=target_cols)
                self.logger.info(f"Resized {worksheet_name} to {target_rows}x{target_cols}")
                
        except Exception as e:
            self.logger.warning(f"Failed to optimize size for {worksheet_name}: {e}")