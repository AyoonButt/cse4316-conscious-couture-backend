# Import all models to ensure they are registered with SQLAlchemy
from .material import MaterialReference
from .clothing_type import ClothingTypeReference
from .calculation_params import CalculationParameter
from .user import User
from .brand import BrandSustainability
from .clothing import ClothingItem, MaterialCompositionContribution
from .swap import Swap
from .sale import Sale
from .impact import ClothingEnvironmentalImpact, SwapEnvironmentalImpact
from .statistics import UserImpactStatistics, PlatformImpactStatistics
from .data_quality import DataQualityTracking
from .review import Review
from .payment import Payment
from .order import Order
from .cart import CartItem

# Make all models available for import
__all__ = [
    # Phase 1: Reference Data Models
    'MaterialReference',
    'ClothingTypeReference',
    'CalculationParameter',

    # Phase 2: Core Entity Models
    'User',
    'BrandSustainability',

    # Phase 3: Main Business Models
    'ClothingItem',
    'MaterialCompositionContribution',
    'Swap',
    'Sale',
    'CartItem',

    # Phase 4: Impact & Analytics
    'ClothingEnvironmentalImpact',
    'SwapEnvironmentalImpact',
    'UserImpactStatistics',
    'PlatformImpactStatistics',
    'DataQualityTracking',

    # Phase 5: Social
    'Review',

    # Phase 6: Payments
    'Payment',
    'Order',
]