#!/usr/bin/env python3
"""
Script to update brand sustainability data.
Can fetch from WikiRate API or update manually.
"""

import sys
import csv
import json
import argparse
import requests
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

WIKIRATE_BASE_URL = "https://wikirate.org"

def fetch_brand_from_wikirate(brand_name: str) -> Optional[Dict[str, Any]]:
    """Fetch brand data from WikiRate API."""
    try:
        # URL encode brand name
        encoded_name = requests.utils.quote(brand_name)
        url = f"{WIKIRATE_BASE_URL}/{encoded_name}.json"
        
        print(f"🌐 Fetching {brand_name} from WikiRate...")
        response = requests.get(url, params={"view": "company_page"}, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Found {brand_name} on WikiRate")
            return response.json()
        elif response.status_code == 404:
            print(f"❌ Brand '{brand_name}' not found on WikiRate")
            return None
        else:
            print(f"⚠️  Error fetching {brand_name}: HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Exception fetching {brand_name}: {e}")
        return None

def parse_wikirate_response(brand_name: str, api_data: Dict) -> Dict[str, Any]:
    """Parse WikiRate API response to extract relevant fields."""
    # This is a template - WikiRate API structure varies
    # You'll need to adapt based on actual API response structure
    
    parsed = {
        'brand_name': brand_name,
        'brand_name_normalized': brand_name.lower().replace(' ', '').replace('&', ''),
        'transparency_index_score': None,
        'transparency_year': 2024,
        'publishes_supplier_list': False,
        'discloses_ghg_emissions': False,
        'discloses_water_usage': False,
        'has_living_wage_commitment': False,
        'has_climate_targets': False,
        'tier1_suppliers_disclosed': 0,
        'last_updated': datetime.now().strftime('%Y-%m-%d')
    }
    
    # TODO: Adapt this based on actual WikiRate API response structure
    # Example parsing (you'll need to adjust based on real data):
    # if 'transparency_score' in api_data:
    #     parsed['transparency_index_score'] = api_data['transparency_score']
    # if 'disclosures' in api_data:
    #     disclosures = api_data['disclosures']
    #     parsed['publishes_supplier_list'] = disclosures.get('supplier_list', False)
    #     parsed['discloses_ghg_emissions'] = disclosures.get('ghg_emissions', False)
    
    print(f"⚠️  Using template data for {brand_name} - please adapt parsing logic")
    return parsed

def get_manual_brand_data(brand_name: str) -> Dict[str, Any]:
    """Get brand data through manual input."""
    
    data = {
        'brand_name': brand_name,
        'brand_name_normalized': brand_name.lower().replace(' ', '').replace('&', ''),
        'last_updated': datetime.now().strftime('%Y-%m-%d')
    }
    
    print(f"\n📝 Manual entry for '{brand_name}'")
    print("Enter data for this brand (press Enter for defaults):")
    
    # Transparency index score
    score = input("Transparency Index Score (0-100, default 30): ").strip()
    data['transparency_index_score'] = int(score) if score else 30
    
    # Year
    year = input("Data year (default 2024): ").strip()
    data['transparency_year'] = int(year) if year else 2024
    
    # Boolean flags
    print("\nDisclosure flags (y/n, default n):")
    data['publishes_supplier_list'] = input("Publishes supplier list? ").lower().startswith('y')
    data['discloses_ghg_emissions'] = input("Discloses GHG emissions? ").lower().startswith('y')
    data['discloses_water_usage'] = input("Discloses water usage? ").lower().startswith('y')
    data['has_living_wage_commitment'] = input("Has living wage commitment? ").lower().startswith('y')
    data['has_climate_targets'] = input("Has climate targets? ").lower().startswith('y')
    
    # Supplier count
    suppliers = input("Number of Tier 1 suppliers disclosed (default 0): ").strip()
    data['tier1_suppliers_disclosed'] = int(suppliers) if suppliers else 0
    
    return data

def brand_exists_in_csv(brand_name: str, csv_path: Path) -> bool:
    """Check if brand already exists in CSV."""
    if not csv_path.exists():
        return False
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['brand_name'].lower() == brand_name.lower():
                return True
    return False

def update_brand_in_csv(data: Dict[str, Any], csv_path: Path, create_if_missing: bool = True):
    """Update or add brand data in CSV file."""
    
    # Read existing data
    existing_data = []
    headers = ['brand_name', 'brand_name_normalized', 'transparency_index_score', 
               'transparency_year', 'publishes_supplier_list', 'discloses_ghg_emissions',
               'discloses_water_usage', 'has_living_wage_commitment', 'has_climate_targets',
    
    brand_updated = False
    
    if csv_path.exists():
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or headers
            
            for row in reader:
                if row['brand_name'].lower() == data['brand_name'].lower():
                    # Update existing brand
                    existing_data.append(data)
                    brand_updated = True
                    print(f"🔄 Updated existing brand: {data['brand_name']}")
                else:
                    existing_data.append(row)
    
    # Add new brand if not found
    if not brand_updated:
        if create_if_missing:
            existing_data.append(data)
            print(f"➕ Added new brand: {data['brand_name']}")
        else:
            print(f"❌ Brand '{data['brand_name']}' not found and create_if_missing=False")
            return False
    
    # Write back to CSV
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(existing_data)
    
    return True

def show_brand_preview(data: Dict[str, Any]):
    """Show preview of brand data."""
    print(f"\n{'='*60}")
    print("BRAND DATA PREVIEW")
    print(f"{'='*60}")
    print(f"Brand: {data['brand_name']} ({data['brand_name_normalized']})")
    print(f"Transparency Score: {data['transparency_index_score']}/100 ({data['transparency_year']})")
    print(f"Publishes Supplier List: {'Yes' if data['publishes_supplier_list'] else 'No'}")
    print(f"Discloses GHG Emissions: {'Yes' if data['discloses_ghg_emissions'] else 'No'}")
    print(f"Discloses Water Usage: {'Yes' if data['discloses_water_usage'] else 'No'}")
    print(f"Living Wage Commitment: {'Yes' if data['has_living_wage_commitment'] else 'No'}")
    print(f"Climate Targets: {'Yes' if data['has_climate_targets'] else 'No'}")
    print(f"Tier 1 Suppliers Disclosed: {data['tier1_suppliers_disclosed']}")
    print(f"Last Updated: {data['last_updated']}")
    print(f"{'='*60}")

def bulk_update_from_wikirate(brands: list, csv_path: Path, delay: float = 1.0):
    """Update multiple brands from WikiRate API."""
    print(f"\n🚀 Bulk updating {len(brands)} brands from WikiRate")
    print(f"⏱️  Using {delay}s delay between requests")
    
    updated_count = 0
    failed_count = 0
    
    for i, brand_name in enumerate(brands, 1):
        print(f"\n[{i}/{len(brands)}] Processing: {brand_name}")
        
        # Fetch from WikiRate
        api_data = fetch_brand_from_wikirate(brand_name)
        
        if api_data:
            # Parse response
            brand_data = parse_wikirate_response(brand_name, api_data)
            
            # Update CSV
            if update_brand_in_csv(brand_data, csv_path):
                updated_count += 1
            else:
                failed_count += 1
        else:
            print(f"❌ Skipping {brand_name} - no data available")
            failed_count += 1
        
        # Rate limiting
        if i < len(brands):  # Don't delay after last request
            time.sleep(delay)
    
    print(f"\n📊 Bulk update summary:")
    print(f"✅ Updated: {updated_count}")
    print(f"❌ Failed: {failed_count}")

def main():
    parser = argparse.ArgumentParser(description='Update brand sustainability data')
    parser.add_argument('brand_name', nargs='?', help='Brand name to update')
    parser.add_argument('--wikirate', action='store_true', help='Fetch data from WikiRate API')
    parser.add_argument('--manual', action='store_true', help='Enter data manually')
    parser.add_argument('--bulk', help='Bulk update brands from file (one brand per line)')
    parser.add_argument('--list', action='store_true', help='List current brands in CSV')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between API requests (default: 1.0s)')
    parser.add_argument('--yes', action='store_true', help='Skip confirmation prompt')
    
    args = parser.parse_args()
    
    csv_path = Path(__file__).parent.parent.parent / "data" / "brands_sustainability.csv"
    
    # List current brands
    if args.list:
        if csv_path.exists():
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                print("Current brands in database:")
                for i, row in enumerate(reader, 1):
                    print(f"{i:2d}. {row['brand_name']} (Score: {row['transparency_index_score']})")
        else:
            print("No brands CSV file found.")
        return
    
    # Bulk update
    if args.bulk:
        bulk_file = Path(args.bulk)
        if not bulk_file.exists():
            print(f"❌ Bulk file not found: {args.bulk}")
            return
        
        with open(bulk_file, 'r') as f:
            brands = [line.strip() for line in f if line.strip()]
        
        bulk_update_from_wikirate(brands, csv_path, args.delay)
        return
    
    # Single brand update
    if not args.brand_name:
        print("❌ Please provide a brand name or use --list/--bulk options")
        return
    
    brand_name = args.brand_name
    print(f"Updating brand: {brand_name}")
    
    # Get brand data
    if args.wikirate:
        api_data = fetch_brand_from_wikirate(brand_name)
        if api_data:
            brand_data = parse_wikirate_response(brand_name, api_data)
        else:
            print("❌ Could not fetch from WikiRate. Use --manual for manual entry.")
            return
    else:
        # Manual entry (default if no method specified)
        brand_data = get_manual_brand_data(brand_name)
    
    # Show preview
    show_brand_preview(brand_data)
    
    # Confirm
    if not args.yes:
        confirm = input("\nUpdate this brand data? (y/N): ").lower().strip()
        if confirm != 'y':
            print("Cancelled.")
            return
    
    # Update CSV
    success = update_brand_in_csv(brand_data, csv_path)
    
    if success:
        print(f"\n🎉 Successfully updated '{brand_name}'!")
        print("\nNext steps:")
        print("1. Review the data in: data/brands_sustainability.csv")
        print("2. Run database loader: python scripts/load_brands.py")

if __name__ == "__main__":
    main()