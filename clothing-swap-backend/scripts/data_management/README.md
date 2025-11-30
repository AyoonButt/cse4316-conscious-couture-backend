# Data Management Scripts

These scripts create, edit, validate, and manage the CSV/JSON reference data files. They work with the file system but don't directly interact with the database.

## Scripts

### Data Creation & Editing

- **`add_clothing_type.py`** - Add new clothing types interactively with guidelines
- **`update_brand_data.py`** - Update brand data from WikiRate API or manual entry
- **`update_material_data.py`** - Update material data from Textile Exchange or manual entry

### Data Import & Validation

- **`bulk_import.py`** - Import multiple records from CSV/Excel files with validation
- **`validate_data.py`** - Comprehensive data integrity and consistency checking

## Usage Examples

### Adding New Data

```bash
# Add a new clothing type interactively
python scripts/data_management/add_clothing_type.py "polo shirt"

# Add clothing type with specific parameters
python scripts/data_management/add_clothing_type.py "winter coat" \
  --category outerwear --weight 1200 --wears 100 --wash-freq 0.1

# Update brand data manually
python scripts/data_management/update_brand_data.py "Patagonia" --manual

# Fetch brand data from WikiRate API
python scripts/data_management/update_brand_data.py "H&M" --wikirate

# Add material data manually
python scripts/data_management/update_material_data.py "organic_hemp" --manual

# Import material data from Excel file
python scripts/data_management/update_material_data.py --excel textile_exchange_2024.xlsx
```

### Bulk Operations

```bash
# Import materials from CSV
python scripts/data_management/bulk_import.py materials new_materials.csv

# Import brands from Excel
python scripts/data_management/bulk_import.py brands sustainability_data.xlsx

# Bulk update brands from file
python scripts/data_management/update_brand_data.py --bulk brands_list.txt
```

### Data Validation

```bash
# Validate all reference data
python scripts/data_management/validate_data.py

# Validate specific data type
python scripts/data_management/validate_data.py --materials-only
python scripts/data_management/validate_data.py --brands-only

# Check file permissions
python scripts/data_management/validate_data.py --check-permissions
```

### Data Review

```bash
# List current materials
python scripts/data_management/update_material_data.py --list

# List current brands
python scripts/data_management/update_brand_data.py --list
```

## Features

### Interactive Input
- **Guided Entry**: Scripts provide guidelines and validation for manual data entry
- **Smart Defaults**: Automatic calculation of ranges and multipliers based on typical values
- **Category Validation**: Ensures data consistency with predefined categories
- **Preview Mode**: Shows data before confirmation

### Data Sources
- **WikiRate API**: Automatic fetching of brand transparency data
- **Textile Exchange**: Support for LCI library Excel imports
- **Manual Entry**: Interactive prompts with validation and guidance
- **Bulk Import**: CSV/Excel file processing with error reporting

### Validation & Quality
- **Field Validation**: Type checking, range validation, required field verification
- **Cross-Reference Checks**: Consistency across related data
- **Duplicate Detection**: Prevents duplicate entries with optional updates
- **Data Quality Scoring**: Tracks data source and reliability

## Data Files

The scripts create and manage these files in the `data/` directory:

- `textile_exchange_materials.csv` - Material environmental impact factors
- `clothing_types.csv` - Clothing type specifications and wear patterns
- `brands_sustainability.csv` - Brand transparency and sustainability metrics
- `calculation_parameters.json` - Environmental calculation constants

## Guidelines

### Material Data
- CO2 emissions: 1-15 kg CO2/kg material
- Water usage: 50-15000 L/kg material  
- Energy usage: 20-200 MJ/kg material
- Processing multipliers: 0.05-0.25 for different stages

### Clothing Types
- Weight range: 50-3000g typical for most garments
- Wash frequency: 0.05-1.0 (every 20 wears to every wear)
- Lifetime wears: 30-150 depending on durability and usage

### Brand Data
- Transparency scores: 0-100 based on disclosure practices
- Boolean flags for specific sustainability commitments
- Supplier disclosure counts for transparency metrics

## Error Handling

- **Input Validation**: Real-time validation with helpful error messages
- **File Safety**: Backup creation before destructive operations
- **Rate Limiting**: API request throttling to respect service limits
- **Rollback Support**: Undo capabilities for batch operations