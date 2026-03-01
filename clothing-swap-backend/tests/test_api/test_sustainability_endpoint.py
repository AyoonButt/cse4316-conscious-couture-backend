#!/usr/bin/env python3
"""
Test script to verify the sustainability metrics endpoint.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from app.main import app
from fastapi.testclient import TestClient

def test_sustainability_endpoint():
    """Test the sustainability metrics endpoint."""
    
    client = TestClient(app)
    
    print('🧪 Testing Sustainability Metrics Endpoint...')
    print('')

    # Test 1: Get a clothing item to test with
    print('1. Getting available clothing items...')
    response = client.get('/api/v1/clothing/?per_page=1')
    if response.status_code == 200:
        data = response.json()
        if data['total'] > 0:
            clothing_id = data['items'][0]['clothing_id']
            item_name = data['items'][0]['description'][:40] if data['items'][0]['description'] else 'Unknown Item'
            print(f'   ✅ Found item {clothing_id}: {item_name}...')
            
            # Test 2: Get sustainability metrics
            print('')
            print(f'2. Getting sustainability metrics for item {clothing_id}...')
            sustainability_response = client.get(f'/api/v1/clothing/{clothing_id}/sustainability')
            
            if sustainability_response.status_code == 200:
                metrics = sustainability_response.json()
                print('   ✅ Sustainability metrics retrieved successfully')
                print(f'   📊 CO2 avoided: {metrics["avoided_impact"]["co2_kg"]:.2f} kg')
                print(f'   💧 Water saved: {metrics["avoided_impact"]["water_liters"]:.0f} liters') 
                print(f'   ⚡ Energy saved: {metrics["avoided_impact"]["energy_kwh"]:.1f} kWh')
                print(f'   📉 Impact reduction: {metrics["avoided_impact"]["percentage_reduction"]:.1f}%')
                print(f'   🚗 Equivalent km not driven: {metrics["equivalents"]["km_not_driven"]:.1f}')
                print(f'   🌳 Equivalent trees planted: {metrics["equivalents"]["trees_planted"]:.2f}')
                print(f'   📱 Smartphone charges: {metrics["equivalents"]["smartphone_charges"]}')
                
                # Check if brand context exists
                if metrics["brand_context"]["brand_name"]:
                    print(f'   🏷️  Brand: {metrics["brand_context"]["brand_name"]}')
                    if metrics["brand_context"]["transparency_score"]:
                        print(f'   📈 Transparency score: {metrics["brand_context"]["transparency_score"]}')
                
                print('')
                print('✅ Sustainability endpoint test passed!')
                
                # Show example response structure
                print('')
                print('📋 Sample Response Structure:')
                print(f'   • Item: {metrics["item_summary"]["name"]}')
                print(f'   • Type: {metrics["item_summary"]["type"]}')
                print(f'   • New garment CO2: {metrics["new_garment"]["co2_kg"]} kg')
                print(f'   • Reuse platform CO2: {metrics["reuse_impact"]["co2_kg"]} kg')
                print(f'   • Calculation version: {metrics["calculation_metadata"]["version"]}')
                
            else:
                print(f'   ❌ Failed to get sustainability metrics: {sustainability_response.status_code}')
                print(f'   Error: {sustainability_response.text}')
        else:
            print('   ⚠️  No clothing items found to test with')
    else:
        print(f'   ❌ Failed to get clothing items: {response.status_code}')
        print(f'   Error: {response.text}')

    # Test 3: Test with non-existent item
    print('')
    print('3. Testing with non-existent item...')
    error_response = client.get('/api/v1/clothing/99999/sustainability')
    if error_response.status_code == 404:
        print('   ✅ Correctly returns 404 for non-existent item')
    else:
        print(f'   ❌ Unexpected response for non-existent item: {error_response.status_code}')

    print('')
    print('🎉 Sustainability metrics endpoint testing complete!')
    print('')
    print('🌐 Endpoint available at: GET /api/v1/clothing/{clothing_id}/sustainability')
    
    return True

if __name__ == "__main__":
    test_sustainability_endpoint()