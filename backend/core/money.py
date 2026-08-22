"""Exact monetary types shared by API validation and domain services."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated

from pydantic import Field, PlainSerializer


MONEY_QUANTUM = Decimal("0.01")


def quantize_money(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def as_decimal(value: Decimal | int | float | str | None) -> Decimal:
    """Convert persisted/request numeric values without introducing binary float error."""
    if value is None:
        return Decimal("0")
    return value if isinstance(value, Decimal) else Decimal(str(value))


_json_number = PlainSerializer(lambda value: float(value), return_type=float, when_used="json")

Money = Annotated[
    Decimal,
    Field(max_digits=14, decimal_places=2),
    _json_number,
]
PositiveMoney = Annotated[
    Decimal,
    Field(gt=0, max_digits=14, decimal_places=2),
    _json_number,
]
NonNegativeMoney = Annotated[
    Decimal,
    Field(ge=0, max_digits=14, decimal_places=2),
    _json_number,
]
Percentage = Annotated[
    Decimal,
    Field(ge=0, le=100, max_digits=7, decimal_places=4),
    _json_number,
]
NonNegativeUnitMoney = Annotated[
    Decimal,
    Field(ge=0, max_digits=18, decimal_places=6),
    _json_number,
]
