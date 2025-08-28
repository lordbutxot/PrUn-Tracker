"""
Debug script to find the correct PrUn API endpoints
"""

import requests
import json
import pandas as pd
import os
from datetime import datetime

def test_api_endpoints():
    """Test various API endpoint patterns"""
    print(" Testing different API endpoint patterns...")
    
    # Common base URLs for PrUn API
    base_urls = [
        "https://rest.fnar.net",
        "https://api.fnar.net", 
        "https://fnar.net/api",
        "https://rest.prosperousuniverse.com",
        "https://api.prosperousuniverse.com"
    ]
    
    endpoints = [
        "/material/all",
        "/materials",
        "/exchange/all",
        "/exchanges", 
        "/market/all",
        "/market",
        "/v1/material/all",
        "/v1/exchange/all"
    ]
    
    for base_url in base_urls:
        print(f"\n Testing base URL: {base_url}")
        
        for endpoint in endpoints:
            try:
                url = base_url + endpoint
                response = requests.get(url, timeout=5)
                print(f"  {endpoint}: Status {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"     SUCCESS: Got {len(data) if isinstance(data, list) else 'data'}")
                        
                        # Save successful endpoint info
                        with open("cache/successful_endpoint.txt", "w") as f:
                            f.write(f"{url}\n")
                            f.write(f"Status: {response.status_code}\n")
                            if isinstance(data, list) and len(data) > 0:
                                f.write(f"Sample keys: {list(data[0].keys())}\n")
                        
                        return url, data
                        
                    except:
                        print(f"     Not JSON data")
                        
            except Exception as e:
                print(f"  {endpoint}:  {e}")
    
    return None, None

def test_exchange_endpoints():
    """Test exchange-specific endpoints"""
    print("\n Testing exchange endpoints...")
    
    base_urls = [
        "https://rest.fnar.net",
        "https://api.fnar.net"
    ]
    
    exchanges = ['AI1', 'CI1', 'CI2', 'IC1', 'NC1', 'NC2']
    
    endpoint_patterns = [
        "/exchange/all/{exchange}",
        "/exchange/{exchange}",
        "/market/{exchange}",
        "/v1/exchange/{exchange}",
        "/exchanges/{exchange}"
    ]
    
    for base_url in base_urls:
        for pattern in endpoint_patterns:
            for exchange in exchanges[:2]:  # Test first 2 exchanges only
                try:
                    url = base_url + pattern.format(exchange=exchange)
                    response = requests.get(url, timeout=5)
                    
                    if response.status_code == 200:
                        print(f" SUCCESS: {url}")
                        try:
                            data = response.json()
                            print(f"    Got {len(data)} items for {exchange}")
                            return url.replace(exchange, "{exchange}"), data
                        except:
                            print(f"     Not JSON")
                    else:
                        print(f" {url}: {response.status_code}")
                        
                except Exception as e:
                    continue
    
    return None, None

def check_fnar_documentation():
    """Check if we can find API documentation"""
    print("\n Looking for API documentation...")
    
    doc_urls = [
        "https://rest.fnar.net",
        "https://fnar.net/docs",
        "https://fnar.net/api",
        "https://doc.fnar.net"
    ]
    
    for url in doc_urls:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f" Found docs at: {url}")
                # Check if it contains API info
                content = response.text.lower()
                if 'api' in content or 'endpoint' in content:
                    print(f"    Contains API information")
        except:
            continue

def try_alternative_apis():
    """Try alternative data sources"""
    print("\n Trying alternative data sources...")
    
    # Try to find if there are other APIs or data sources
    alternatives = [
        "https://prosperousuniverse.com/api",
        "https://data.prosperousuniverse.com", 
        "https://market.prosperousuniverse.com"
    ]
    
    for url in alternatives:
        try:
            response = requests.get(url, timeout=5)
            print(f"{url}: Status {response.status_code}")
        except Exception as e:
            print(f"{url}:  {e}")

def inspect_existing_data():
    """Check if we have any existing working data"""
    print("\n Looking for existing working data...")
    
    # Check current directory and parent directories for data
    search_dirs = [
        ".",
        "..",
        "cache",
        "../cache",
        "data",
        "../data",
        "historical_data"
    ]
    
    for search_dir in search_dirs:
        if os.path.exists(search_dir):
            print(f"\n Checking {search_dir}:")
            try:
                files = os.listdir(search_dir)
                data_files = [f for f in files if f.endswith(('.csv', '.json')) and 'market' in f.lower() or 'material' in f.lower()]
                
                for file in data_files:
                    file_path = os.path.join(search_dir, file)
                    size = os.path.getsize(file_path)
                    print(f"   {file}: {size} bytes")
                    
                    if file.endswith('.csv') and size > 0:
                        try:
                            df = pd.read_csv(file_path, nrows=3)
                            print(f"    Columns: {list(df.columns)}")
                        except:
                            pass
                            
            except:
                pass

if __name__ == "__main__":
    print(" PrUn API Endpoint Debug")
    print("=" * 50)
    
    # Create cache directory
    os.makedirs("cache", exist_ok=True)
    
    # Test various endpoints
    working_url, sample_data = test_api_endpoints()
    
    if working_url:
        print(f"\n Found working endpoint: {working_url}")
    else:
        print("\n No working material endpoints found")
    
    # Test exchange endpoints
    exchange_url, exchange_data = test_exchange_endpoints()
    
    if exchange_url:
        print(f"\n Found working exchange endpoint: {exchange_url}")
    else:
        print("\n No working exchange endpoints found")
    
    # Check documentation
    check_fnar_documentation()
    
    # Try alternatives
    try_alternative_apis()
    
    # Check existing data
    inspect_existing_data()
    
    print("\n API debug complete!")
    
    # Summary
    if working_url or exchange_url:
        print("\n RESULTS:")
        if working_url:
            print(f"  Materials API: {working_url}")
        if exchange_url:
            print(f"  Exchange API: {exchange_url}")
    else:
        print("\n No working APIs found. Possible issues:")
        print("  1. API has changed or been deprecated")
        print("  2. Authentication required")
        print("  3. Different base URL")
        print("  4. Rate limiting")