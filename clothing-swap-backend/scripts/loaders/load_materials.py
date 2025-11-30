#!/usr/bin/env python3
"""
Load material reference data from CSV into the database.
Creates MaterialReference records from textile_exchange_materials.csv
"""

import sys
import csv
import argparse
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.database import get_database_session
from app.models.material import MaterialReference

def load_materials_from_csv(csv_path: Path, session, update_existing: bool = False) -> dict:
    """Load materials from CSV file into database."""
    
    if not csv_path.exists():
        raise FileNotFoundError(f"Materials CSV file not found: {csv_path}")
    
    results = {
        'loaded': 0,
        'updated': 0,
        'skipped': 0,
        'errors': 0
    }
    
    print(f"📥 Loading materials from: {csv_path}")
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, 2):  # Start from row 2 (header is row 1)
            try:
                material_name = row.get('material_name', '').strip()
                if not material_name:
                    print(f"⏭️  Row {row_num}: Skipping empty material name")
                    results['skipped'] += 1
                    continue
                
                # Check if material already exists
                existing_material = session.query(MaterialReference).filter(
                    MaterialReference.material_name == material_name
                ).first()
                
                if existing_material and not update_existing:
                    print(f"⏭️  Row {row_num}: Material '{material_name}' already exists, skipping")
                    results['skipped'] += 1
                    continue
                
                # Parse numeric values with defaults
                co2_per_kg = Decimal(row.get('co2_per_kg', '0') or '0')
                water_liters_per_kg = Decimal(row.get('water_liters_per_kg', '0') or '0')
                energy_mj_per_kg = Decimal(row.get('energy_mj_per_kg', '0') or '0')
                land_use_m2_per_kg = None
                if row.get('land_use_m2_per_kg'):
                    try:
                        land_use_m2_per_kg = Decimal(row['land_use_m2_per_kg'])
                    except (ValueError, TypeError):
                        pass
                
                # Parse processing multipliers with defaults
                spinning_multiplier = Decimal(row.get('spinning_multiplier', '0.05') or '0.05')
                weaving_multiplier = Decimal(row.get('weaving_multiplier', '0.08') or '0.08')
                dyeing_multiplier = Decimal(row.get('dyeing_multiplier', '0.25') or '0.25')
                finishing_multiplier = Decimal(row.get('finishing_multiplier', '0.10') or '0.10')
                
                # Parse last updated date
                last_updated = None
                if row.get('last_updated'):
                    try:
                        last_updated = datetime.strptime(row['last_updated'], '%Y-%m-%d').date()
                    except ValueError:
                        try:
                            last_updated = datetime.strptime(row['last_updated'], '%Y-%m-%d %H:%M:%S').date()
                        except ValueError:
                            last_updated = datetime.now().date()
                else:
                    last_updated = datetime.now().date()
                
                if existing_material:
                    # Update existing material
                    existing_material.material_category = row.get('material_category', 'unknown')
                    existing_material.co2_per_kg = co2_per_kg
                    existing_material.water_liters_per_kg = water_liters_per_kg
                    existing_material.energy_mj_per_kg = energy_mj_per_kg
                    existing_material.land_use_m2_per_kg = land_use_m2_per_kg
                    existing_material.spinning_multiplier = spinning_multiplier
                    existing_material.weaving_multiplier = weaving_multiplier
                    existing_material.dyeing_multiplier = dyeing_multiplier
                    existing_material.finishing_multiplier = finishing_multiplier
                    existing_material.production_region = row.get('production_region', 'Global Average')
                    existing_material.data_quality = row.get('data_quality', 'medium')
                    existing_material.last_updated = last_updated
                    
                    print(f"🔄 Row {row_num}: Updated material '{material_name}'")
                    results['updated'] += 1
                else:
                    # Create new material
                    material = MaterialReference(
                        material_name=material_name,
                        material_category=row.get('material_category', 'unknown'),
                        co2_per_kg=co2_per_kg,
                        water_liters_per_kg=water_liters_per_kg,
                        energy_mj_per_kg=energy_mj_per_kg,
                        land_use_m2_per_kg=land_use_m2_per_kg,
                        spinning_multiplier=spinning_multiplier,
                        weaving_multiplier=weaving_multiplier,
                        dyeing_multiplier=dyeing_multiplier,
                        finishing_multiplier=finishing_multiplier,
                        production_region=row.get('production_region', 'Global Average'),
                        data_quality=row.get('data_quality', 'medium'),
                        last_updated=last_updated
                    )
                    
                    session.add(material)
                    print(f"✅ Row {row_num}: Loaded material '{material_name}'")
                    results['loaded'] += 1
                
            except Exception as e:
                print(f"❌ Row {row_num}: Error loading material: {e}")
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

def clear_materials_table(session):
    """Clear all materials from the database."""
    try:
        count = session.query(MaterialReference).count()
        session.query(MaterialReference).delete()
        session.commit()
        print(f"🗑️  Cleared {count} existing materials from database")
    except Exception as e:
        session.rollback()
        print(f"❌ Error clearing materials table: {e}")
        raise

def show_materials_summary(session):
    """Show summary of materials in database."""
    materials = session.query(MaterialReference).all()
    
    if not materials:
        print("No materials found in database.")
        return
    
    print(f"\n📊 Materials Summary ({len(materials)} total):")
    
    # Group by category
    by_category = {}
    for material in materials:
        category = material.material_category
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(material)
    
    for category, materials_list in by_category.items():
        print(f"\n{category.upper()} ({len(materials_list)} materials):")
        for material in materials_list:
            print(f"  • {material.material_name} - {material.co2_per_kg} kg CO2/kg")

def main():
    parser = argparse.ArgumentParser(description='Load material reference data into database')
    parser.add_argument('--csv-path', help='Path to materials CSV file',
                        default=str(Path(__file__).parent.parent.parent / "data" / "textile_exchange_materials.csv"))
    parser.add_argument('--update', action='store_true', 
                        help='Update existing materials instead of skipping them')
    parser.add_argument('--clear', action='store_true', 
                        help='Clear existing materials before loading')
    parser.add_argument('--summary', action='store_true', 
                        help='Show summary of materials in database')
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
            show_materials_summary(session)
            return
        
        # Clear existing data if requested
        if args.clear:
            if not args.dry_run:
                confirm = input("⚠️  This will delete all existing materials. Continue? (y/N): ")
                if confirm.lower() != 'y':
                    print("Cancelled.")
                    return
                clear_materials_table(session)
            else:
                print("🔍 DRY RUN: Would clear existing materials table")
        
        # Load materials
        csv_path = Path(args.csv_path)
        
        if args.dry_run:
            print(f"🔍 DRY RUN: Would load materials from {csv_path}")
            print(f"Update existing: {args.update}")
            return
        
        results = load_materials_from_csv(csv_path, session, args.update)
        
        # Print summary
        print(f"\n📊 Loading Summary:")
        print(f"✅ Loaded: {results['loaded']}")
        print(f"🔄 Updated: {results['updated']}")
        print(f"⏭️  Skipped: {results['skipped']}")
        print(f"❌ Errors: {results['errors']}")
        
        if results['loaded'] > 0 or results['updated'] > 0:
            print(f"\n🎉 Successfully processed {results['loaded'] + results['updated']} materials!")
            
            # Show final summary
            show_materials_summary(session)
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main()