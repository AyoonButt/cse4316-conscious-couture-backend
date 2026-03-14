#!/usr/bin/env python3
"""
Script to update material data from Textile Exchange or manual entry.
Can add new materials or update existing ones with latest impact factors.
"""

import sys
import csv
import argparse
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

def get_manual_material_data(material_name: str) -> Dict[str, Any]:
    """Get material data through manual input."""
    
    data = {
        'material_name': material_name.lower().replace(' ', '_'),
        'data_quality': 'medium',
        'last_updated': datetime.now().strftime('%Y-%m-%d')
    }
    
    print(f"\n📝 Manual entry for '{material_name}'")
    
    # Material category
    print("\nAvailable categories:")
    print("1. natural (cotton, wool, silk, linen, hemp)")
    print("2. synthetic (polyester, nylon, acrylic, elastane)")
    print("3. cellulosic (viscose, rayon, modal, lyocell)")
    
    category_map = {'1': 'natural', '2': 'synthetic', '3': 'cellulosic'}
    category_choice = input("Select category (1-3) or enter custom: ").strip()
    data['material_category'] = category_map.get(category_choice, category_choice)
    
    # Environmental impact factors
    print(f"\n🌍 Environmental impact factors for {material_name}")
    print("Guidelines for CO2 per kg:")
    print("- Low impact: 1-3 kg CO2/kg (hemp, linen, recycled materials)")
    print("- Medium impact: 3-7 kg CO2/kg (cotton, viscose, polyester)")
    print("- High impact: 7-15+ kg CO2/kg (wool, silk, virgin synthetics)")
    
    co2 = input("CO2 emissions per kg (kg CO2-eq/kg): ").strip()
    data['co2_per_kg'] = float(co2) if co2 else 5.0
    
    print("\nGuidelines for water usage:")
    print("- Low water: 50-500 L/kg (synthetics, hemp)")
    print("- Medium water: 500-3000 L/kg (linen, silk)")
    print("- High water: 3000-15000 L/kg (cotton, wool)")
    
    water = input("Water usage per kg (liters/kg): ").strip()
    data['water_liters_per_kg'] = float(water) if water else 2000.0
    
    print("\nGuidelines for energy usage:")
    print("- Low energy: 20-50 MJ/kg (natural fibers)")
    print("- Medium energy: 50-100 MJ/kg (processed naturals)")
    print("- High energy: 100-200 MJ/kg (synthetics, intensive processing)")
    
    energy = input("Energy usage per kg (MJ/kg): ").strip()
    data['energy_mj_per_kg'] = float(energy) if energy else 60.0
    
    # Optional land use
    land_use = input("Land use per kg (m²/kg, optional): ").strip()
    data['land_use_m2_per_kg'] = float(land_use) if land_use else None
    
    # Processing multipliers (use defaults if not provided)
    print(f"\nProcessing stage multipliers (press Enter for defaults):")
    print("These represent additional impact from processing stages")
    
    spinning = input("Spinning multiplier (default 0.05): ").strip()
    data['spinning_multiplier'] = float(spinning) if spinning else 0.05
    
    weaving = input("Weaving multiplier (default 0.08): ").strip()
    data['weaving_multiplier'] = float(weaving) if weaving else 0.08
    
    dyeing = input("Dyeing multiplier (default 0.25): ").strip()
    data['dyeing_multiplier'] = float(dyeing) if dyeing else 0.25
    
    finishing = input("Finishing multiplier (default 0.10): ").strip()
    data['finishing_multiplier'] = float(finishing) if finishing else 0.10
    
    # Production region and data quality
    region = input("Production region (default 'Global Average'): ").strip()
    data['production_region'] = region or 'Global Average'
    
    print("\nData quality options:")
    print("- high: Peer-reviewed LCA studies")
    print("- medium: Industry reports, estimates")
    print("- low: Rough estimates, incomplete data")
    
    quality = input("Data quality (high/medium/low, default medium): ").strip()
    data['data_quality'] = quality if quality in ['high', 'medium', 'low'] else 'medium'
    
    
    return data

def import_from_textile_exchange(excel_path: Path) -> list:
    """Import materials from Textile Exchange Excel file."""
    print(f"📊 Importing from Textile Exchange file: {excel_path}")
    
    try:
        # Try to read Excel file (adapt based on actual structure)
        df = pd.read_excel(excel_path)
        
        print("📋 Excel file structure:")
        print(f"Columns: {list(df.columns)}")
        print(f"Rows: {len(df)}")
        
        # TODO: Adapt this mapping based on actual Textile Exchange file structure
        print("\n⚠️  Please adapt the column mapping in this script based on your Excel file structure")
        
        # Example mapping (you'll need to customize this)
        materials = []
        for _, row in df.iterrows():
            # Adapt these column names to match your Excel file
            material = {
                'material_name': row.get('Material', '').lower().replace(' ', '_'),
                'material_category': 'unknown',  # Determine from material name
                'co2_per_kg': row.get('GWP (kg CO2-eq)', 0),
                'water_liters_per_kg': row.get('Water Use (L)', 0),
                'energy_mj_per_kg': row.get('Energy (MJ)', 0),
                'spinning_multiplier': 0.05,
                'weaving_multiplier': 0.08,
                'dyeing_multiplier': 0.25,
                'finishing_multiplier': 0.10,
                'production_region': 'Global Average',
                'data_quality': 'high',
                'last_updated': datetime.now().strftime('%Y-%m-%d')
            }
            
            if material['material_name']:  # Skip empty rows
                materials.append(material)
        
        print(f"✅ Parsed {len(materials)} materials from Excel file")
        return materials
        
    except Exception as e:
        print(f"❌ Error reading Excel file: {e}")
        return []

