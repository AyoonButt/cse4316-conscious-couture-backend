#!/usr/bin/env python3
"""
Bulk import script for reference data.
Can import from CSV/Excel files for materials, clothing types, brands, or parameters.
"""

import sys
import csv
import json
import argparse
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

def validate_material_data(row: Dict[str, Any]) -> Dict[str, str]:
    """Validate material data row. Returns dict of errors."""
    errors = {}
    
    required_fields = ['material_name', 'material_category', 'co2_per_kg']
    for field in required_fields:
        if not row.get(field):
            errors[field] = f"Required field '{field}' is missing"
    
    # Validate numeric fields
    numeric_fields = ['co2_per_kg', 'water_liters_per_kg', 'energy_mj_per_kg', 
                      'spinning_multiplier', 'weaving_multiplier', 'dyeing_multiplier', 'finishing_multiplier']
    
    for field in numeric_fields:
        if row.get(field) and row[field] != '':
            try:
                float(row[field])
            except (ValueError, TypeError):
                errors[field] = f"'{field}' must be a number"
    
    # Validate category
    valid_categories = ['natural', 'synthetic', 'cellulosic']
    if row.get('material_category') and row['material_category'] not in valid_categories:
        errors['material_category'] = f"Category must be one of: {valid_categories}"
    
    return errors

def validate_clothing_type_data(row: Dict[str, Any]) -> Dict[str, str]:
    """Validate clothing type data row. Returns dict of errors."""
    errors = {}
    
    required_fields = ['clothing_type', 'category', 'typical_weight_grams']
    for field in required_fields:
        if not row.get(field):
            errors[field] = f"Required field '{field}' is missing"
    
    # Validate numeric fields
    numeric_fields = ['typical_weight_grams', 'weight_range_min', 'weight_range_max', 'typical_wears']
    for field in numeric_fields:
        if row.get(field) and row[field] != '':
            try:
                int(row[field])
            except (ValueError, TypeError):
                errors[field] = f"'{field}' must be an integer"
    
    # Validate wash frequency
    if row.get('wash_frequency'):
        try:
            freq = float(row['wash_frequency'])
            if not (0 < freq <= 1.0):
                errors['wash_frequency'] = "wash_frequency must be between 0 and 1.0"
        except (ValueError, TypeError):
            errors['wash_frequency'] = "wash_frequency must be a number"
    
    # Validate category
    valid_categories = ['tops', 'bottoms', 'dresses', 'outerwear', 'accessories']
    if row.get('category') and row['category'] not in valid_categories:
        errors['category'] = f"Category must be one of: {valid_categories}"
    
    return errors

def validate_brand_data(row: Dict[str, Any]) -> Dict[str, str]:
    """Validate brand data row. Returns dict of errors."""
    errors = {}
    
    required_fields = ['brand_name']
    for field in required_fields:
        if not row.get(field):
            errors[field] = f"Required field '{field}' is missing"
    
    # Validate transparency score
    if row.get('transparency_index_score'):
        try:
            score = int(row['transparency_index_score'])
            if not (0 <= score <= 100):
                errors['transparency_index_score'] = "transparency_index_score must be between 0 and 100"
        except (ValueError, TypeError):
            errors['transparency_index_score'] = "transparency_index_score must be an integer"
    
    # Validate boolean fields
    boolean_fields = ['publishes_supplier_list', 'discloses_ghg_emissions', 'discloses_water_usage',
                      'has_living_wage_commitment', 'has_climate_targets']
    
    for field in boolean_fields:
        if row.get(field) and row[field] not in ['true', 'false', 'True', 'False', '1', '0', '', True, False]:
            errors[field] = f"'{field}' must be true/false"
    
    return errors

def validate_parameter_data(row: Dict[str, Any]) -> Dict[str, str]:
    """Validate parameter data row. Returns dict of errors."""
    errors = {}
    
    required_fields = ['parameter_name', 'parameter_value']
    for field in required_fields:
        if not row.get(field):
            errors[field] = f"Required field '{field}' is missing"
    
    # Validate parameter value
    if row.get('parameter_value'):
        try:
            float(row['parameter_value'])
        except (ValueError, TypeError):
            errors['parameter_value'] = "parameter_value must be a number"
    
    return errors

