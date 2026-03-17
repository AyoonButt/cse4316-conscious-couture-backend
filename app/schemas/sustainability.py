from typing import Optional
from pydantic import BaseModel, Field


class SustainabilityEquivalents(BaseModel):
    km_not_driven: float = Field(..., description="Equivalent kilometers not driven")
    trees_planted: float = Field(..., description="Equivalent trees planted")
    days_drinking_water: float = Field(..., description="Days of drinking water saved")
    smartphone_charges: int = Field(..., description="Smartphone charges equivalent")


class NewItemImpact(BaseModel):
    co2_kg: float = Field(..., description="CO2 emissions in kg for new item production")
    water_liters: float = Field(..., description="Water consumption in liters")
    energy_kwh: float = Field(..., description="Energy consumption in kWh")
    breakdown: dict = Field(..., description="Detailed breakdown of impact sources")


class ReuseImpact(BaseModel):
    co2_kg: float = Field(..., description="CO2 emissions from reuse platform")
    breakdown: dict = Field(..., description="Breakdown of reuse platform impacts")


class AvoidedImpact(BaseModel):
    co2_kg: float = Field(..., description="Net CO2 avoided")
    water_liters: float = Field(..., description="Net water saved")
    energy_kwh: float = Field(..., description="Net energy saved")
    percentage_reduction: float = Field(..., description="Percentage reduction vs new item")


class BrandContext(BaseModel):
    brand_name: Optional[str] = Field(None, description="Brand name")
    transparency_score: Optional[int] = Field(None, description="Transparency index score")
    sustainability_rating: Optional[str] = Field(None, description="Overall sustainability rating")
    certifications: list = Field(default_factory=list, description="Sustainability certifications")
    impact_commitments: dict = Field(default_factory=dict, description="Brand environmental commitments")


class SustainabilityMetricsResponse(BaseModel):
    clothing_id: int = Field(..., description="Clothing item ID")
    item_summary: dict = Field(..., description="Basic item information")
    new_garment: NewItemImpact = Field(..., description="Environmental impact of producing new equivalent")
    reuse_impact: ReuseImpact = Field(..., description="Environmental cost of reuse platform")
    avoided_impact: AvoidedImpact = Field(..., description="Net environmental benefit")
    equivalents: SustainabilityEquivalents = Field(..., description="Real-world impact equivalents")
    brand_context: BrandContext = Field(..., description="Brand sustainability information")
    calculation_metadata: dict = Field(..., description="Calculation version and data quality info")


class SwapParticipantImpact(BaseModel):
    clothing_id: int = Field(..., description="Clothing item ID")
    item_summary: dict = Field(..., description="Basic item information")
    environmental_cost: dict = Field(..., description="Total environmental cost of this item")
    condition_factor: float = Field(..., description="Condition impact factor (0.8-1.2)")
    brand_sustainability: Optional[BrandContext] = Field(None, description="Brand sustainability context")


class SwapTransportImpact(BaseModel):
    distance_km: Optional[float] = Field(None, description="Transport distance in kilometers")
    transport_method: Optional[str] = Field(None, description="Method of transportation")
    co2_emissions: float = Field(..., description="CO2 emissions from transportation")
    penalty_applied: float = Field(..., description="Score penalty applied for transport impact")


class SwapImpactComparison(BaseModel):
    item1_gets_description: str = Field(..., description="Description of what user1 receives")
    item2_gets_description: str = Field(..., description="Description of what user2 receives")
    net_environmental_change_co2: float = Field(..., description="Net CO2 change for user1 (negative = benefit)")
    net_environmental_change_water: float = Field(..., description="Net water change for user1")
    net_environmental_change_energy: float = Field(..., description="Net energy change for user1")
    impact_description: str = Field(..., description="Human-readable impact description")


class SwapScoreBreakdown(BaseModel):
    base_score: float = Field(..., description="Base score from environmental comparison")
    transport_penalty: float = Field(..., description="Penalty for transportation emissions")
    condition_bonus: float = Field(..., description="Bonus for item conditions")
    brand_bonus: float = Field(..., description="Bonus for sustainable brands")
    final_score: float = Field(..., description="Final score (0.00-10.00)")


class SwapScore(BaseModel):
    score: float = Field(..., description="Overall swap score (0.00-10.00)")
    grade_description: str = Field(..., description="Score interpretation")
    breakdown: SwapScoreBreakdown = Field(..., description="Detailed score breakdown")
    environmental_benefit: bool = Field(..., description="Whether this swap provides net environmental benefit")


class SwapImpactResponse(BaseModel):
    item1_summary: dict = Field(..., description="Summary of first clothing item")
    item2_summary: dict = Field(..., description="Summary of second clothing item")
    item1_impact: SwapParticipantImpact = Field(..., description="Environmental impact of first item")
    item2_impact: SwapParticipantImpact = Field(..., description="Environmental impact of second item")
    impact_comparison: SwapImpactComparison = Field(..., description="Comparison of environmental impacts")
    transport_impact: Optional[SwapTransportImpact] = Field(None, description="Transportation impact if applicable")
    swap_score: SwapScore = Field(..., description="Overall sustainability score")
    equivalents: SustainabilityEquivalents = Field(..., description="Real-world impact equivalents")
    recommendations: list = Field(default_factory=list, description="Recommendations for improvement")
    calculation_metadata: dict = Field(..., description="Calculation version and data quality info")