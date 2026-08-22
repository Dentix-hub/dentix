"""
Price List Models (Multi Price List & Insurance Support)

This module defines models for:
- PriceList: Cash or Insurance price lists
- PriceListItem: Individual prices per procedure
- InsuranceProvider: Insurance company info
"""

from enum import Enum
from .base import (
    Base,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Numeric,
    Text,
    Date,
    ForeignKey,
    relationship,
    Index,
    datetime,
    timezone,
)
from sqlalchemy import CheckConstraint, column
from rls.schemas import Permissive, ConditionArg, Command


class PriceListType(str, Enum):
    """Types of price lists."""

    CASH = "cash"
    INSURANCE = "insurance"


class InsuranceProvider(Base):
    """
    Insurance company/provider information.

    Each tenant can have multiple insurance providers.
    """

    __tablename__ = "insurance_providers"
    __table_args__ = (Index("idx_insurance_tenant", "tenant_id"),)

    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)

    # Provider info
    name = Column(String, nullable=False)
    code = Column(String, nullable=True)  # Company code for claims
    contact_email = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    # Relationships
    price_lists = relationship("PriceList", back_populates="insurance_provider")


class PriceList(Base):
    """
    Price list for procedures.

    Each tenant can have:
    - One default CASH price list
    - Multiple INSURANCE price lists (one per provider)
    """

    __tablename__ = "price_lists"
    __table_args__ = (
        Index("idx_pricelist_tenant_type", "tenant_id", "type"),
        Index("idx_pricelist_active", "tenant_id", "is_active"),
        CheckConstraint(
            "coverage_percent >= 0 AND coverage_percent <= 100",
            name="ck_price_lists_coverage_range",
        ),
        CheckConstraint(
            "copay_percent >= 0 AND copay_percent <= 100",
            name="ck_price_lists_copay_range",
        ),
        CheckConstraint("copay_fixed >= 0", name="ck_price_lists_copay_nonnegative"),
    )

    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)

    # Basic info
    name = Column(String, nullable=False)  # e.g., "كاش", "تأمين XYZ"
    type = Column(String, default=PriceListType.CASH.value)  # cash | insurance
    description = Column(Text, nullable=True)

    # Status
    is_default = Column(Boolean, default=False)  # Default for tenant
    is_active = Column(Boolean, default=True)

    # Insurance-specific fields
    insurance_provider_id = Column(
        Integer, ForeignKey("insurance_providers.id"), nullable=True
    )
    coverage_percent = Column(Numeric(7, 4), default=100.0)
    copay_percent = Column(Numeric(7, 4), default=0.0)
    copay_fixed = Column(Numeric(14, 2), default=0.0)

    # Validity period
    effective_from = Column(Date, nullable=True)
    effective_to = Column(Date, nullable=True)

    # Metadata
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    # Relationships
    insurance_provider = relationship("InsuranceProvider", back_populates="price_lists")
    items = relationship(
        "PriceListItem", back_populates="price_list", cascade="all, delete-orphan"
    )

    def is_valid(self) -> bool:
        """Check if price list is currently valid."""
        from datetime import date, timezone

        today = date.today()

        if not self.is_active:
            return False

        if self.effective_from and today < self.effective_from:
            return False

        if self.effective_to and today > self.effective_to:
            return False

        return True


class PriceListItem(Base):
    """
    Individual price for a procedure in a price list.

    Links Procedure → PriceList with specific price.
    """

    __tablename__ = "price_list_items"
    __table_args__ = (
        Index("idx_pricelist_item_procedure", "price_list_id", "procedure_id"),
        CheckConstraint("price >= 0", name="ck_price_list_items_price_nonnegative"),
        CheckConstraint(
            "discount_percent >= 0 AND discount_percent <= 100",
            name="ck_price_list_items_discount_range",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    price_list_id = Column(
        Integer, ForeignKey("price_lists.id"), nullable=False, index=True
    )
    procedure_id = Column(
        Integer, ForeignKey("procedures.id"), nullable=False, index=True
    )

    # Pricing
    price = Column(Numeric(14, 2), nullable=False)
    discount_percent = Column(Numeric(7, 4), default=0.0)

    # Insurance-specific
    insurance_code = Column(String, nullable=True)  # Code for insurance claim
    max_units = Column(Integer, nullable=True)  # Max units covered
    requires_approval = Column(Boolean, default=False)  # Needs pre-approval

    # Metadata
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    # Relationships
    price_list = relationship("PriceList", back_populates="items")
    procedure = relationship("Procedure")

    @property
    def final_price(self) -> float:
        """Calculate final price after discount."""
        if self.discount_percent:
            return self.price * (1 - self.discount_percent / 100)
        return self.price