def material_exists_in_csv(material_name: str, csv_path: Path) -> bool:
    """Check if material already exists in CSV."""
    if not csv_path.exists():
        return False
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['material_name'].lower() == material_name.lower():
                return True
    return False

def update_material_in_csv(data: Dict[str, Any], csv_path: Path, create_if_missing: bool = True):
    """Update or add material data in CSV file."""
    
    # Read existing data
    existing_data = []
    headers = ['material_name', 'material_category', 'co2_per_kg', 'water_liters_per_kg',
               'energy_mj_per_kg', 'land_use_m2_per_kg', 'spinning_multiplier', 
               'weaving_multiplier', 'dyeing_multiplier', 'finishing_multiplier',
    
    material_updated = False
    
    if csv_path.exists():
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or headers
            
            for row in reader:
                if row['material_name'].lower() == data['material_name'].lower():
                    # Update existing material
                    existing_data.append(data)
                    material_updated = True
                    print(f"🔄 Updated existing material: {data['material_name']}")
                else:
                    existing_data.append(row)
    
    # Add new material if not found
    if not material_updated:
        if create_if_missing:
            existing_data.append(data)
            print(f"➕ Added new material: {data['material_name']}")
        else:
            print(f"❌ Material '{data['material_name']}' not found and create_if_missing=False")
            return False
    
    # Write back to CSV
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(existing_data)
    
    return True

def show_material_preview(data: Dict[str, Any]):
    """Show preview of material data."""
    print(f"\n{'='*60}")
    print("MATERIAL DATA PREVIEW")
    print(f"{'='*60}")
    print(f"Material: {data['material_name']} ({data['material_category']})")
    print(f"CO2 Impact: {data['co2_per_kg']} kg CO2-eq/kg")
    print(f"Water Usage: {data['water_liters_per_kg']} L/kg")
    print(f"Energy Usage: {data['energy_mj_per_kg']} MJ/kg")
    if data.get('land_use_m2_per_kg'):
        print(f"Land Use: {data['land_use_m2_per_kg']} m²/kg")
    print(f"Processing Multipliers: {data['spinning_multiplier']:.3f} / {data['weaving_multiplier']:.3f} / {data['dyeing_multiplier']:.3f} / {data['finishing_multiplier']:.3f}")
    print(f"Production Region: {data['production_region']}")
    print(f"Data Quality: {data['data_quality']}")
    print(f"Last Updated: {data['last_updated']}")
    print(f"{'='*60}")

def bulk_update_materials(materials_data: list, csv_path: Path):
    """Update multiple materials at once."""
    print(f"\n🚀 Bulk updating {len(materials_data)} materials")
    
    updated_count = 0
    failed_count = 0
    
    for i, material_data in enumerate(materials_data, 1):
        print(f"\n[{i}/{len(materials_data)}] Processing: {material_data['material_name']}")
        
        if update_material_in_csv(material_data, csv_path):
            updated_count += 1
        else:
            failed_count += 1
    
    print(f"\n📊 Bulk update summary:")
    print(f"✅ Updated: {updated_count}")
    print(f"❌ Failed: {failed_count}")

def main():
    parser = argparse.ArgumentParser(description='Update material data')
    parser.add_argument('material_name', nargs='?', help='Material name to update')
    parser.add_argument('--excel', help='Import from Textile Exchange Excel file')
    parser.add_argument('--manual', action='store_true', help='Enter data manually')
    parser.add_argument('--list', action='store_true', help='List current materials in CSV')
    parser.add_argument('--yes', action='store_true', help='Skip confirmation prompt')
    
    args = parser.parse_args()
    
    csv_path = Path(__file__).parent.parent.parent / "data" / "textile_exchange_materials.csv"
    
    # List current materials
    if args.list:
        if csv_path.exists():
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                print("Current materials in database:")
                for i, row in enumerate(reader, 1):
                    print(f"{i:2d}. {row['material_name']} ({row['material_category']}) - {row['co2_per_kg']} kg CO2/kg")
        else:
            print("No materials CSV file found.")
        return
    
    # Import from Excel
    if args.excel:
        excel_path = Path(args.excel)
        if not excel_path.exists():
            print(f"❌ Excel file not found: {args.excel}")
            return
        
        materials_data = import_from_textile_exchange(excel_path)
        if materials_data:
            bulk_update_materials(materials_data, csv_path)
        return
    
    # Single material update
    if not args.material_name:
        print("❌ Please provide a material name or use --list/--excel options")
        return
    
    material_name = args.material_name
    print(f"Updating material: {material_name}")
    
    # Get material data (manual entry)
    material_data = get_manual_material_data(material_name)
    
    # Show preview
    show_material_preview(material_data)
    
    # Confirm
    if not args.yes:
        confirm = input("\nUpdate this material data? (y/N): ").lower().strip()
        if confirm != 'y':
            print("Cancelled.")
            return
    
    # Update CSV
    success = update_material_in_csv(material_data, csv_path)
    
    if success:
        print(f"\n🎉 Successfully updated '{material_name}'!")
        print("\nNext steps:")
        print("1. Review the data in: data/textile_exchange_materials.csv")
        print("2. Run database loader: python scripts/load_materials.py")

if __name__ == "__main__":
    main()