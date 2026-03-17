#!/usr/bin/env python3
"""
Populate the database with clothing items from the frontend homepage.
"""

import sys
import random
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.database import get_database_session
from app.models.clothing import ClothingItem
from app.models.user import User
from app.models.brand import BrandSustainability


def map_frontend_to_clothing_type(main_category: str, sub_category: str) -> str:
    """Map frontend categories to database clothing types."""
    
    # Mapping based on existing clothing types in the database
    clothing_type_map = {
        # Men's clothing
        ("Men", "T-shirt"): "t-shirt",
        ("Men", "Jersey"): "t-shirt",  # Sports jerseys are essentially t-shirts
        ("Men", "Button-Down Shirt"): "shirt",
        ("Men", "Jackets"): "jacket",
        ("Men", "Sweaters"): "sweater", 
        ("Men", "Pants"): "pants",
        ("Men", "Shorts"): "shorts",
        
        # Women's clothing
        ("Women", "Tops"): "blouse",
        ("Women", "Dresses"): "dress",
        ("Women", "Jackets"): "jacket",
        ("Women", "Sweaters"): "sweater",
        ("Women", "Pants"): "pants",
        
        # Default mappings
        "t-shirt": "t-shirt",
        "jersey": "t-shirt",
        "shirt": "shirt", 
        "jeans": "jeans",
        "pants": "pants",
        "jacket": "jacket",
        "sweater": "sweater",
        "dress": "dress",
        "blouse": "blouse",
    }
    
    # Try exact mapping first
    key = (main_category, sub_category)
    if key in clothing_type_map:
        return clothing_type_map[key]
    
    # Try lowercase sub_category
    lower_sub = sub_category.lower()
    if lower_sub in clothing_type_map:
        return clothing_type_map[lower_sub]
    
    # Default fallbacks
    if "shirt" in lower_sub:
        return "shirt"
    elif "pant" in lower_sub or "jean" in lower_sub:
        return "pants"
    elif "jacket" in lower_sub:
        return "jacket"
    elif "sweater" in lower_sub:
        return "sweater"
    elif "dress" in lower_sub:
        return "dress"
    else:
        return "t-shirt"  # Default


def estimate_material_composition(clothing_type: str, brand: str) -> dict:
    """Estimate material composition based on clothing type and brand."""
    
    # Basic material composition estimates
    if clothing_type in ["t-shirt", "shirt"]:
        if "organic" in brand.lower() or brand in ["Patagonia"]:
            return {"cotton_organic": 100.0}
        else:
            return {"cotton_conventional": 80.0, "polyester": 20.0}
    elif clothing_type == "jeans":
        return {"cotton_conventional": 98.0, "elastane": 2.0}
    elif clothing_type == "sweater":
        if "wool" in brand.lower():
            return {"wool": 100.0}
        else:
            return {"cotton_conventional": 60.0, "polyester": 40.0}
    elif clothing_type == "jacket":
        return {"polyester": 60.0, "nylon": 30.0, "elastane": 10.0}
    elif clothing_type == "dress":
        return {"polyester": 70.0, "elastane": 30.0}
    else:
        # Default composition
        return {"cotton_conventional": 70.0, "polyester": 30.0}


def get_brand_id(session, brand_name: str):
    """Get brand ID from the database."""
    if not brand_name:
        return None
        
    brand = session.query(BrandSustainability).filter(
        BrandSustainability.brand_name.ilike(f"%{brand_name}%")
    ).first()
    
    return brand.brand_id if brand else None


