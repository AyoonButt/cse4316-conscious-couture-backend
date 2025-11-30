#!/usr/bin/env python3
"""
Load calculation parameters from JSON into the database.
Creates CalculationParameter records from calculation_parameters.json
"""

import sys
import json
import argparse
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.database import get_database_session
from app.models.calculation_params import CalculationParameter

def load_parameters_from_json(json_path: Path, session, update_existing: bool = False) -> dict:
    """Load parameters from JSON file into database."""
    
    if not json_path.exists():
        raise FileNotFoundError(f"Parameters JSON file not found: {json_path}")
    
    results = {
        'loaded': 0,
        'updated': 0,
        'skipped': 0,
        'errors': 0
    }
    
    print(f"📥 Loading parameters from: {json_path}")
    
    with open(json_path, 'r') as f:
        parameters = json.load(f)
    
    if not isinstance(parameters, list):
        raise ValueError("JSON file must contain an array of parameter objects")
    
    for param_num, param in enumerate(parameters, 1):
        try:
            parameter_name = param.get('parameter_name', '').strip()
            if not parameter_name:
                print(f"⏭️  Parameter {param_num}: Skipping empty parameter name")
                results['skipped'] += 1
                continue
            
            # Check if parameter already exists
            existing_param = session.query(CalculationParameter).filter(
                CalculationParameter.parameter_name == parameter_name
            ).first()
            
            if existing_param and not update_existing:
                print(f"⏭️  Parameter {param_num}: Parameter '{parameter_name}' already exists, skipping")
                results['skipped'] += 1
                continue
            
            # Parse parameter value
            parameter_value = None
            if param.get('parameter_value') is not None:
                try:
                    parameter_value = Decimal(str(param['parameter_value']))
                except (ValueError, TypeError):
                    print(f"❌ Parameter {param_num}: Invalid parameter_value for '{parameter_name}'")
                    results['errors'] += 1
                    continue
            else:
                print(f"❌ Parameter {param_num}: Missing parameter_value for '{parameter_name}'")
                results['errors'] += 1
                continue
            
            # Parse optional fields
            description = param.get('description', '')
            unit = param.get('unit', '')
            
            # Parse last updated date
            last_updated = None
            if param.get('last_updated'):
                try:
                    last_updated = datetime.strptime(param['last_updated'], '%Y-%m-%d').date()
                except ValueError:
                    try:
                        last_updated = datetime.strptime(param['last_updated'], '%Y-%m-%d %H:%M:%S').date()
                    except ValueError:
                        last_updated = datetime.now().date()
            else:
                last_updated = datetime.now().date()
            
            if existing_param:
                # Update existing parameter
                existing_param.parameter_value = parameter_value
                existing_param.description = description
                existing_param.unit = unit
                existing_param.last_updated = last_updated
                
                print(f"🔄 Parameter {param_num}: Updated parameter '{parameter_name}'")
                results['updated'] += 1
            else:
                # Create new parameter
                calc_param = CalculationParameter(
                    parameter_name=parameter_name,
                    parameter_value=parameter_value,
                    description=description,
                    unit=unit,
                    last_updated=last_updated
                )
                
                session.add(calc_param)
                print(f"✅ Parameter {param_num}: Loaded parameter '{parameter_name}'")
                results['loaded'] += 1
            
        except Exception as e:
            print(f"❌ Parameter {param_num}: Error loading parameter: {e}")
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

def clear_parameters_table(session):
    """Clear all parameters from the database."""
    try:
        count = session.query(CalculationParameter).count()
        session.query(CalculationParameter).delete()
        session.commit()
        print(f"🗑️  Cleared {count} existing parameters from database")
    except Exception as e:
        session.rollback()
        print(f"❌ Error clearing parameters table: {e}")
        raise

def show_parameters_summary(session):
    """Show summary of parameters in database."""
    parameters = session.query(CalculationParameter).order_by(
        CalculationParameter.parameter_name
    ).all()
    
    if not parameters:
        print("No parameters found in database.")
        return
    
    print(f"\n📊 Calculation Parameters Summary ({len(parameters)} total):")
    
    # Group parameters by category (based on name patterns)
    categories = {
        'Energy': [],
        'Water': [],
        'Transportation': [],
        'Lifecycle': [],
        'Processing': [],
        'Other': []
    }
    
    for param in parameters:
        name = param.parameter_name.lower()
        if 'energy' in name or 'kwh' in name or 'electricity' in name:
            categories['Energy'].append(param)
        elif 'water' in name or 'wash' in name:
            categories['Water'].append(param)
        elif 'transport' in name or 'shipping' in name or 'delivery' in name:
            categories['Transportation'].append(param)
        elif 'lifespan' in name or 'lifetime' in name or 'year' in name:
            categories['Lifecycle'].append(param)
        elif 'process' in name or 'production' in name or 'manufacturing' in name:
            categories['Processing'].append(param)
        else:
            categories['Other'].append(param)
    
    for category, params_list in categories.items():
        if params_list:
            print(f"\n{category} Parameters ({len(params_list)}):")
            for param in params_list:
                unit_text = f" {param.unit}" if param.unit else ""
                description_text = f" - {param.description}" if param.description else ""
                print(f"  • {param.parameter_name}: {param.parameter_value}{unit_text}{description_text}")

