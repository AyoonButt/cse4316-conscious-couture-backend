# Clothing API Integration Guide

## Overview
This document explains how the frontend homepage has been integrated with the backend API to load clothing items dynamically instead of using hardcoded data.

## What Was Done

### Backend Changes
1. **Renamed API endpoints**: `/api/v1/garments/` → `/api/v1/clothing/`
2. **Created Pydantic schemas**: Added comprehensive request/response models for clothing items
3. **Implemented full CRUD API**: 
   - `GET /api/v1/clothing/` - List all clothing items with filtering and pagination
   - `GET /api/v1/clothing/{id}` - Get specific clothing item
   - `POST /api/v1/clothing/` - Create new clothing item
   - `PUT /api/v1/clothing/{id}` - Update clothing item
   - `DELETE /api/v1/clothing/{id}` - Delete clothing item
4. **Added utility endpoints**:
   - `GET /api/v1/clothing/categories/` - Get available clothing types
   - `GET /api/v1/clothing/brands/` - Get available brands
   - `GET /api/v1/clothing/sizes/` - Get available sizes
5. **Populated database**: Added 26 clothing items from the original frontend hardcoded data

### Frontend Changes
1. **Created API service**: `src/utils/api.js` - Centralized API calls
2. **Updated Homepage component**: 
   - Replaced hardcoded `itemData` with API calls
   - Added loading and error states
   - Connected search functionality to filter items
   - Maintained existing UI and filtering logic
3. **Enhanced search**: Now searches through item descriptions, brands, and clothing types

## Running the Application

### Backend
```bash
cd clothing-swap-backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
```bash
cd frontend
npm start
```

## API Endpoints

### Get All Clothing Items
```http
GET /api/v1/clothing/
```

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `per_page` (int): Items per page (default: 20, max: 100)
- `clothing_type` (string): Filter by clothing type
- `brand` (string): Filter by brand name
- `size` (string): Filter by size
- `condition` (string): Filter by condition
- `status` (string): Filter by status (default: "available")
- `search` (string): Search in description and brand

**Example Response:**
```json
{
  "items": [
    {
      "clothing_id": 1,
      "owner_user_id": 1,
      "clothing_type": "t-shirt",
      "brand": "Adidas",
      "description": "Adidas Benfica FC Portugal Soccer Jersey",
      "size": "M",
      "color": null,
      "condition": "good",
      "material_composition": {"cotton_conventional": 80.0, "polyester": 20.0},
      "primary_image_url": "https://media-photos.depop.com/...",
      "status": "available",
      "created_at": "2024-11-30T...",
      "updated_at": "2024-11-30T..."
    }
  ],
  "total": 26,
  "page": 1,
  "per_page": 20,
  "total_pages": 2
}
```

## Database Schema
The clothing items are stored with the following key fields:
- `clothing_id`: Primary key
- `owner_user_id`: Foreign key to users table
- `clothing_type`: Type (t-shirt, jeans, jacket, etc.)
- `brand`: Brand name
- `description`: Item description/title
- `size`: Item size
- `condition`: Item condition (good, excellent, etc.)
- `material_composition`: JSON object with material percentages
- `primary_image_url`: URL to main image
- `status`: availability status

## Frontend Integration
The frontend `Home.jsx` component now:
1. Fetches clothing items from the API on component mount
2. Transforms API data to match the existing UI format
3. Implements real-time search and filtering
4. Shows loading and error states
5. Maintains all existing category filtering functionality

## Data Migration
All 26 original hardcoded items have been migrated to the database with:
- Proper clothing type mapping
- Brand extraction from titles
- Material composition estimation
- Random user assignment
- Category classification (Men/Women/Vintage/Sports/etc.)

## CORS Configuration
The backend is configured to allow requests from the frontend at `http://localhost:3000` (or wherever the React app is running).

## Error Handling
- The frontend shows user-friendly error messages if the backend is unavailable
- API errors are logged to the console for debugging
- Fallback behavior maintains a functional UI even without backend connectivity