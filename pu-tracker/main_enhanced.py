import asyncio
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add paths for imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir / "core"))
sys.path.append(str(current_dir / "historical_data"))

from core.pipeline_controller import PipelineController
from core.smart_cache import SmartCache

async def run_catch_data(cache_system, use_cache=True):
    """Async wrapper for catch_data"""
    try:
        from catch_data import main as catch_main
        print("Running data collection...")
        result = catch_main()
        print("Data collection completed successfully")
        return result
    except Exception as e:
        print(f"Error in data collection: {e}")
        raise

async def run_process_data(cache_system, exchanges=None):
    """Async wrapper for process_data"""
    try:
        from unified_processor import main as process_main
        print("Running data processing...")
        result = process_main()
        print("Data processing completed successfully")
        return result
    except Exception as e:
        print(f"Error in data processing: {e}")
        raise

async def run_upload_data(cache_system, exchanges=None):
    """Async wrapper for upload_data"""
    try:
        # Try ultra upload first, fallback to standard
        import subprocess
        result = subprocess.run([sys.executable, "ultra_all_exchanges_upload.py"], 
                              capture_output=True, text=True, cwd=current_dir)
        if result.returncode == 0:
            print("Ultra upload completed successfully")
            return "ultra_upload_success"
        else:
            # Fallback to standard upload
            from upload_data import main as upload_main
            result = upload_main()
            print("Standard upload completed successfully")
            return result
    except Exception as e:
        print(f"Error in data upload: {e}")
        raise

async def main():
    """Enhanced main entry point with async support"""
    parser = argparse.ArgumentParser(description='PrUn-Tracker Enhanced Pipeline')
    parser.add_argument('command', choices=['catch', 'process', 'upload', 'full'], 
                       help='Pipeline command to run')
    parser.add_argument('--skip-cache', action='store_true', help='Skip cache and force refresh')
    parser.add_argument('--exchanges', nargs='+', default=['AI1', 'CI1', 'CI2'], 
                       help='Exchanges to process')
    parser.add_argument('--clear-cache', action='store_true', help='Clear expired cache entries')
    args = parser.parse_args()
    
    # Initialize core systems
    cache_dir = Path("cache")
    data_dir = Path("data")
    cache_system = SmartCache(cache_dir, default_ttl=1800)  # 30 min default TTL
    
    # Clear expired cache if requested
    if args.clear_cache:
        cleared = cache_system.clear_expired()
        print(f"Cleared {cleared} expired cache entries")
    
    # Setup pipeline controller
    controller = PipelineController(cache_dir, data_dir)
    
    # Configure pipeline steps based on command
    if args.command in ['catch', 'full']:
        controller.add_step('data_collection', 
                          lambda: run_catch_data(cache_system, not args.skip_cache),
                          timeout=600)
    
    if args.command in ['process', 'full']:
        controller.add_step('data_processing', 
                          lambda: run_process_data(cache_system, args.exchanges),
                          timeout=300)
    
    if args.command in ['upload', 'full']:
        controller.add_step('data_upload', 
                          lambda: run_upload_data(cache_system, args.exchanges),
                          timeout=600)
    
    # Run pipeline
    print(f"========================================")
    print(f"  PrUn-Tracker Enhanced Pipeline")
    print(f"========================================")
    print(f"Command: {args.command}")
    print(f"Started at: {datetime.now()}")
    print(f"Cache stats: {cache_system.get_cache_stats()}")
    print()
    
    results = await controller.run_pipeline()
    
    # Print results
    print(f"\n========================================")
    print(f"  Pipeline Results")
    print(f"========================================")
    
    summary = results.get('pipeline_summary', {})
    print(f"Duration: {summary.get('total_duration', 0):.2f}s")
    print(f"Successful steps: {summary.get('success_count', 0)}")
    print(f"Failed steps: {summary.get('error_count', 0)}")
    
    if summary.get('error_count', 0) > 0:
        print(f"\nPipeline completed with errors!")
        sys.exit(1)
    else:
        print(f"\nPipeline completed successfully!")
        sys.exit(0)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nPipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)