def add_default_parameters(session):
    """Add default calculation parameters if they don't exist."""
    
    default_params = [
        {
            'parameter_name': 'electricity_co2_per_kwh',
            'parameter_value': '0.233',
            'description': 'Global average CO2 emissions per kWh of electricity',
            'unit': 'kg CO2/kWh',
        },
        {
            'parameter_name': 'washing_machine_energy_kwh',
            'parameter_value': '0.9',
            'description': 'Average energy consumption per wash cycle',
            'unit': 'kWh/wash',
        },
        {
            'parameter_name': 'dryer_energy_kwh',
            'parameter_value': '2.5',
            'description': 'Average energy consumption per dryer cycle',
            'unit': 'kWh/cycle',
        },
        {
            'parameter_name': 'water_heating_energy_ratio',
            'parameter_value': '0.85',
            'description': 'Fraction of washing energy used for heating water',
            'unit': 'ratio',
        },
        {
            'parameter_name': 'average_clothing_lifespan_years',
            'parameter_value': '2.2',
            'description': 'Average lifespan of clothing items',
            'unit': 'years',
        },
        {
            'parameter_name': 'garment_use_phase_ratio',
            'parameter_value': '0.25',
            'description': 'Fraction of total environmental impact from use phase',
            'unit': 'ratio',
        },
        {
            'parameter_name': 'production_phase_ratio',
            'parameter_value': '0.60',
            'description': 'Fraction of total environmental impact from production',
            'unit': 'ratio',
        },
        {
            'parameter_name': 'transport_phase_ratio',
            'parameter_value': '0.05',
            'description': 'Fraction of total environmental impact from transport',
            'unit': 'ratio',
        },
        {
            'parameter_name': 'disposal_phase_ratio',
            'parameter_value': '0.10',
            'description': 'Fraction of total environmental impact from disposal',
            'unit': 'ratio',
        },
        {
            'parameter_name': 'swap_impact_reduction_factor',
            'parameter_value': '0.8',
            'description': 'Environmental impact reduction from clothing swaps',
            'unit': 'factor',
        },
        {
            'parameter_name': 'packaging_co2_per_shipment',
            'parameter_value': '0.05',
            'description': 'CO2 emissions from packaging per shipment',
            'unit': 'kg CO2/shipment',
        },
        {
            'parameter_name': 'local_delivery_co2_per_km',
            'parameter_value': '0.2',
            'description': 'CO2 emissions per kilometer for local delivery',
            'unit': 'kg CO2/km',
        }
    ]
    
    loaded_count = 0
    
    for param_data in default_params:
        existing = session.query(CalculationParameter).filter(
            CalculationParameter.parameter_name == param_data['parameter_name']
        ).first()
        
        if not existing:
            param = CalculationParameter(
                parameter_name=param_data['parameter_name'],
                parameter_value=Decimal(param_data['parameter_value']),
                description=param_data['description'],
                unit=param_data['unit'],
                last_updated=datetime.now().date()
            )
            session.add(param)
            loaded_count += 1
            print(f"✅ Added default parameter: {param_data['parameter_name']}")
    
    if loaded_count > 0:
        session.commit()
        print(f"\n💾 Added {loaded_count} default parameters")
    else:
        print("No new default parameters needed")

def main():
    parser = argparse.ArgumentParser(description='Load calculation parameters into database')
    parser.add_argument('--json-path', help='Path to parameters JSON file',
                        default=str(Path(__file__).parent.parent.parent / "data" / "calculation_parameters.json"))
    parser.add_argument('--update', action='store_true', 
                        help='Update existing parameters instead of skipping them')
    parser.add_argument('--clear', action='store_true', 
                        help='Clear existing parameters before loading')
    parser.add_argument('--summary', action='store_true', 
                        help='Show summary of parameters in database')
    parser.add_argument('--add-defaults', action='store_true',
                        help='Add default calculation parameters')
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
            show_parameters_summary(session)
            return
        
        # Add default parameters
        if args.add_defaults:
            if not args.dry_run:
                add_default_parameters(session)
                show_parameters_summary(session)
            else:
                print("🔍 DRY RUN: Would add default parameters")
            return
        
        # Clear existing data if requested
        if args.clear:
            if not args.dry_run:
                confirm = input("⚠️  This will delete all existing parameters. Continue? (y/N): ")
                if confirm.lower() != 'y':
                    print("Cancelled.")
                    return
                clear_parameters_table(session)
            else:
                print("🔍 DRY RUN: Would clear existing parameters table")
        
        # Load parameters
        json_path = Path(args.json_path)
        
        if args.dry_run:
            print(f"🔍 DRY RUN: Would load parameters from {json_path}")
            print(f"Update existing: {args.update}")
            return
        
        results = load_parameters_from_json(json_path, session, args.update)
        
        # Print summary
        print(f"\n📊 Loading Summary:")
        print(f"✅ Loaded: {results['loaded']}")
        print(f"🔄 Updated: {results['updated']}")
        print(f"⏭️  Skipped: {results['skipped']}")
        print(f"❌ Errors: {results['errors']}")
        
        if results['loaded'] > 0 or results['updated'] > 0:
            print(f"\n🎉 Successfully processed {results['loaded'] + results['updated']} parameters!")
            
            # Show final summary
            show_parameters_summary(session)
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main()