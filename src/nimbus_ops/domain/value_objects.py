from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        if self.amount < Decimal("0"):
            raise ValueError("Money cannot be negative.")
        if len(self.currency) != 3:
            raise ValueError("Currency must be an ISO-4217 code.")

    @classmethod
    def from_float(cls, amount: float, currency: str = "USD") -> "Money":
        rounded = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return cls(rounded, currency.upper())

    def add(self, other: "Money") -> "Money":
        self._assert_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def multiply(self, quantity: int | float | Decimal) -> "Money":
        value = (self.amount * Decimal(str(quantity))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return Money(value, self.currency)

    def _assert_same_currency(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise ValueError("Cannot combine amounts with different currencies.")


@dataclass(frozen=True)
class Address:
    line1: str
    city: str
    country: str
    postal_code: str
    line2: str | None = None

    def normalized(self) -> str:
        parts = [self.line1, self.line2, self.city, self.postal_code, self.country]
        return ", ".join(part.strip() for part in parts if part and part.strip())