def normalize_boolean(value: Any) -> bool:
    """Convert various boolean representations to Python bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ['true', '1', 'yes', 'y']
    if isinstance(value, (int, float)):
        return bool(value)
    return False

def import_materials(file_path: Path, target_csv: Path, validate: bool = True) -> Dict[str, int]:
    """Import materials from file."""
    print(f"📥 Importing materials from: {file_path}")
    
    # Read file
    if file_path.suffix.lower() in ['.xlsx', '.xls']:
        df = pd.read_excel(file_path)
        data = df.to_dict('records')
    elif file_path.suffix.lower() == '.csv':
        with open(file_path, 'r') as f:
            data = list(csv.DictReader(f))
    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}")
    
    results = {'imported': 0, 'errors': 0, 'skipped': 0}
    existing_data = []
    
    # Read existing CSV if it exists
    if target_csv.exists():
        with open(target_csv, 'r') as f:
            existing_data = list(csv.DictReader(f))
    
    existing_materials = {row['material_name'].lower() for row in existing_data}
    
    for i, row in enumerate(data, 1):
        if validate:
            errors = validate_material_data(row)
            if errors:
                print(f"❌ Row {i}: {errors}")
                results['errors'] += 1
                continue
        
        # Check for duplicates
        material_name = row['material_name'].lower().replace(' ', '_')
        if material_name in existing_materials:
            print(f"⏭️  Row {i}: Material '{material_name}' already exists, skipping")
            results['skipped'] += 1
            continue
        
        # Normalize data
        row['material_name'] = material_name
        row['last_updated'] = row.get('last_updated', datetime.now().strftime('%Y-%m-%d'))
        
        existing_data.append(row)
        existing_materials.add(material_name)
        results['imported'] += 1
        print(f"✅ Row {i}: Added '{material_name}'")
    
    # Write updated CSV
    if results['imported'] > 0:
        headers = ['material_name', 'material_category', 'co2_per_kg', 'water_liters_per_kg',
                   'energy_mj_per_kg', 'land_use_m2_per_kg', 'spinning_multiplier', 
                   'weaving_multiplier', 'dyeing_multiplier', 'finishing_multiplier',
        
        with open(target_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(existing_data)
    
    return results

def import_clothing_types(file_path: Path, target_csv: Path, validate: bool = True) -> Dict[str, int]:
    """Import clothing types from file."""
    print(f"📥 Importing clothing types from: {file_path}")
    
    # Read file
    if file_path.suffix.lower() in ['.xlsx', '.xls']:
        df = pd.read_excel(file_path)
        data = df.to_dict('records')
    elif file_path.suffix.lower() == '.csv':
        with open(file_path, 'r') as f:
            data = list(csv.DictReader(f))
    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}")
    
    results = {'imported': 0, 'errors': 0, 'skipped': 0}
    existing_data = []
    
    # Read existing CSV if it exists
    if target_csv.exists():
        with open(target_csv, 'r') as f:
            existing_data = list(csv.DictReader(f))
    
    existing_types = {row['clothing_type'].lower() for row in existing_data}
    
    for i, row in enumerate(data, 1):
        if validate:
            errors = validate_clothing_type_data(row)
            if errors:
                print(f"❌ Row {i}: {errors}")
                results['errors'] += 1
                continue
        
        # Check for duplicates
        clothing_type = row['clothing_type'].lower().replace(' ', '_')
        if clothing_type in existing_types:
            print(f"⏭️  Row {i}: Clothing type '{clothing_type}' already exists, skipping")
            results['skipped'] += 1
            continue
        
        # Normalize data
        row['clothing_type'] = clothing_type
        
        existing_data.append(row)
        existing_types.add(clothing_type)
        results['imported'] += 1
        print(f"✅ Row {i}: Added '{clothing_type}'")
    
    # Write updated CSV
    if results['imported'] > 0:
        headers = ['clothing_type', 'category', 'typical_weight_grams', 'weight_range_min',
                   'weight_range_max', 'typical_wears', 'wash_frequency']
        
        with open(target_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(existing_data)
    
    return results

def import_brands(file_path: Path, target_csv: Path, validate: bool = True) -> Dict[str, int]:
    """Import brands from file."""
    print(f"📥 Importing brands from: {file_path}")
    
    # Read file
    if file_path.suffix.lower() in ['.xlsx', '.xls']:
        df = pd.read_excel(file_path)
        data = df.to_dict('records')
    elif file_path.suffix.lower() == '.csv':
        with open(file_path, 'r') as f:
            data = list(csv.DictReader(f))
    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}")
    
    results = {'imported': 0, 'errors': 0, 'skipped': 0}
    existing_data = []
    
    # Read existing CSV if it exists
    if target_csv.exists():
        with open(target_csv, 'r') as f:
            existing_data = list(csv.DictReader(f))
    
    existing_brands = {row['brand_name'].lower() for row in existing_data}
    
    for i, row in enumerate(data, 1):
        if validate:
            errors = validate_brand_data(row)
            if errors:
                print(f"❌ Row {i}: {errors}")
                results['errors'] += 1
                continue
        
        # Check for duplicates
        brand_name = row['brand_name']
        if brand_name.lower() in existing_brands:
            print(f"⏭️  Row {i}: Brand '{brand_name}' already exists, skipping")
            results['skipped'] += 1
            continue
        
        # Normalize data
        row['brand_name_normalized'] = brand_name.lower().replace(' ', '').replace('&', '')
        row['last_updated'] = row.get('last_updated', datetime.now().strftime('%Y-%m-%d'))
        
        # Normalize boolean fields
        boolean_fields = ['publishes_supplier_list', 'discloses_ghg_emissions', 'discloses_water_usage',
                          'has_living_wage_commitment', 'has_climate_targets']
        for field in boolean_fields:
            if field in row:
                row[field] = normalize_boolean(row[field])
        
        existing_data.append(row)
        existing_brands.add(brand_name.lower())
        results['imported'] += 1
        print(f"✅ Row {i}: Added '{brand_name}'")
    
    # Write updated CSV
    if results['imported'] > 0:
        headers = ['brand_name', 'brand_name_normalized', 'transparency_index_score',
                   'transparency_year', 'publishes_supplier_list', 'discloses_ghg_emissions',
                   'discloses_water_usage', 'has_living_wage_commitment', 'has_climate_targets',
        
        with open(target_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(existing_data)
    
    return results

def import_parameters(file_path: Path, target_json: Path, validate: bool = True) -> Dict[str, int]:
    """Import parameters from file."""
    print(f"📥 Importing parameters from: {file_path}")
    
    # Read file
    if file_path.suffix.lower() in ['.xlsx', '.xls']:
        df = pd.read_excel(file_path)
        data = df.to_dict('records')
    elif file_path.suffix.lower() == '.csv':
        with open(file_path, 'r') as f:
            data = list(csv.DictReader(f))
    elif file_path.suffix.lower() == '.json':
        with open(file_path, 'r') as f:
            data = json.load(f)
    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}")
    
    results = {'imported': 0, 'errors': 0, 'skipped': 0}
    existing_data = []
    
    # Read existing JSON if it exists
    if target_json.exists():
        with open(target_json, 'r') as f:
            existing_data = json.load(f)
    
    existing_params = {param['parameter_name'].lower() for param in existing_data}
    
    for i, row in enumerate(data, 1):
        if validate:
            errors = validate_parameter_data(row)
            if errors:
                print(f"❌ Row {i}: {errors}")
                results['errors'] += 1
                continue
        
        # Check for duplicates
        param_name = row['parameter_name']
        if param_name.lower() in existing_params:
            print(f"⏭️  Row {i}: Parameter '{param_name}' already exists, skipping")
            results['skipped'] += 1
            continue
        
        # Normalize data
        row['last_updated'] = row.get('last_updated', datetime.now().strftime('%Y-%m-%d'))
        
        existing_data.append(row)
        existing_params.add(param_name.lower())
        results['imported'] += 1
        print(f"✅ Row {i}: Added '{param_name}'")
    
    # Write updated JSON
    if results['imported'] > 0:
        with open(target_json, 'w') as f:
            json.dump(existing_data, f, indent=2)
    
    return results

def main():
    parser = argparse.ArgumentParser(description='Bulk import reference data')
    parser.add_argument('data_type', choices=['materials', 'clothing_types', 'brands', 'parameters'],
                        help='Type of data to import')
    parser.add_argument('file_path', help='Path to CSV/Excel file to import')
    parser.add_argument('--no-validate', action='store_true', help='Skip data validation')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be imported without actually importing')
    
    args = parser.parse_args()
    
    file_path = Path(args.file_path)
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return
    
    data_dir = Path(__file__).parent.parent.parent / "data"
    
    # Determine target file
    target_files = {
        'materials': data_dir / "textile_exchange_materials.csv",
        'clothing_types': data_dir / "clothing_types.csv", 
        'brands': data_dir / "brands_sustainability.csv",
        'parameters': data_dir / "calculation_parameters.json"
    }
    
    target_file = target_files[args.data_type]
    validate = not args.no_validate
    
    print(f"📋 Bulk import settings:")
    print(f"   Data type: {args.data_type}")
    print(f"   Source file: {file_path}")
    print(f"   Target file: {target_file}")
    print(f"   Validation: {'Enabled' if validate else 'Disabled'}")
    print(f"   Dry run: {'Yes' if args.dry_run else 'No'}")
    
    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made")
    
    # Import based on data type
    try:
        if args.data_type == 'materials':
            results = import_materials(file_path, target_file, validate)
        elif args.data_type == 'clothing_types':
            results = import_clothing_types(file_path, target_file, validate)
        elif args.data_type == 'brands':
            results = import_brands(file_path, target_file, validate)
        elif args.data_type == 'parameters':
            results = import_parameters(file_path, target_file, validate)
        
        # Show summary
        print(f"\n📊 Import Summary:")
        print(f"✅ Imported: {results['imported']}")
        print(f"⏭️  Skipped: {results['skipped']}")
        print(f"❌ Errors: {results['errors']}")
        
        if results['imported'] > 0:
            print(f"\n🎉 Successfully imported {results['imported']} records!")
            print(f"Next step: Run the appropriate loader script to update the database")
        
    except Exception as e:
        print(f"❌ Import failed: {e}")

if __name__ == "__main__":
    main()