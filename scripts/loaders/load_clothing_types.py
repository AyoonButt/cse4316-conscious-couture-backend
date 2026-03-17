#!/usr/bin/env python3
"""
Load clothing type reference data from CSV into the database.
Creates ClothingTypeReference records from clothing_types.csv
"""

import sys
import csv
import argparse
from pathlib import Path
from decimal import Decimal
from typing import Optional

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.database import get_database_session
from app.models.clothing_type import ClothingTypeReference

def load_clothing_types_from_csv(csv_path: Path, session, update_existing: bool = False) -> dict:
    """Load clothing types from CSV file into database."""
    
    if not csv_path.exists():
        raise FileNotFoundError(f"Clothing types CSV file not found: {csv_path}")
    
    results = {
        'loaded': 0,
        'updated': 0,
        'skipped': 0,
        'errors': 0
    }
    
    print(f"📥 Loading clothing types from: {csv_path}")
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, 2):  # Start from row 2 (header is row 1)
            try:
                clothing_type = row.get('clothing_type', '').strip()
                if not clothing_type:
                    print(f"⏭️  Row {row_num}: Skipping empty clothing type")
                    results['skipped'] += 1
                    continue
                
                # Check if clothing type already exists
                existing_type = session.query(ClothingTypeReference).filter(
                    ClothingTypeReference.clothing_type == clothing_type
                ).first()
                
                if existing_type and not update_existing:
                    print(f"⏭️  Row {row_num}: Clothing type '{clothing_type}' already exists, skipping")
                    results['skipped'] += 1
                    continue
                
                # Parse required fields
                category = row.get('category', 'unknown')
                typical_weight_grams = int(row.get('typical_weight_grams', '0') or '0')
                
                # Parse optional fields with defaults
                weight_range_min = None
                weight_range_max = None
                if row.get('weight_range_min'):
                    try:
                        weight_range_min = int(row['weight_range_min'])
                    except (ValueError, TypeError):
                        pass
                if row.get('weight_range_max'):
                    try:
                        weight_range_max = int(row['weight_range_max'])
                    except (ValueError, TypeError):
                        pass
                
                typical_wears = None
                if row.get('typical_wears'):
                    try:
                        typical_wears = int(row['typical_wears'])
                    except (ValueError, TypeError):
                        pass
                
                wash_frequency = None
                if row.get('wash_frequency'):
                    try:
                        wash_frequency = Decimal(str(row['wash_frequency']))
                    except (ValueError, TypeError):
                        pass
                
                if existing_type:
                    # Update existing clothing type
                    existing_type.category = category
                    existing_type.typical_weight_grams = typical_weight_grams
                    existing_type.weight_range_min = weight_range_min
                    existing_type.weight_range_max = weight_range_max
                    existing_type.typical_wears = typical_wears
                    existing_type.wash_frequency = wash_frequency
                    
                    print(f"🔄 Row {row_num}: Updated clothing type '{clothing_type}'")
                    results['updated'] += 1
                else:
                    # Create new clothing type
                    clothing_type_obj = ClothingTypeReference(
                        clothing_type=clothing_type,
                        category=category,
                        typical_weight_grams=typical_weight_grams,
                        weight_range_min=weight_range_min,
                        weight_range_max=weight_range_max,
                        typical_wears=typical_wears,
                        wash_frequency=wash_frequency
                    )
                    
                    session.add(clothing_type_obj)
                    print(f"✅ Row {row_num}: Loaded clothing type '{clothing_type}'")
                    results['loaded'] += 1
                
            except Exception as e:
                print(f"❌ Row {row_num}: Error loading clothing type: {e}")
                results['errors'] += 1
                continue
    
    # Commit all changes
    try:
        session.commit()
        print(f"\n💾 Database changes committed successfully")
    except Exception as e:
        session.rollback()
        print(f"\n❌ Error committing to database: {e}")
        raise
    
    return results

def clear_clothing_types_table(session):
    """Clear all clothing types from the database."""
    try:
        count = session.query(ClothingTypeReference).count()
        session.query(ClothingTypeReference).delete()
        session.commit()
        print(f"🗑️  Cleared {count} existing clothing types from database")
    except Exception as e:
        session.rollback()
        print(f"❌ Error clearing clothing types table: {e}")
        raise

def show_clothing_types_summary(session):
    """Show summary of clothing types in database."""
    clothing_types = session.query(ClothingTypeReference).all()
    
    if not clothing_types:
        print("No clothing types found in database.")
        return
    
    print(f"\n📊 Clothing Types Summary ({len(clothing_types)} total):")
    
    # Group by category
    by_category = {}
    for clothing_type in clothing_types:
        category = clothing_type.category
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(clothing_type)
    
    for category, types_list in by_category.items():
        print(f"\n{category.upper()} ({len(types_list)} types):")
        for clothing_type in types_list:
            weight_info = f"{clothing_type.typical_weight_grams}g"
            if clothing_type.weight_range_min and clothing_type.weight_range_max:
                weight_info += f" ({clothing_type.weight_range_min}-{clothing_type.weight_range_max}g)"
            
            wears_info = ""
            if clothing_type.typical_wears:
                wears_info = f" - ~{clothing_type.typical_wears} wears"
            
            wash_info = ""
            if clothing_type.wash_frequency:
                wash_info = f" - wash every {1/float(clothing_type.wash_frequency):.1f} wears"
            
            print(f"  • {clothing_type.clothing_type} - {weight_info}{wears_info}{wash_info}")

def main():
    parser = argparse.ArgumentParser(description='Load clothing type reference data into database')
    parser.add_argument('--csv-path', help='Path to clothing types CSV file',
                        default=str(Path(__file__).parent.parent.parent / "data" / "clothing_types.csv"))
    parser.add_argument('--update', action='store_true', 
                        help='Update existing clothing types instead of skipping them')
    parser.add_argument('--clear', action='store_true', 
                        help='Clear existing clothing types before loading')
    parser.add_argument('--summary', action='store_true', 
                        help='Show summary of clothing types in database')
    parser.add_argument('--dry-run', action='store_true', 
                        help='Show what would be loaded without actually loading')
    
    args = parser.parse_args()
    
    # Get database session
    try:
        session = get_database_session()
        print(f"🔗 Connected to database")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return
    
    try:
        # Show summary only
        if args.summary:
            show_clothing_types_summary(session)
            return
        
        # Clear existing data if requested
        if args.clear:
            if not args.dry_run:
                confirm = input("⚠️  This will delete all existing clothing types. Continue? (y/N): ")
                if confirm.lower() != 'y':
                    print("Cancelled.")
                    return
                clear_clothing_types_table(session)
            else:
                print("🔍 DRY RUN: Would clear existing clothing types table")
        
        # Load clothing types
        csv_path = Path(args.csv_path)
        
        if args.dry_run:
            print(f"🔍 DRY RUN: Would load clothing types from {csv_path}")
            print(f"Update existing: {args.update}")
            return
        
        results = load_clothing_types_from_csv(csv_path, session, args.update)
        
        # Print summary
        print(f"\n📊 Loading Summary:")
        print(f"✅ Loaded: {results['loaded']}")
        print(f"🔄 Updated: {results['updated']}")
        print(f"⏭️  Skipped: {results['skipped']}")
        print(f"❌ Errors: {results['errors']}")
        
        if results['loaded'] > 0 or results['updated'] > 0:
            print(f"\n🎉 Successfully processed {results['loaded'] + results['updated']} clothing types!")
            
            # Show final summary
            show_clothing_types_summary(session)
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main()