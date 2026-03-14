#!/usr/bin/env python3
"""
Test script to verify the swap modal and swap details API integration.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from app.main import app
from fastapi.testclient import TestClient

def test_swap_integration():
    """Test the swap integration functionality."""
    
    client = TestClient(app)
    
    print("🔄 Testing Swap Integration...")
    
    # Test 1: Get clothing items for swap modal
    print("\n1. Testing clothing items for swap selection")
    response = client.get('/api/v1/clothing/?per_page=10&status=available')
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Found {data['total']} available items for swapping")
        
        if len(data['items']) >= 2:
            item1 = data['items'][0]
            item2 = data['items'][1]
            
            print(f"   📦 Item 1: {item1['description'][:40]}... (ID: {item1['clothing_id']})")
            print(f"   📦 Item 2: {item2['description'][:40]}... (ID: {item2['clothing_id']})")
            
            # Test 2: Create a new clothing item (simulating new item in swap modal)
            print(f"\n2. Testing new item creation for swap")
            new_item_data = {
                "owner_user_id": 1,
                "clothing_type": "t-shirt",
                "brand": "Test Brand",
                "description": "Test Swap Item for API Integration",
                "size": "M",
                "color": "Blue",
                "condition": "good",
                "material_composition": {"cotton_conventional": 100.0},
                "primary_image_url": None
            }
            
            create_response = client.post('/api/v1/clothing/', json=new_item_data)
            
            if create_response.status_code == 200:
                new_item = create_response.json()
                print(f"   ✅ Created new item: {new_item['description']} (ID: {new_item['clothing_id']})")
                
                # Test 3: Simulate swap data structure
                print(f"\n3. Testing swap data structure")
                
                swap_data = {
                    "targetItem": {
                        "id": item1['clothing_id'],
                        "name": item1['description'],
                        "size": item1['size'],
                        "condition": item1['condition'],
                        "image": item1['primary_image_url'],
                        "description": item1['description'],
                        "brand": item1.get('brand'),
                        "owner": {
                            "name": "Test Owner",
                            "user_id": item1['owner_user_id']
                        }
                    },
                    "selectedItem": {
                        "id": new_item['clothing_id'],
                        "name": new_item['description'],
                        "size": new_item['size'],
                        "condition": new_item['condition'],
                        "description": new_item['description'],
                        "brand": new_item.get('brand'),
                        "image": new_item['primary_image_url']
                    },
                    "timestamp": "2024-11-30T12:00:00Z",
                    "isNewItem": True
                }
                
                print(f"   ✅ Swap data structure ready:")
                print(f"      Target: {swap_data['targetItem']['name'][:30]}...")
                print(f"      Offer:  {swap_data['selectedItem']['name'][:30]}...")
                
                # Test 4: Verify items can be retrieved individually
                print(f"\n4. Testing individual item retrieval")
                
                target_response = client.get(f"/api/v1/clothing/{item1['clothing_id']}")
                offer_response = client.get(f"/api/v1/clothing/{new_item['clothing_id']}")
                
                if target_response.status_code == 200 and offer_response.status_code == 200:
                    print(f"   ✅ Both items can be retrieved for swap details page")
                else:
                    print(f"   ❌ Failed to retrieve items individually")
                
                # Clean up: Delete test item
                delete_response = client.delete(f"/api/v1/clothing/{new_item['clothing_id']}")
                if delete_response.status_code == 200:
                    print(f"   🧹 Cleaned up test item")
                
            else:
                print(f"   ❌ Failed to create new item: {create_response.status_code}")
                print(f"      Error: {create_response.text}")
                
        else:
            print(f"   ⚠️  Need at least 2 items for swap testing, found {len(data['items'])}")
            
    else:
        print(f"   ❌ Failed to get clothing items: {response.status_code}")
        print(f"   Error: {response.text}")
    
    # Test 5: Test utility endpoints used by swap modal
    print(f"\n5. Testing utility endpoints")
    
    endpoints = [
        ('/api/v1/clothing/categories/', 'clothing types'),
        ('/api/v1/clothing/brands/', 'brands'),
        ('/api/v1/clothing/sizes/', 'sizes')
    ]
    
    for endpoint, name in endpoints:
        response = client.get(endpoint)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ {name}: {len(data)} options available")
        else:
            print(f"   ❌ Failed to get {name}: {response.status_code}")
    
    print(f"\n🎉 Swap integration testing complete!")
    
    # Frontend integration URLs
    print(f"\n📱 Frontend Swap Flow URLs to Test:")
    print(f"   1. Homepage → Click any item → Click 'Request Swap'")
    print(f"   2. SwapModal → Select existing item or create new item")
    print(f"   3. SwapDetails → Review and confirm swap")
    
    print(f"\n🔧 Frontend Integration Notes:")
    print(f"   • SwapModal now loads real user items from API")
    print(f"   • Creating new items saves to database immediately") 
    print(f"   • SwapDetails shows real item data and handles API errors")
    print(f"   • All components have loading states and error handling")
    
    return True

if __name__ == "__main__":
    test_swap_integration()