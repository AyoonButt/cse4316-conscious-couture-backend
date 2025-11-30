#!/usr/bin/env python3
"""
Data validation script for reference data files.
Validates data integrity, consistency, and completeness across all data files.
"""

import sys
import csv
import json
import argparse
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from collections import Counter

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

class DataValidator:
    """Comprehensive data validator for all reference data files."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.errors = []
        self.warnings = []
        
        # Define expected file paths
        self.files = {
            'materials': data_dir / "textile_exchange_materials.csv",
            'clothing_types': data_dir / "clothing_types.csv", 
            'brands': data_dir / "brands_sustainability.csv",
            'parameters': data_dir / "calculation_parameters.json"
        }
    
    def add_error(self, category: str, message: str):
        """Add validation error."""
        self.errors.append(f"❌ [{category}] {message}")
    
    def add_warning(self, category: str, message: str):
        """Add validation warning."""
        self.warnings.append(f"⚠️  [{category}] {message}")
    
    def validate_materials(self) -> bool:
        """Validate materials data."""
        if not self.files['materials'].exists():
            self.add_error("Materials", "File not found: textile_exchange_materials.csv")
            return False
        
        try:
            with open(self.files['materials'], 'r') as f:
                reader = csv.DictReader(f)
                materials = list(reader)
            
            if not materials:
                self.add_error("Materials", "No materials found in CSV")
                return False
            
            # Check required fields
            required_fields = ['material_name', 'material_category', 'co2_per_kg']
            for i, material in enumerate(materials, 2):  # Start from row 2 (header is row 1)
                # Required fields
                for field in required_fields:
                    if not material.get(field):
                        self.add_error("Materials", f"Row {i}: Missing required field '{field}'")
                
                # Validate material name format
                if material.get('material_name'):
                    name = material['material_name']
                    if ' ' in name or name != name.lower():
                        self.add_warning("Materials", f"Row {i}: Material name '{name}' should be lowercase with underscores")
                
                # Validate category
                valid_categories = ['natural', 'synthetic', 'cellulosic']
                if material.get('material_category') and material['material_category'] not in valid_categories:
                    self.add_error("Materials", f"Row {i}: Invalid category '{material['material_category']}', must be one of: {valid_categories}")
                
                # Validate numeric fields
                numeric_fields = ['co2_per_kg', 'water_liters_per_kg', 'energy_mj_per_kg']
                for field in numeric_fields:
                    value = material.get(field)
                    if value and value != '':
                        try:
                            num_val = float(value)
                            if num_val < 0:
                                self.add_error("Materials", f"Row {i}: {field} cannot be negative")
                            elif field == 'co2_per_kg' and (num_val < 0.1 or num_val > 50):
                                self.add_warning("Materials", f"Row {i}: {field} value {num_val} seems unusual (typical range: 0.1-50)")
                        except (ValueError, TypeError):
                            self.add_error("Materials", f"Row {i}: {field} must be a number")
            
            # Check for duplicates
            names = [m['material_name'] for m in materials if m.get('material_name')]
            duplicates = [name for name, count in Counter(names).items() if count > 1]
            if duplicates:
                self.add_error("Materials", f"Duplicate material names: {duplicates}")
            
            print(f"✅ Validated {len(materials)} materials")
            return True
            
        except Exception as e:
            self.add_error("Materials", f"Error reading file: {e}")
            return False
    
    def validate_clothing_types(self) -> bool:
        """Validate clothing types data."""
        if not self.files['clothing_types'].exists():
            self.add_error("Clothing Types", "File not found: clothing_types.csv")
            return False
        
        try:
            with open(self.files['clothing_types'], 'r') as f:
                reader = csv.DictReader(f)
                clothing_types = list(reader)
            
            if not clothing_types:
                self.add_error("Clothing Types", "No clothing types found in CSV")
                return False
            
            # Check required fields
            required_fields = ['clothing_type', 'category', 'typical_weight_grams']
            for i, item in enumerate(clothing_types, 2):
                # Required fields
                for field in required_fields:
                    if not item.get(field):
                        self.add_error("Clothing Types", f"Row {i}: Missing required field '{field}'")
                
                # Validate clothing type name format
                if item.get('clothing_type'):
                    name = item['clothing_type']
                    if ' ' in name or name != name.lower():
                        self.add_warning("Clothing Types", f"Row {i}: Clothing type '{name}' should be lowercase with underscores")
                
                # Validate category
                valid_categories = ['tops', 'bottoms', 'dresses', 'outerwear', 'accessories']
                if item.get('category') and item['category'] not in valid_categories:
                    self.add_error("Clothing Types", f"Row {i}: Invalid category '{item['category']}', must be one of: {valid_categories}")
                
                # Validate weight fields
                weight_fields = ['typical_weight_grams', 'weight_range_min', 'weight_range_max']
                for field in weight_fields:
                    value = item.get(field)
                    if value and value != '':
                        try:
                            weight = int(value)
                            if weight <= 0:
                                self.add_error("Clothing Types", f"Row {i}: {field} must be positive")
                            elif field == 'typical_weight_grams' and (weight < 50 or weight > 3000):
                                self.add_warning("Clothing Types", f"Row {i}: {field} value {weight}g seems unusual (typical range: 50-3000g)")
                        except (ValueError, TypeError):
                            self.add_error("Clothing Types", f"Row {i}: {field} must be an integer")
                
                # Validate wash frequency
                if item.get('wash_frequency'):
                    try:
                        freq = float(item['wash_frequency'])
                        if not (0 < freq <= 1.0):
                            self.add_error("Clothing Types", f"Row {i}: wash_frequency must be between 0 and 1.0")
                    except (ValueError, TypeError):
                        self.add_error("Clothing Types", f"Row {i}: wash_frequency must be a number")
                
                # Validate weight range consistency
                if all(item.get(f) for f in ['typical_weight_grams', 'weight_range_min', 'weight_range_max']):
                    try:
                        typical = int(item['typical_weight_grams'])
                        min_weight = int(item['weight_range_min'])
                        max_weight = int(item['weight_range_max'])
                        
                        if min_weight >= max_weight:
                            self.add_error("Clothing Types", f"Row {i}: weight_range_min must be less than weight_range_max")
                        if not (min_weight <= typical <= max_weight):
                            self.add_warning("Clothing Types", f"Row {i}: typical_weight_grams should be within weight range")
                    except (ValueError, TypeError):
                        pass  # Already caught in weight validation above
            
            # Check for duplicates
            names = [ct['clothing_type'] for ct in clothing_types if ct.get('clothing_type')]
            duplicates = [name for name, count in Counter(names).items() if count > 1]
            if duplicates:
                self.add_error("Clothing Types", f"Duplicate clothing types: {duplicates}")
            
            print(f"✅ Validated {len(clothing_types)} clothing types")
            return True
            
        except Exception as e:
            self.add_error("Clothing Types", f"Error reading file: {e}")
            return False
    
    def validate_brands(self) -> bool:
        """Validate brands data."""
        if not self.files['brands'].exists():
            self.add_error("Brands", "File not found: brands_sustainability.csv")
            return False
        
        try:
            with open(self.files['brands'], 'r') as f:
                reader = csv.DictReader(f)
                brands = list(reader)
            
            if not brands:
                self.add_error("Brands", "No brands found in CSV")
                return False
            
            # Check required fields
            required_fields = ['brand_name']
            for i, brand in enumerate(brands, 2):
                # Required fields
                for field in required_fields:
                    if not brand.get(field):
                        self.add_error("Brands", f"Row {i}: Missing required field '{field}'")
                
                # Validate transparency score
                if brand.get('transparency_index_score'):
                    try:
                        score = int(brand['transparency_index_score'])
                        if not (0 <= score <= 100):
                            self.add_error("Brands", f"Row {i}: transparency_index_score must be between 0 and 100")
                    except (ValueError, TypeError):
                        self.add_error("Brands", f"Row {i}: transparency_index_score must be an integer")
                
                # Validate boolean fields
                boolean_fields = ['publishes_supplier_list', 'discloses_ghg_emissions', 'discloses_water_usage',
                                  'has_living_wage_commitment', 'has_climate_targets']
                for field in boolean_fields:
                    value = brand.get(field)
                    if value and value not in ['true', 'false', 'True', 'False']:
                        self.add_error("Brands", f"Row {i}: {field} must be true/false")
                
                # Validate tier1 suppliers count
                if brand.get('tier1_suppliers_disclosed'):
                    try:
                        count = int(brand['tier1_suppliers_disclosed'])
                        if count < 0:
                            self.add_error("Brands", f"Row {i}: tier1_suppliers_disclosed cannot be negative")
                        elif count > 1000:
                            self.add_warning("Brands", f"Row {i}: tier1_suppliers_disclosed value {count} seems unusually high")
                    except (ValueError, TypeError):
                        self.add_error("Brands", f"Row {i}: tier1_suppliers_disclosed must be an integer")
            
            # Check for duplicates
            names = [b['brand_name'] for b in brands if b.get('brand_name')]
            duplicates = [name for name, count in Counter(names).items() if count > 1]
            if duplicates:
                self.add_error("Brands", f"Duplicate brand names: {duplicates}")
            
            print(f"✅ Validated {len(brands)} brands")
            return True
            
        except Exception as e:
            self.add_error("Brands", f"Error reading file: {e}")
            return False
    
    def validate_parameters(self) -> bool:
        """Validate calculation parameters."""
        if not self.files['parameters'].exists():
            self.add_error("Parameters", "File not found: calculation_parameters.json")
            return False
        
        try:
            with open(self.files['parameters'], 'r') as f:
                parameters = json.load(f)
            
            if not parameters:
                self.add_error("Parameters", "No parameters found in JSON")
                return False
            
            # Check required fields
            required_fields = ['parameter_name', 'parameter_value']
            for i, param in enumerate(parameters, 1):
                # Required fields
                for field in required_fields:
                    if not param.get(field):
                        self.add_error("Parameters", f"Parameter {i}: Missing required field '{field}'")
                
                # Validate parameter value
                if param.get('parameter_value'):
                    try:
                        float(param['parameter_value'])
                    except (ValueError, TypeError):
                        self.add_error("Parameters", f"Parameter {i}: parameter_value must be a number")
                
                # Validate specific parameters
                param_name = param.get('parameter_name', '')
                param_value = param.get('parameter_value')
                
                if param_name == 'washing_machine_energy_kwh' and param_value:
                    try:
                        val = float(param_value)
                        if not (0.5 <= val <= 3.0):
                            self.add_warning("Parameters", f"washing_machine_energy_kwh value {val} outside typical range (0.5-3.0 kWh)")
                    except (ValueError, TypeError):
                        pass
                
                if param_name == 'average_clothing_lifespan_years' and param_value:
                    try:
                        val = float(param_value)
                        if not (1 <= val <= 10):
                            self.add_warning("Parameters", f"average_clothing_lifespan_years value {val} outside typical range (1-10 years)")
                    except (ValueError, TypeError):
                        pass
            
            # Check for duplicate parameter names
            names = [p['parameter_name'] for p in parameters if p.get('parameter_name')]
            duplicates = [name for name, count in Counter(names).items() if count > 1]
            if duplicates:
                self.add_error("Parameters", f"Duplicate parameter names: {duplicates}")
            
            print(f"✅ Validated {len(parameters)} parameters")
            return True
            
        except Exception as e:
            self.add_error("Parameters", f"Error reading file: {e}")
            return False
    
    def validate_cross_references(self) -> bool:
        """Validate cross-references between data files."""
        # This would check for consistency across files
        # For example, ensuring referenced materials exist, etc.
        
        # For now, just check data freshness
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=365)  # 1 year ago
        
        # Check material data freshness
        if self.files['materials'].exists():
            try:
                with open(self.files['materials'], 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('last_updated'):
                            try:
                                update_date = datetime.strptime(row['last_updated'], '%Y-%m-%d')
                                if update_date < cutoff_date:
                                    self.add_warning("Data Freshness", f"Material '{row['material_name']}' data is over 1 year old")
                            except ValueError:
                                self.add_warning("Data Freshness", f"Invalid date format for material '{row['material_name']}'")
            except Exception:
                pass
        
        return True
    
    def validate_all(self) -> bool:
        """Run all validations."""
        print("🔍 Starting comprehensive data validation...\n")
        
        # Validate individual files
        materials_ok = self.validate_materials()
        clothing_types_ok = self.validate_clothing_types()
        brands_ok = self.validate_brands()
        parameters_ok = self.validate_parameters()
        
        # Cross-reference validation
        cross_ref_ok = self.validate_cross_references()
        
        return all([materials_ok, clothing_types_ok, brands_ok, parameters_ok, cross_ref_ok])
    
    def print_summary(self):
        """Print validation summary."""
        print(f"\n{'='*60}")
        print("VALIDATION SUMMARY")
        print(f"{'='*60}")
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"   {error}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"   {warning}")
        
        if not self.errors and not self.warnings:
            print("\n🎉 All validations passed! Data is clean and consistent.")
        elif not self.errors:
            print(f"\n✅ No errors found. {len(self.warnings)} warnings to review.")
        else:
            print(f"\n💥 Found {len(self.errors)} errors and {len(self.warnings)} warnings.")
            print("Please fix errors before using the data.")
        
        print(f"{'='*60}")

def check_file_permissions(data_dir: Path) -> bool:
    """Check if data files are readable."""
    files_to_check = [
        "textile_exchange_materials.csv",
        "clothing_types.csv", 
        "brands_sustainability.csv",
        "calculation_parameters.json"
    ]
    
    all_readable = True
    for filename in files_to_check:
        filepath = data_dir / filename
        if filepath.exists():
            try:
                filepath.read_text()
                print(f"✅ {filename} is readable")
            except PermissionError:
                print(f"❌ {filename} permission denied")
                all_readable = False
            except Exception as e:
                print(f"❌ {filename} error: {e}")
                all_readable = False
        else:
            print(f"⚠️  {filename} not found")
    
    return all_readable

def main():
    parser = argparse.ArgumentParser(description='Validate reference data files')
    parser.add_argument('--data-dir', help='Directory containing data files', 
                        default=str(Path(__file__).parent.parent.parent / "data"))
    parser.add_argument('--check-permissions', action='store_true', 
                        help='Check file permissions only')
    parser.add_argument('--materials-only', action='store_true', 
                        help='Validate materials data only')
    parser.add_argument('--clothing-types-only', action='store_true', 
                        help='Validate clothing types only')
    parser.add_argument('--brands-only', action='store_true', 
                        help='Validate brands data only')
    parser.add_argument('--parameters-only', action='store_true', 
                        help='Validate parameters only')
    
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        return
    
    # Check permissions only
    if args.check_permissions:
        check_file_permissions(data_dir)
        return
    
    # Create validator
    validator = DataValidator(data_dir)
    
    # Run specific validations
    if args.materials_only:
        validator.validate_materials()
    elif args.clothing_types_only:
        validator.validate_clothing_types()
    elif args.brands_only:
        validator.validate_brands()
    elif args.parameters_only:
        validator.validate_parameters()
    else:
        # Run all validations
        validator.validate_all()
    
    # Print summary
    validator.print_summary()
    
    # Exit with error code if validation failed
    if validator.errors:
        sys.exit(1)

if __name__ == "__main__":
    main()