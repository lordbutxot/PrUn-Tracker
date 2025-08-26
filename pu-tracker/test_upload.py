#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(__file__))

print("Starting upload test...")

try:
    import upload_data
    print("Import successful, calling main...")
    upload_data.main()
    print("Main completed successfully")
except Exception as e:
    print(f"Error occurred: {e}")
    import traceback
    traceback.print_exc()
