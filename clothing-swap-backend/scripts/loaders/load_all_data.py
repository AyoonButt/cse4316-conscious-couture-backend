#!/usr/bin/env python3
"""
Load all reference data into the database in the correct order.
Orchestrates loading of materials, clothing types, brands, and parameters.
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.database import get_database_session

# Import individual loaders
from load_materials import load_materials_from_csv, clear_materials_table, show_materials_summary
from load_clothing_types import load_clothing_types_from_csv, clear_clothing_types_table, show_clothing_types_summary
from load_brands import load_brands_from_csv, clear_brands_table, show_brands_summary
from load_parameters import load_parameters_from_json, clear_parameters_table, show_parameters_summary, add_default_parameters

def load_all_reference_data(data_dir: Path, session, update_existing: bool = False, clear_first: bool = False) -> dict:
    """Load all reference data in the correct order."""
    
    # Define file paths
    files = {
        'materials': data_dir / "textile_exchange_materials.csv",
        'clothing_types': data_dir / "clothing_types.csv",
        'brands': data_dir / "brands_sustainability.csv",
        'parameters': data_dir / "calculation_parameters.json"
    }
    
    # Check all files exist
    missing_files = [name for name, path in files.items() if not path.exists()]
    if missing_files:
        print(f"❌ Missing data files: {', '.join(missing_files)}")
        print("Please ensure all data files exist before loading.")
        return {'success': False, 'missing_files': missing_files}
    
    results = {
        'success': True,
        'materials': {'loaded': 0, 'updated': 0, 'skipped': 0, 'errors': 0},
        'clothing_types': {'loaded': 0, 'updated': 0, 'skipped': 0, 'errors': 0},
        'brands': {'loaded': 0, 'updated': 0, 'skipped': 0, 'errors': 0},
        'parameters': {'loaded': 0, 'updated': 0, 'skipped': 0, 'errors': 0},
        'start_time': datetime.now(),
        'end_time': None
    }
    
    print("🚀 Starting comprehensive data loading...")
    print(f"Update existing records: {update_existing}")
    print(f"Clear tables first: {clear_first}")
    print(f"Data directory: {data_dir}")
    
    try:
        # Phase 0: Clear existing data if requested
        if clear_first:
            print(f"\n{'='*60}")
            print("PHASE 0: CLEARING EXISTING DATA")
            print(f"{'='*60}")
            
            print("🗑️  Clearing all reference tables...")
            clear_parameters_table(session)
            clear_brands_table(session)
            clear_clothing_types_table(session)
            clear_materials_table(session)
            print("✅ All tables cleared successfully")
        
        # Phase 1: Load materials (foundation data)
        print(f"\n{'='*60}")
        print("PHASE 1: LOADING MATERIALS")
        print(f"{'='*60}")
        
        materials_result = load_materials_from_csv(files['materials'], session, update_existing)
        results['materials'] = materials_result
        
        if materials_result['errors'] > 0:
            print(f"⚠️  {materials_result['errors']} errors in materials loading")
        
        # Phase 2: Load clothing types
        print(f"\n{'='*60}")
        print("PHASE 2: LOADING CLOTHING TYPES")
        print(f"{'='*60}")
        
        clothing_types_result = load_clothing_types_from_csv(files['clothing_types'], session, update_existing)
        results['clothing_types'] = clothing_types_result
        
        if clothing_types_result['errors'] > 0:
            print(f"⚠️  {clothing_types_result['errors']} errors in clothing types loading")
        
        # Phase 3: Load brands
        print(f"\n{'='*60}")
        print("PHASE 3: LOADING BRANDS")
        print(f"{'='*60}")
        
        brands_result = load_brands_from_csv(files['brands'], session, update_existing)
        results['brands'] = brands_result
        
        if brands_result['errors'] > 0:
            print(f"⚠️  {brands_result['errors']} errors in brands loading")
        
        # Phase 4: Load calculation parameters
        print(f"\n{'='*60}")
        print("PHASE 4: LOADING CALCULATION PARAMETERS")
        print(f"{'='*60}")
        
        parameters_result = load_parameters_from_json(files['parameters'], session, update_existing)
        results['parameters'] = parameters_result
        
        if parameters_result['errors'] > 0:
            print(f"⚠️  {parameters_result['errors']} errors in parameters loading")
        
        # Phase 5: Add default parameters if needed
        if not files['parameters'].exists() or clear_first:
            print(f"\n{'='*60}")
            print("PHASE 5: ADDING DEFAULT PARAMETERS")
            print(f"{'='*60}")
            
            add_default_parameters(session)
        
        results['end_time'] = datetime.now()
        results['duration'] = results['end_time'] - results['start_time']
        
        return results
        
    except Exception as e:
        print(f"❌ Critical error during data loading: {e}")
        session.rollback()
        results['success'] = False
        results['error'] = str(e)
        return results

def print_comprehensive_summary(session, results: dict):
    """Print comprehensive summary of all loaded data."""
    
    print(f"\n{'='*80}")
    print("COMPREHENSIVE DATA LOADING SUMMARY")
    print(f"{'='*80}")
    
    # Loading statistics
    print(f"\n📊 Loading Statistics:")
    total_loaded = sum(r['loaded'] for r in [results['materials'], results['clothing_types'], results['brands'], results['parameters']])
    total_updated = sum(r['updated'] for r in [results['materials'], results['clothing_types'], results['brands'], results['parameters']])
    total_skipped = sum(r['skipped'] for r in [results['materials'], results['clothing_types'], results['brands'], results['parameters']])
    total_errors = sum(r['errors'] for r in [results['materials'], results['clothing_types'], results['brands'], results['parameters']])
    
    print(f"  ✅ Total Loaded: {total_loaded}")
    print(f"  🔄 Total Updated: {total_updated}")
    print(f"  ⏭️  Total Skipped: {total_skipped}")
    print(f"  ❌ Total Errors: {total_errors}")
    
    if 'duration' in results:
        print(f"  ⏱️  Duration: {results['duration']}")
    
    # Detailed breakdown
    print(f"\n📋 Detailed Breakdown:")
    for category in ['materials', 'clothing_types', 'brands', 'parameters']:
        r = results[category]
        print(f"  {category.upper()}:")
        print(f"    Loaded: {r['loaded']}, Updated: {r['updated']}, Skipped: {r['skipped']}, Errors: {r['errors']}")
    
    # Show summaries if data was loaded successfully
    if total_loaded > 0 or total_updated > 0:
        print(f"\n📚 Database Content Summary:")
        
        try:
            # Materials summary
            print(f"\n🧵 MATERIALS:")
            show_materials_summary(session)
            
            # Clothing types summary
            print(f"\n👕 CLOTHING TYPES:")
            show_clothing_types_summary(session)
            
            # Brands summary
            print(f"\n🏷️  BRANDS:")
            show_brands_summary(session)
            
            # Parameters summary
            print(f"\n⚙️  CALCULATION PARAMETERS:")
            show_parameters_summary(session)
            
        except Exception as e:
            print(f"⚠️  Error showing summaries: {e}")
    
    # Success/failure message
    if results['success'] and total_errors == 0:
        print(f"\n🎉 ALL DATA LOADED SUCCESSFULLY!")
        print("The database is now ready for the clothing swap application.")
    elif results['success'] and total_errors > 0:
        print(f"\n⚠️  DATA LOADING COMPLETED WITH {total_errors} ERRORS")
        print("Review the errors above and consider fixing data files.")
    else:
        print(f"\n💥 DATA LOADING FAILED")
        if 'error' in results:
            print(f"Error: {results['error']}")
    
    print(f"{'='*80}")

def validate_data_directory(data_dir: Path) -> bool:
    """Validate that the data directory contains expected files."""
    
    required_files = [
        "textile_exchange_materials.csv",
        "clothing_types.csv", 
        "brands_sustainability.csv",
        "calculation_parameters.json"
    ]
    
    print(f"🔍 Validating data directory: {data_dir}")
    
    if not data_dir.exists():
        print(f"❌ Data directory does not exist: {data_dir}")
        return False
    
    missing_files = []
    for filename in required_files:
        filepath = data_dir / filename
        if filepath.exists():
            print(f"✅ Found: {filename}")
        else:
            print(f"❌ Missing: {filename}")
            missing_files.append(filename)
    
    if missing_files:
        print(f"\n💡 To create missing files, you can:")
        for filename in missing_files:
            if "materials" in filename:
                print(f"  • Run: python scripts/update_material_data.py <material_name>")
            elif "clothing_types" in filename:
                print(f"  • Run: python scripts/add_clothing_type.py <clothing_type>")
            elif "brands" in filename:
                print(f"  • Run: python scripts/update_brand_data.py <brand_name>")
            elif "parameters" in filename:
                print(f"  • Use: --add-defaults flag to create default parameters")
        return False
    
    print(f"\n✅ All required files found!")
    return True

def main():
    parser = argparse.ArgumentParser(description='Load all reference data into database')
    parser.add_argument('--data-dir', help='Directory containing data files',
                        default=str(Path(__file__).parent.parent.parent / "data"))
    parser.add_argument('--update', action='store_true', 
                        help='Update existing records instead of skipping them')
    parser.add_argument('--clear', action='store_true', 
                        help='Clear all existing data before loading')
    parser.add_argument('--validate-only', action='store_true',
                        help='Only validate data files without loading')
    parser.add_argument('--dry-run', action='store_true', 
                        help='Show what would be loaded without actually loading')
    parser.add_argument('--summary-only', action='store_true',
                        help='Show summary of existing data without loading')
    
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir)
    
    # Validate data directory
    if args.validate_only:
        validate_data_directory(data_dir)
        return
    
    # Get database session
    try:
        session = get_database_session()
        print(f"🔗 Connected to database")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return
    
    try:
        # Show summary only
        if args.summary_only:
            print("📊 Current Database Summary:")
            show_materials_summary(session)
            show_clothing_types_summary(session)
            show_brands_summary(session)
            show_parameters_summary(session)
            return
        
        # Dry run
        if args.dry_run:
            print("🔍 DRY RUN MODE - No changes will be made")
            if not validate_data_directory(data_dir):
                return
            print(f"\nWould load data from: {data_dir}")
            print(f"Update existing: {args.update}")
            print(f"Clear first: {args.clear}")
            return
        
        # Validate before loading
        if not validate_data_directory(data_dir):
            print("\n❌ Cannot proceed with invalid data directory")
            return
        
        # Confirm destructive operations
        if args.clear:
            print(f"\n⚠️  WARNING: This will delete ALL existing reference data!")
            confirm = input("Are you sure you want to continue? (y/N): ")
            if confirm.lower() != 'y':
                print("Cancelled.")
                return
        
        # Load all data
        results = load_all_reference_data(data_dir, session, args.update, args.clear)
        
        # Print comprehensive summary
        print_comprehensive_summary(session, results)
        
        # Exit with error code if there were issues
        if not results['success']:
            sys.exit(1)
        
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Loading interrupted by user")
        session.rollback()
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        session.rollback()
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    main()