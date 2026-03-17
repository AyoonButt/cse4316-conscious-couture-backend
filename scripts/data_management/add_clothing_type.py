#!/usr/bin/env python3
"""
Script to add new clothing types to the reference data.
Can be used interactively or with command line arguments.
"""

import sys
import csv
import argparse
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

def get_clothing_type_data(
    clothing_type: str,
    category: str = None,
    typical_weight_grams: int = None,
    weight_range_min: int = None,
    weight_range_max: int = None,
    typical_wears: int = None,
    wash_frequency: float = None
) -> Dict[str, Any]:
    """Get clothing type data either from parameters or interactive input."""
    
    data = {}
    
    # Clothing type (required)
    data['clothing_type'] = clothing_type.lower().replace(' ', '_')
    
    # Category with suggestions
    if not category:
        print("\nAvailable categories: tops, bottoms, dresses, outerwear, accessories")
        category = input(f"Category for '{clothing_type}': ").strip()
    data['category'] = category
    
    # Weight data
    if typical_weight_grams is None:
        print(f"\nWeight guidelines:")
        print("- Light items (t-shirt, tank top): 120-200g")
        print("- Medium items (shirt, pants): 200-600g")
        print("- Heavy items (jeans, sweater): 400-700g")
        print("- Outerwear (jacket, coat): 600-1500g")
        typical_weight_grams = int(input(f"Typical weight for '{clothing_type}' (grams): "))
    data['typical_weight_grams'] = typical_weight_grams
    
    # Weight range (auto-calculate if not provided)
    if weight_range_min is None:
        weight_range_min = int(typical_weight_grams * 0.7)  # 30% below typical
    if weight_range_max is None:
        weight_range_max = int(typical_weight_grams * 1.4)  # 40% above typical
    
    data['weight_range_min'] = weight_range_min
    data['weight_range_max'] = weight_range_max
    
    # Typical wears
    if typical_wears is None:
        print(f"\nLifetime wear guidelines:")
        print("- Everyday items (t-shirt): 40-60 wears")
        print("- Occasional items (dress, blouse): 30-50 wears")
        print("- Durable items (jeans): 60-100 wears")
        print("- Outerwear (coat, jacket): 80-150 wears")
        typical_wears = int(input(f"Expected lifetime wears for '{clothing_type}': "))
    data['typical_wears'] = typical_wears
    
    # Wash frequency
    if wash_frequency is None:
        print(f"\nWash frequency guidelines:")
        print("- 1.0 = washed after every wear (underwear, t-shirts)")
        print("- 0.5 = washed every 2 wears (shirts, blouses)")
        print("- 0.33 = washed every 3 wears (pants)")
        print("- 0.2 = washed every 5 wears (jeans)")
        print("- 0.1 = washed every 10 wears (jackets)")
        print("- 0.05 = washed every 20 wears (coats)")
        wash_frequency = float(input(f"Wash frequency for '{clothing_type}' (0.05-1.0): "))
    data['wash_frequency'] = wash_frequency
    
    return data

def clothing_type_exists(clothing_type: str, csv_path: Path) -> bool:
    """Check if clothing type already exists in CSV."""
    if not csv_path.exists():
        return False
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['clothing_type'].lower() == clothing_type.lower():
                return True
    return False

def add_clothing_type_to_csv(data: Dict[str, Any], csv_path: Path, update_if_exists: bool = False):
    """Add clothing type to CSV file."""
    
    # Check if already exists
    if clothing_type_exists(data['clothing_type'], csv_path):
        if not update_if_exists:
            print(f"❌ Clothing type '{data['clothing_type']}' already exists!")
            print("Use --update flag to overwrite existing entries.")
            return False
        else:
            print(f"🔄 Updating existing clothing type '{data['clothing_type']}'")
    
    # Read existing data
    existing_data = []
    headers = ['clothing_type', 'category', 'typical_weight_grams', 'weight_range_min', 
               'weight_range_max', 'typical_wears', 'wash_frequency']
    
    if csv_path.exists():
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or headers
            for row in reader:
                if update_if_exists and row['clothing_type'].lower() == data['clothing_type'].lower():
                    continue  # Skip existing entry (will be replaced)
                existing_data.append(row)
    
    # Add new data
    existing_data.append(data)
    
    # Write back to CSV
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(existing_data)
    
    action = "Updated" if update_if_exists else "Added"
    print(f"✅ {action} clothing type '{data['clothing_type']}' to {csv_path}")
    return True

def show_preview(data: Dict[str, Any]):
    """Show preview of the data to be added."""
    print(f"\n{'='*50}")
    print("CLOTHING TYPE PREVIEW")
    print(f"{'='*50}")
    print(f"Type: {data['clothing_type']}")
    print(f"Category: {data['category']}")
    print(f"Typical Weight: {data['typical_weight_grams']}g")
    print(f"Weight Range: {data['weight_range_min']}-{data['weight_range_max']}g")
    print(f"Expected Wears: {data['typical_wears']}")
    print(f"Wash Frequency: {data['wash_frequency']} (every {1/data['wash_frequency']:.1f} wears)")
    print(f"{'='*50}")

def main():
    parser = argparse.ArgumentParser(description='Add new clothing type to reference data')
    parser.add_argument('clothing_type', help='Name of the clothing type (e.g., "polo shirt")')
    parser.add_argument('--category', help='Category: tops, bottoms, dresses, outerwear, accessories')
    parser.add_argument('--weight', type=int, help='Typical weight in grams')
    parser.add_argument('--min-weight', type=int, help='Minimum weight in grams')
    parser.add_argument('--max-weight', type=int, help='Maximum weight in grams')
    parser.add_argument('--wears', type=int, help='Expected lifetime wears')
    parser.add_argument('--wash-freq', type=float, help='Wash frequency (0.05-1.0)')
    parser.add_argument('--update', action='store_true', help='Update if clothing type already exists')
    parser.add_argument('--yes', action='store_true', help='Skip confirmation prompt')
    
    args = parser.parse_args()
    
    # Paths
    csv_path = Path(__file__).parent.parent.parent / "data" / "clothing_types.csv"
    
    print(f"Adding clothing type: {args.clothing_type}")
    
    # Get clothing type data
    data = get_clothing_type_data(
        clothing_type=args.clothing_type,
        category=args.category,
        typical_weight_grams=args.weight,
        weight_range_min=args.min_weight,
        weight_range_max=args.max_weight,
        typical_wears=args.wears,
        wash_frequency=args.wash_freq
    )
    
    # Show preview
    show_preview(data)
    
    # Confirm
    if not args.yes:
        confirm = input("\nAdd this clothing type? (y/N): ").lower().strip()
        if confirm != 'y':
            print("Cancelled.")
            return
    
    # Add to CSV
    success = add_clothing_type_to_csv(data, csv_path, args.update)
    
    if success:
        print(f"\n🎉 Successfully added '{data['clothing_type']}'!")
        print("\nNext steps:")
        print("1. Review the data in: data/clothing_types.csv")
        print("2. Run database loader: python scripts/load_clothing_types.py")
    
if __name__ == "__main__":
    main()