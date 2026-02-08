"""
AI Price Context (Pricing Security)

SECURITY CRITICAL: Ensures AI never exposes unauthorized pricing data.

Rules:
- AI can ONLY reference price lists allowed to the user
- AI must NEVER compare insurance prices across companies
- AI must NEVER reveal hidden price lists
- AI must NEVER suggest cheaper alternatives
"""

from sqlalchemy.orm import Session
from typing import Set, List
from dataclasses import dataclass, field

from backend.models import User, PriceList
from backend.services.pricing_service import get_pricing_service


@dataclass
class AIPriceContext:
    """
    Context for AI pricing operations.
    
    Restricts AI access to pricing data based on user permissions.
    """
    user_id: int
    user_role: str
    tenant_id: int
    allowed_price_list_ids: Set[int] = field(default_factory=set)
    can_compare_prices: bool = False
    can_see_insurance_details: bool = False
    
    SAFE_RESPONSE = "ليس لدي صلاحية للوصول لتفاصيل الأسعار في هذه الحالة"
    
    @classmethod
    def from_user(
        cls,
        db: Session,
        user: User,
        tenant_id: int
    ) -> "AIPriceContext":
        """Create context from user."""
        pricing = get_pricing_service(db, tenant_id)
        available_lists = pricing.get_available_price_lists(user)
        
        # Determine permissions based on role
        can_compare = user.role in ["admin", "accountant"]
        can_see_insurance = user.role in ["admin", "accountant"]
        
        return cls(
            user_id=user.id,
            user_role=user.role,
            tenant_id=tenant_id,
            allowed_price_list_ids={pl.id for pl in available_lists},
            can_compare_prices=can_compare,
            can_see_insurance_details=can_see_insurance
        )
    
    def can_access_price_list(self, price_list_id: int) -> bool:
        """Check if AI can access a specific price list."""
        if self.user_role == "admin":
            return True
        return price_list_id in self.allowed_price_list_ids
    
    def get_system_prompt_rules(self) -> str:
        """
        Get pricing rules for AI system prompt.
        
        MUST be included in every AI request that might involve pricing.
        """
        return f"""
=== PRICING RULES (MANDATORY) ===
Role: {self.user_role}
Allowed Price Lists: {len(self.allowed_price_list_ids)} lists

STRICT RULES FOR PRICING:
1. You can ONLY provide prices from allowed price lists
2. NEVER compare prices between different insurance companies
3. NEVER reveal insurance contract details to non-admin users
4. NEVER suggest "cheaper" alternatives or discount strategies
5. NEVER expose hidden pricing or special agreements
6. If asked about unauthorized pricing, respond: "{self.SAFE_RESPONSE}"

{"ADMIN MODE: Full access to pricing data and comparisons" if self.can_compare_prices else "RESTRICTED: Limited pricing access"}
=== END PRICING RULES ===
"""
    
    def filter_price_response(self, prices: List[dict]) -> List[dict]:
        """
        Filter AI price responses to only allowed data.
        
        Safety net - tools should also filter.
        """
        if self.user_role == "admin":
            return prices
        
        return [
            p for p in prices 
            if p.get("price_list_id") in self.allowed_price_list_ids
        ]


def create_ai_price_context(
    db: Session,
    user: User,
    tenant_id: int
) -> AIPriceContext:
    """Factory function for AI price context."""
    return AIPriceContext.from_user(db, user, tenant_id)
