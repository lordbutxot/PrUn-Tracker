"""
Unit tests for data processing
"""
import unittest
import pandas as pd
import sys
import os

# Add the project root to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from pu_tracker.historical_data.data_processor import DataProcessor

class TestDataProcessor(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.processor = DataProcessor()
        
        # Create sample data
        self.sample_market_data = pd.DataFrame({
            'Ticker': ['ALU', 'FE', 'CU'],
            'AI1_Price': [100, 200, 150],
            'AI1_Supply': [50, 30, 40],
            'AI1_Demand': [60, 25, 45]
        })
        
        self.sample_materials = pd.DataFrame({
            'Ticker': ['ALU', 'FE', 'CU'],
            'Name': ['Aluminum', 'Iron', 'Copper'],
            'CategoryName': ['Metals', 'Metals', 'Metals'],
            'Tier': [1, 1, 1]
        })
        
        self.sample_chains = {
            'ALU': {
                'recipe_key': 'ALU_SMELTING',
                'inputs': {'FE': 2, 'CU': 1},
                'output_amount': 1
            }
        }
    
    def test_standardize_columns(self):
        """Test column standardization"""
        result = self.processor.standardize_columns(self.sample_market_data)
        self.assertIn('Ticker', result.columns)
    
    def test_process_data(self):
        """Test main data processing method"""
        result = self.processor.process_data(
            self.sample_market_data,
            self.sample_materials,
            self.sample_chains
        )
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0)

if __name__ == '__main__':
    unittest.main()