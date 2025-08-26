"""
main.py
Top-level entry point for PrUn-Tracker pipeline.
This is a simple wrapper that redirects to the main entry point in historical_data folder.
"""

import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

def main():
    """Main entry point - redirects to historical_data.main"""
    # Import and run the main function from historical_data
    from historical_data.main import main as historical_main
    historical_main()

if __name__ == "__main__":
    main()
