# Scripts Directory

This directory contains all scripts for managing the clothing swap backend's reference data and database operations.

## Directory Structure

```
scripts/
├── README.md                    # This file
├── loaders/                     # Database loading scripts
│   ├── load_materials.py
│   ├── load_clothing_types.py
│   ├── load_brands.py
│   ├── load_parameters.py
│   └── load_all_data.py
└── data_management/             # CSV/JSON editing scripts
    ├── add_clothing_type.py
    ├── update_brand_data.py
    ├── update_material_data.py
    ├── bulk_import.py
    └── validate_data.py
```

## Purpose

### Database Loaders (`loaders/`)
Scripts that read CSV/JSON files from the `data/` directory and load them into the SQLAlchemy database models. These handle the actual database operations.

### Data Management (`data_management/`)
Scripts that create, edit, validate, and manage the CSV/JSON reference data files. These work with the file system but don't directly touch the database.

## Typical Workflow

1. **Create/Edit Data**: Use `data_management/` scripts to add or modify reference data
2. **Validate Data**: Run `data_management/validate_data.py` to check data integrity
3. **Load to Database**: Use `loaders/` scripts to populate the database with validated data

## Quick Start

```bash
# Add new clothing type
python scripts/data_management/add_clothing_type.py "polo shirt"

# Update brand sustainability data
python scripts/data_management/update_brand_data.py "Patagonia" --manual

# Validate all reference data
python scripts/data_management/validate_data.py

# Load all data to database
python scripts/loaders/load_all_data.py

# Show database summary
python scripts/loaders/load_all_data.py --summary-only
```

## Dependencies

All scripts require:
- Python 3.8+
- SQLAlchemy 2.0+ (for loader scripts)
- Pandas (for Excel imports)
- Requests (for API data fetching)

The scripts automatically add the project root to the Python path to import app modules.