def create_clothing_items(session):
    """Create clothing items from frontend data."""
    
    # Frontend homepage item data (extracted from Home.jsx)
    homepage_items = [
        {
            'img': 'https://media-photos.depop.com/b1/51176473/3015572650_3f3027d52bfc4a25b335c41d069e7671/P0.jpg',
            'title': 'Adidas Benfica FC Portugal Soccer Jersey',
            'types': 'Sports',
            'main': 'Men',
            'sub': 'Jersey',
            'size': 'M',
        },
        {
            'img': 'https://media-photos.depop.com/r1/15915712/2533782253_f4655070d5574d83b7b3e743dde526ca/P0.jpg',
            'title': 'Vintage 90s Spiderman T-shirt',
            'types': 'Vintage',
            'main': 'Men',
            'sub': 'T-shirt',
            'size': 'L',
        },
        {
            'img': 'https://media-photos.depop.com/b1/34380814/2931957337_765f9f392841475594b6f1891ea1ed33/P0.jpg',
            'title': 'Vintage Levis 501',
            'types': 'Vintage',
            'main': 'Men',
            'sub': 'Pants',
            'size': '32x30'
        },
        {
            'img': 'https://media-photos.depop.com/b1/272352312/2970756992_3f368f0e27c347f891688d2596078e9e/P0.jpg',
            'title': 'Grey Blank Vintage Zip Up Hoodie',
            'types': 'Streetwear',
            'main': 'Men',
            'sub': 'Jackets',
            'size': 'S'
        },
        {
            'img': 'https://media-photos.depop.com/b1/36269286/3114006648_6480fb49c93d452a9c5171b8c672f44c/P0.jpg',
            'title': 'Harley Davidson Mens Black and Grey T-shirt',
            'types': 'Vintage',
            'main': 'Men',
            'sub': 'T-shirt',
            'size': 'M',
        },
        {
            'img': 'https://media-photos.depop.com/b1/423762091/3130887827_66573b148b0746ddb197d451727d0801/P0.jpg',
            'title': 'Mitchell & Ness Rodman Bulls Jersey',
            'types': 'Sports',
            'main': 'Men',
            'sub': 'Jersey',
            'size': 'XL',
        },
        {
            'img': 'https://media-photos.depop.com/b1/43892191/3127803328_a003132d86174b76923a4c9a9329ac17/P0.jpg',
            'title': 'Vintage 90s Dallas Stars CCM Hockey Jersey',
            'types': 'Sports',
            'main': 'Men',
            'sub': 'Jersey',
            'size': 'XL'
        },
        {
            'img': 'https://media-photos.depop.com/b1/44114323/3128787642_7c15c96a53a14e3e87099a912bf87aa2/P0.jpg',
            'title': 'Vintage 60s/70s big mac flannel shirt',
            'types': 'Vintage',
            'main': 'Men',
            'sub': 'Button-Down Shirt',
            'size': 'XL'
        },
        {
            'img': 'https://media-photos.depop.com/r1/43928653/3127220415_285d75ec85d243a9a0d11219c9cc40a0/P0.jpg',
            'title': 'Vintage 1990s Woolrich Button Up Flannel',
            'types': 'Vintage',
            'main': 'Men',
            'sub': 'Button-Down Shirt',
            'size': 'M'
        },
        {
            'img': 'https://media-photos.depop.com/b1/11676083/3116942922_3da89921db2b4fca978910fa44f32860/P0.jpg',
            'title': 'Vintage 60s 70s Green and brown wool flannel',
            'types': 'Vintage',
            'main': 'Men',
            'sub': 'Button-Down Shirt',
            'size': 'M'
        },
        {
            'img': 'https://media-photos.depop.com/b1/10311300/3104128631_401176b7969f4de99b0d4d1f10e295a6/P0.jpg',
            'title': 'Coogi style 3D knit multicolor sweater',
            'types': 'Vintage',
            'main': 'Men',
            'sub': 'Sweaters',
            'size': 'M'
        },
        {
            'img': 'https://media-photos.depop.com/b1/234012652/3125354580_8f1a3db82c214822a0ccbd9cd075a4e8/P0.jpg',
            'title': 'Ralph Lauren Cable-Knit Jumper',
            'types': 'Vintage',
            'main': 'Men',
            'sub': 'Sweaters',
            'size': 'L'
        },
        {
            'img': 'https://media-photos.depop.com/r1/39295972/2950953733_ae92354fee67415b84365542835b84d8/P0.jpg',
            'title': 'Ralph Lauren Womens Cream and White Jumper',
            'main': 'Women',
            'sub': 'Tops',
            'size': 'S'
        },
        {
            'img': 'https://media-photos.depop.com/b1/9561899/1716427062_72819b586fd543b3a298f1bb33cf84e6/P0.jpg',
            'title': 'Womens Tan and Black Jumper',
            'main': 'Women',
            'sub': 'Tops',
            'size': 'M',
        },
        {
            'img': 'https://media-photos.depop.com/b1/21606785/2684574059_84f1c83d78cd40218097b2c1439c8b71/P0.jpg',
            'title': 'Hollister Co. Womens Navy and Blue Vest',
            'main': 'Women',
            'sub': 'Tops',
            'size': 'S'
        },
        {
            'img': 'https://media-photos.depop.com/b0/31863100/1079679697_b178dd42a0684441a82b9b5e6e1ea2b6/P0.jpg',
            'title': 'Nike Womens Black Crop-top',
            'main': 'Women',
            'sub': 'Tops',
            'size': 'M'
        },
        {
            'img': 'https://media-photos.depop.com/b1/405182541/2865253782_b32b2c0881b54f76a71d5e75e8127dcb/P0.jpg',
            'title': 'Madewell Womens multi Dress',
            'main': 'Women',
            'sub': 'Dresses',
            'size': 'M'
        },
        {
            'img': 'https://media-photos.depop.com/b1/51303409/2665882890_799cfe694d3c43d89cfeb034407f457d/P0.jpg',
            'title': 'Lucy in the Sky Womens Blue and Green Dress',
            'main': 'Women',
            'sub': 'Dresses',
            'size': 'S'
        },
        {
            'img': 'https://media-photos.depop.com/b1/24692972/repop_48457068_1847737862/2057370696_4c8bcd6b61b14d20bf148b4de450b9f2/P0.jpg',
            'title': 'Victorias Secret Womens Yellow Dress',
            'main': 'Women',
            'sub': 'Dresses',
            'size': 'M'
        },
        {
            'img': 'https://media-photos.depop.com/b1/44062071/2510365185_bccfbcaa7f3e4c3e88483881499f73fe/P0.jpg',
            'title': 'Lululemon Womens Khaki and Green Jacket',
            'main': 'Women',
            'sub': 'Jackets',
            'size': 'S'
        },
        {
            'img': 'https://media-photos.depop.com/b1/6390551/1788358963_e487c64e910b4f54a52a0bd3b9d132bb/P0.jpg',
            'title': 'Lululemon Womens Black Jacket',
            'main': 'Women',
            'sub': 'Jackets',
            'size': 'M'
        },
        {
            'img': 'https://media-photos.depop.com/b1/50002075/2682427768_9045818b7f3442cb8425fbbf7428db3a/P0.jpg',
            'title': 'Brandy Melville Womens Blue and Green Jacket',
            'main': 'Women',
            'sub': 'Jackets',
            'size': 'S'
        },
        {
            'img': 'https://media-photos.depop.com/b1/36363509/2841739168_800ca49bf259442c9b964ed0694ba895/P0.jpg',
            'title': 'Vintage Ralph Lauren Downhill Ski Hand Knit Womens Sweater',
            'types': 'Vintage',
            'main': 'Women',
            'sub': 'Sweaters',
            'size': 'L'
        },
        {
            'img': 'https://media-photos.depop.com/b1/1832344/2354745199_a6513c6d88e2416b90ec778e7f59f6fc/P0.jpg',
            'title': 'vintage 70s peruvian wool chunky knit womens sweater',
            'types': 'Vintage',
            'main': 'Women',
            'sub': 'Sweaters',
            'size': 'M'
        },
        {
            'img': 'https://media-photos.depop.com/b0/1102614/1133346596_6037d9f14077486190e1809e151c0739/P0.jpg',
            'title': 'Ronny Kobo Womens Blue Cardigan',
            'main': 'Women',
            'sub': 'Sweaters',
            'size': 'S'
        },
        {
            'img': 'https://media-photos.depop.com/b1/23465969/2648121440_a88fcd5ad0cc48df9b8fbdd2202bdff9/P0.jpg',
            'title': 'Paloma Wool Womens multi Jumper Sweater',
            'main': 'Women',
            'sub': 'Sweaters',
            'size': 'L'
        }
    ]
    
    # Get all users for random assignment
    users = session.query(User).all()
    if not users:
        print("❌ No users found in database. Please run create_sample_users.py first.")
        return []
    
    created_items = []
    
    for idx, item_data in enumerate(homepage_items):
        # Extract brand from title
        brand = None
        title = item_data['title']
        
        # Common brand extraction patterns
        brands_to_check = ["Adidas", "Nike", "Ralph Lauren", "Levi", "Hollister", "Lululemon", 
                          "Brandy Melville", "Harley Davidson", "Mitchell & Ness", "Patagonia"]
        
        for brand_name in brands_to_check:
            if brand_name.lower() in title.lower():
                brand = brand_name
                break
        
        # If no brand found, try to extract from title
        if not brand and "Womens" not in title and "Mens" not in title:
            words = title.split()
            if len(words) > 1:
                brand = words[0]  # First word often is brand
        
        # Map to clothing type
        clothing_type = map_frontend_to_clothing_type(
            item_data.get('main', ''), 
            item_data.get('sub', '')
        )
        
        # Get material composition
        material_composition = estimate_material_composition(clothing_type, brand or "")
        
        # Random owner assignment
        owner = random.choice(users)
        
        # Extract color from title (basic extraction)
        color = None
        color_words = ["black", "white", "blue", "red", "green", "yellow", "brown", "grey", "gray", "navy", "tan", "khaki"]
        for color_word in color_words:
            if color_word.lower() in title.lower():
                color = color_word.lower()
                break
        
        # Create clothing item
        clothing_item = ClothingItem(
            owner_user_id=owner.user_id,
            clothing_type=clothing_type,
            brand=brand,
            brand_id=get_brand_id(session, brand),
            description=title,
            size=item_data['size'],
            color=color,
            condition="good",  # Default condition
            material_composition=material_composition,
            weight_grams=None,  # Will be estimated automatically
            primary_image_url=item_data['img'],
            additional_images=[],
            status="available"
        )
        
        session.add(clothing_item)
        created_items.append(clothing_item)
        
        print(f"✅ Added: {title[:50]}{'...' if len(title) > 50 else ''}")
    
    session.commit()
    
    # Refresh to get IDs
    for item in created_items:
        session.refresh(item)
    
    return created_items


def main():
    """Main function."""
    
    print("🚀 Populating database with homepage clothing items...")
    
    try:
        session = get_database_session()
        
        # Check if items already exist
        existing_count = session.query(ClothingItem).count()
        if existing_count > 0:
            print(f"⚠️  Found {existing_count} existing clothing items.")
            response = input("Do you want to add more items anyway? (y/N): ")
            if response.lower() != 'y':
                print("Cancelled.")
                return True
        
        items = create_clothing_items(session)
        
        print(f"\n📊 Summary:")
        print(f"Created {len(items)} clothing items")
        print(f"Total items in database: {session.query(ClothingItem).count()}")
        
        print(f"\n✅ Homepage items population complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'session' in locals():
            session.close()
    
    return True


if __name__ == "__main__":
    main()