#!/usr/bin/env python3
"""
Load brand sustainability data from CSV into the database.
Creates BrandSustainability records from brands_sustainability.csv
"""

import sys
import csv
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.database import get_database_session
from app.models.brand import BrandSustainability

def parse_boolean(value: str) -> bool:
    """Parse various boolean representations."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ['true', '1', 'yes', 'y']
    return False

def load_brands_from_csv(csv_path: Path, session, update_existing: bool = False) -> dict:
    """Load brands from CSV file into database."""
    
    if not csv_path.exists():
        raise FileNotFoundError(f"Brands CSV file not found: {csv_path}")
    
    results = {
        'loaded': 0,
        'updated': 0,
        'skipped': 0,
        'errors': 0
    }
    
    print(f"📥 Loading brands from: {csv_path}")
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, 2):  # Start from row 2 (header is row 1)
            try:
                brand_name = row.get('brand_name', '').strip()
                if not brand_name:
                    print(f"⏭️  Row {row_num}: Skipping empty brand name")
                    results['skipped'] += 1
                    continue
                
                # Check if brand already exists
                existing_brand = session.query(BrandSustainability).filter(
                    BrandSustainability.brand_name == brand_name
                ).first()
                
                if existing_brand and not update_existing:
                    print(f"⏭️  Row {row_num}: Brand '{brand_name}' already exists, skipping")
                    results['skipped'] += 1
                    continue
                
                # Parse normalized brand name
                brand_name_normalized = row.get('brand_name_normalized', 
                                                 brand_name.lower().replace(' ', '').replace('&', ''))
                
                # Parse transparency score
                transparency_index_score = None
                if row.get('transparency_index_score'):
                    try:
                        transparency_index_score = int(row['transparency_index_score'])
                    except (ValueError, TypeError):
                        pass
                
                # Parse transparency year
                transparency_year = None
                if row.get('transparency_year'):
                    try:
                        transparency_year = int(row['transparency_year'])
                    except (ValueError, TypeError):
                        transparency_year = 2024  # Default to current year
                else:
                    transparency_year = 2024
                
                # Parse boolean fields
                publishes_supplier_list = parse_boolean(row.get('publishes_supplier_list', 'false'))
                discloses_ghg_emissions = parse_boolean(row.get('discloses_ghg_emissions', 'false'))
                discloses_water_usage = parse_boolean(row.get('discloses_water_usage', 'false'))
                has_living_wage_commitment = parse_boolean(row.get('has_living_wage_commitment', 'false'))
                has_climate_targets = parse_boolean(row.get('has_climate_targets', 'false'))
                
                # Parse tier1 suppliers count
                tier1_suppliers_disclosed = None
                if row.get('tier1_suppliers_disclosed'):
                    try:
                        tier1_suppliers_disclosed = int(row['tier1_suppliers_disclosed'])
                    except (ValueError, TypeError):
                        tier1_suppliers_disclosed = 0
                else:
                    tier1_suppliers_disclosed = 0
                
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
                
                if existing_brand:
                    # Update existing brand
                    existing_brand.brand_name_normalized = brand_name_normalized
                    existing_brand.transparency_index_score = transparency_index_score
                    existing_brand.transparency_year = transparency_year
                    existing_brand.publishes_supplier_list = publishes_supplier_list
                    existing_brand.discloses_ghg_emissions = discloses_ghg_emissions
                    existing_brand.discloses_water_usage = discloses_water_usage
                    existing_brand.has_living_wage_commitment = has_living_wage_commitment
                    existing_brand.has_climate_targets = has_climate_targets
                    existing_brand.tier1_suppliers_disclosed = tier1_suppliers_disclosed
                    existing_brand.last_updated = last_updated
                    
                    print(f"🔄 Row {row_num}: Updated brand '{brand_name}'")
                    results['updated'] += 1
                else:
                    # Create new brand
                    brand = BrandSustainability(
                        brand_name=brand_name,
                        brand_name_normalized=brand_name_normalized,
                        transparency_index_score=transparency_index_score,
                        transparency_year=transparency_year,
                        publishes_supplier_list=publishes_supplier_list,
                        discloses_ghg_emissions=discloses_ghg_emissions,
                        discloses_water_usage=discloses_water_usage,
                        has_living_wage_commitment=has_living_wage_commitment,
                        has_climate_targets=has_climate_targets,
                        tier1_suppliers_disclosed=tier1_suppliers_disclosed,
                        last_updated=last_updated
                    )
                    
                    session.add(brand)
                    print(f"✅ Row {row_num}: Loaded brand '{brand_name}'")
                    results['loaded'] += 1
                
            except Exception as e:
                print(f"❌ Row {row_num}: Error loading brand: {e}")
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

def clear_brands_table(session):
    """Clear all brands from the database."""
    try:
        count = session.query(BrandSustainability).count()
        session.query(BrandSustainability).delete()
        session.commit()
        print(f"🗑️  Cleared {count} existing brands from database")
    except Exception as e:
        session.rollback()
        print(f"❌ Error clearing brands table: {e}")
        raise

def show_brands_summary(session):
    """Show summary of brands in database."""
    brands = session.query(BrandSustainability).order_by(
        BrandSustainability.transparency_index_score.desc().nullslast()
    ).all()
    
    if not brands:
        print("No brands found in database.")
        return
    
    print(f"\n📊 Brands Summary ({len(brands)} total):")
    
    # Calculate sustainability metrics
    total_with_score = len([b for b in brands if b.transparency_index_score is not None])
    avg_score = None
    if total_with_score > 0:
        avg_score = sum(b.transparency_index_score for b in brands if b.transparency_index_score is not None) / total_with_score
    
    supplier_disclosers = len([b for b in brands if b.publishes_supplier_list])
    ghg_disclosers = len([b for b in brands if b.discloses_ghg_emissions])
    climate_commitments = len([b for b in brands if b.has_climate_targets])
    living_wage_commitments = len([b for b in brands if b.has_living_wage_commitment])
    
    print(f"\n🏆 Transparency Metrics:")
    if avg_score:
        print(f"  • Average transparency score: {avg_score:.1f}/100 ({total_with_score} brands)")
    print(f"  • Supplier list disclosure: {supplier_disclosers}/{len(brands)} ({supplier_disclosers/len(brands)*100:.1f}%)")
    print(f"  • GHG emissions disclosure: {ghg_disclosers}/{len(brands)} ({ghg_disclosers/len(brands)*100:.1f}%)")
    print(f"  • Climate targets: {climate_commitments}/{len(brands)} ({climate_commitments/len(brands)*100:.1f}%)")
    print(f"  • Living wage commitment: {living_wage_commitments}/{len(brands)} ({living_wage_commitments/len(brands)*100:.1f}%)")
    
    print(f"\n📋 Brand Details:")
    for brand in brands[:15]:  # Show top 15 brands
        score_text = f"{brand.transparency_index_score}/100" if brand.transparency_index_score else "No score"
        
        features = []
        if brand.publishes_supplier_list:
            features.append("Suppliers")
        if brand.discloses_ghg_emissions:
            features.append("GHG")
        if brand.has_climate_targets:
            features.append("Climate")
        if brand.has_living_wage_commitment:
            features.append("Living Wage")
        
        features_text = f" [{', '.join(features)}]" if features else ""
        
        print(f"  • {brand.brand_name} - {score_text}{features_text}")
    
    if len(brands) > 15:
        print(f"  ... and {len(brands) - 15} more brands")

def main():
    parser = argparse.ArgumentParser(description='Load brand sustainability data into database')
    parser.add_argument('--csv-path', help='Path to brands CSV file',
                        default=str(Path(__file__).parent.parent.parent / "data" / "brands_sustainability.csv"))
    parser.add_argument('--update', action='store_true', 
                        help='Update existing brands instead of skipping them')
    parser.add_argument('--clear', action='store_true', 
                        help='Clear existing brands before loading')
    parser.add_argument('--summary', action='store_true', 
                        help='Show summary of brands in database')
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
            show_brands_summary(session)
            return
        
        # Clear existing data if requested
        if args.clear:
            if not args.dry_run:
                confirm = input("⚠️  This will delete all existing brands. Continue? (y/N): ")
                if confirm.lower() != 'y':
                    print("Cancelled.")
                    return
                clear_brands_table(session)
            else:
                print("🔍 DRY RUN: Would clear existing brands table")
        
        # Load brands
        csv_path = Path(args.csv_path)
        
        if args.dry_run:
            print(f"🔍 DRY RUN: Would load brands from {csv_path}")
            print(f"Update existing: {args.update}")
            return
        
        results = load_brands_from_csv(csv_path, session, args.update)
        
        # Print summary
        print(f"\n📊 Loading Summary:")
        print(f"✅ Loaded: {results['loaded']}")
        print(f"🔄 Updated: {results['updated']}")
        print(f"⏭️  Skipped: {results['skipped']}")
        print(f"❌ Errors: {results['errors']}")
        
        if results['loaded'] > 0 or results['updated'] > 0:
            print(f"\n🎉 Successfully processed {results['loaded'] + results['updated']} brands!")
            
            # Show final summary
            show_brands_summary(session)
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main()