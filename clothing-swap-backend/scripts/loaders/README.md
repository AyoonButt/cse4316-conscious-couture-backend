# Database Loaders

These scripts load reference data from CSV/JSON files into the SQLAlchemy database models.

## Scripts

### Individual Loaders

- **`load_materials.py`** - Load material reference data (textile impact factors)
- **`load_clothing_types.py`** - Load clothing type reference data (weights, wear patterns)
- **`load_brands.py`** - Load brand sustainability data (transparency scores, certifications)
- **`load_parameters.py`** - Load calculation parameters (environmental factors, constants)

### Master Loader

- **`load_all_data.py`** - Load all reference data in the correct order with comprehensive reporting

## Common Options

All loader scripts support these flags:

- `--update` - Update existing records instead of skipping them
- `--clear` - Clear existing data before loading (destructive!)
- `--summary` - Show current database contents without loading
- `--dry-run` - Preview what would be loaded without making changes

## Usage Examples

```bash
# Load all reference data (recommended)
python scripts/loaders/load_all_data.py

# Load specific data type
python scripts/loaders/load_materials.py

# Update existing brand data
python scripts/loaders/load_brands.py --update

# Clear and reload all data
python scripts/loaders/load_all_data.py --clear

# Preview loading operation
python scripts/loaders/load_all_data.py --dry-run

# Show current database state
python scripts/loaders/load_all_data.py --summary-only

# Add default calculation parameters
python scripts/loaders/load_parameters.py --add-defaults
```

## Data Sources

The loaders expect these files in the `data/` directory:

- `textile_exchange_materials.csv` - Material environmental impact data
- `clothing_types.csv` - Clothing type reference data  
- `brands_sustainability.csv` - Brand transparency and sustainability data
- `calculation_parameters.json` - Environmental calculation parameters

## Database Models

The scripts populate these SQLAlchemy models:

- **MaterialReference** - Material environmental impact factors
- **ClothingTypeReference** - Clothing type specifications
- **BrandSustainability** - Brand sustainability metrics
- **CalculationParameter** - Environmental calculation constants

## Error Handling

- **Transaction Safety**: All operations use database transactions and rollback on errors
- **Validation**: Data is validated during loading with detailed error reports
- **Duplicate Handling**: Configurable behavior for existing records (skip/update)
- **Confirmation**: Destructive operations require user confirmation

## Dependencies

- SQLAlchemy 2.0+ with database session management
- Pandas for CSV/Excel file reading
- Decimal for precise numerical calculations
- pathlib for cross-platform file handling