# Clothing Swap Environmental Impact API Backend

A FastAPI-based backend system for tracking environmental impact of clothing swaps and sustainable fashion choices. This API enables users to calculate, track, and analyze the carbon footprint reduction achieved through clothing exchanges and sustainable fashion practices.

## Tech Stack

- **FastAPI** - Modern, fast web framework for building APIs
- **SQLite** - Lightweight, file-based database for development
- **SQLAlchemy** - Python SQL toolkit and ORM
- **Pydantic** - Data validation using Python type annotations
- **Uvicorn** - ASGI web server implementation

## Features

- User authentication and management
- Garment and material tracking
- Brand environmental impact data
- Clothing swap transaction recording
- Environmental impact calculations
- User and platform statistics
- Integration with external sustainability data sources

## Quick Start

### Prerequisites

- Python 3.8+
- pip

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd clothing-swap-backend
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your specific configuration
```

5. Run the application:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### Development

For development with additional tools:
```bash
pip install -r requirements-dev.txt
```

## API Documentation

Once the server is running, you can access:

- **Interactive API docs (Swagger UI)**: http://localhost:8000/docs
- **Alternative API docs (ReDoc)**: http://localhost:8000/redoc
- **Health check**: http://localhost:8000/health

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Refresh access token

### Users
- `GET /api/v1/users/` - Get all users
- `GET /api/v1/users/{user_id}` - Get specific user
- `POST /api/v1/users/` - Create user
- `PUT /api/v1/users/{user_id}` - Update user
- `DELETE /api/v1/users/{user_id}` - Delete user

### Garments
- `GET /api/v1/garments/` - Get all garments
- `GET /api/v1/garments/{garment_id}` - Get specific garment
- `POST /api/v1/garments/` - Create garment
- `PUT /api/v1/garments/{garment_id}` - Update garment
- `DELETE /api/v1/garments/{garment_id}` - Delete garment

### Materials
- `GET /api/v1/materials/` - Get all materials
- `GET /api/v1/materials/{material_name}` - Get specific material data

### Brands
- `GET /api/v1/brands/` - Get all brands
- `GET /api/v1/brands/{brand_id}` - Get specific brand
- `POST /api/v1/brands/` - Create brand
- `PUT /api/v1/brands/{brand_id}` - Update brand
- `DELETE /api/v1/brands/{brand_id}` - Delete brand

### Swaps
- `GET /api/v1/swaps/` - Get all swaps
- `GET /api/v1/swaps/{swap_id}` - Get specific swap
- `POST /api/v1/swaps/` - Create swap
- `PUT /api/v1/swaps/{swap_id}` - Update swap
- `DELETE /api/v1/swaps/{swap_id}` - Delete swap

### Environmental Impact
- `POST /api/v1/impact/calculate` - Calculate environmental impact

### Statistics
- `GET /api/v1/stats/user/{user_id}` - Get user statistics
- `GET /api/v1/stats/platform` - Get platform-wide statistics

## Project Structure

```
clothing-swap-backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── auth.py
│   │       ├── users.py
│   │       ├── garments.py
│   │       ├── materials.py
│   │       ├── brands.py
│   │       ├── swaps.py
│   │       ├── impact.py
│   │       └── stats.py
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── repositories/
│   ├── utils/
│   ├── external/
│   ├── config.py
│   ├── database.py
│   └── main.py
├── alembic/
│   └── versions/
├── tests/
│   ├── test_api/
│   ├── test_services/
│   └── test_repositories/
├── scripts/
├── data/
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── .gitignore
└── README.md
```

## Development Status

This is Phase 1 initialization. All endpoints currently return placeholder responses and need implementation.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

[Add your license information here]