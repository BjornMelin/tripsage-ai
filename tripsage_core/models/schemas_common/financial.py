"""
Financial models and schemas for TripSage AI.

This module contains price, currency, budget, and payment-related models
used across the application for consistent financial data handling.
"""

from decimal import Decimal
from typing import Dict, Optional

from pydantic import Field, field_validator

from tripsage_core.models.base import TripSageModel

from .enums import CurrencyCode


class Currency(TripSageModel):
    """Currency information with metadata."""

    code: CurrencyCode = Field(description="ISO 4217 currency code")
    symbol: Optional[str] = Field(None, description="Currency symbol")
    name: Optional[str] = Field(None, description="Currency name")
    decimal_places: int = Field(2, ge=0, le=4, description="Number of decimal places")

    @field_validator("decimal_places")
    @classmethod
    def validate_decimal_places(cls, v: int) -> int:
        """Validate decimal places are reasonable."""
        if not 0 <= v <= 4:
            raise ValueError("Decimal places must be between 0 and 4")
        return v


class Price(TripSageModel):
    """Price with currency and optional breakdown."""

    amount: Decimal = Field(description="Price amount", ge=0)
    currency: CurrencyCode = Field(description="Currency code")
    formatted: Optional[str] = Field(None, description="Formatted price string")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Validate price amount is non-negative."""
        if v < 0:
            raise ValueError("Price amount must be non-negative")
        return v

    def to_float(self) -> float:
        """Convert amount to float for calculations."""
        return float(self.amount)

    def format(self, currency_symbol: Optional[str] = None) -> str:
        """Format price with currency symbol."""
        if self.formatted:
            return self.formatted

        symbol = currency_symbol or str(self.currency.value)
        return f"{symbol}{self.amount:.2f}"

    def convert_to(
        self, target_currency: CurrencyCode, exchange_rate: Decimal
    ) -> "Price":
        """Convert price to another currency using exchange rate."""
        new_amount = self.amount * exchange_rate
        return Price(amount=new_amount, currency=target_currency)


class PriceRange(TripSageModel):
    """Price range with minimum and maximum values."""

    min_price: Price = Field(description="Minimum price")
    max_price: Price = Field(description="Maximum price")

    @field_validator("max_price")
    @classmethod
    def validate_max_price(cls, v: Price, info) -> Price:
        """Validate max price is greater than or equal to min price."""
        if "min_price" in info.data:
            min_price = info.data["min_price"]
            if v.currency != min_price.currency:
                raise ValueError("Min and max prices must use the same currency")
            if v.amount < min_price.amount:
                raise ValueError("Max price must be greater than or equal to min price")
        return v

    def contains(self, price: Price) -> bool:
        """Check if a price falls within this range."""
        if price.currency != self.min_price.currency:
            return False
        return self.min_price.amount <= price.amount <= self.max_price.amount

    def average(self) -> Price:
        """Calculate average price in the range."""
        avg_amount = (self.min_price.amount + self.max_price.amount) / 2
        return Price(amount=avg_amount, currency=self.min_price.currency)


class PriceBreakdown(TripSageModel):
    """Detailed price breakdown with components."""

    base_price: Price = Field(description="Base price")
    taxes: Optional[Price] = Field(None, description="Tax amount")
    fees: Optional[Price] = Field(None, description="Additional fees")
    discounts: Optional[Price] = Field(None, description="Discount amount")
    total: Price = Field(description="Total price")

    @field_validator("total")
    @classmethod
    def validate_total(cls, v: Price, info) -> Price:
        """Validate total price matches breakdown components."""
        if "base_price" not in info.data:
            return v

        base_price = info.data["base_price"]
        if v.currency != base_price.currency:
            raise ValueError("All price components must use the same currency")

        # Calculate expected total
        expected_total = base_price.amount

        if "taxes" in info.data and info.data["taxes"]:
            taxes = info.data["taxes"]
            if taxes.currency != base_price.currency:
                raise ValueError("All price components must use the same currency")
            expected_total += taxes.amount

        if "fees" in info.data and info.data["fees"]:
            fees = info.data["fees"]
            if fees.currency != base_price.currency:
                raise ValueError("All price components must use the same currency")
            expected_total += fees.amount

        if "discounts" in info.data and info.data["discounts"]:
            discounts = info.data["discounts"]
            if discounts.currency != base_price.currency:
                raise ValueError("All price components must use the same currency")
            expected_total -= discounts.amount

        # Allow small rounding differences
        if abs(v.amount - expected_total) > Decimal("0.01"):
            raise ValueError("Total price does not match breakdown components")

        return v


class Budget(TripSageModel):
    """Budget allocation and tracking."""

    total_budget: Price = Field(description="Total budget amount")
    allocated: Optional[Price] = Field(None, description="Allocated amount")
    spent: Optional[Price] = Field(None, description="Spent amount")
    remaining: Optional[Price] = Field(None, description="Remaining amount")
    categories: Optional[Dict[str, Price]] = Field(
        None, description="Budget by category"
    )

    @field_validator("allocated", "spent", "remaining")
    @classmethod
    def validate_currency_consistency(cls, v: Optional[Price], info) -> Optional[Price]:
        """Validate all amounts use the same currency."""
        if v is None:
            return v

        if "total_budget" in info.data:
            total_budget = info.data["total_budget"]
            if v.currency != total_budget.currency:
                raise ValueError("All budget amounts must use the same currency")

        return v

    def calculate_remaining(self) -> Price:
        """Calculate remaining budget."""
        if self.spent:
            remaining_amount = self.total_budget.amount - self.spent.amount
        elif self.allocated:
            remaining_amount = self.total_budget.amount - self.allocated.amount
        else:
            remaining_amount = self.total_budget.amount

        return Price(
            amount=max(Decimal("0"), remaining_amount),
            currency=self.total_budget.currency,
        )

    def utilization_percentage(self) -> float:
        """Calculate budget utilization as percentage."""
        if not self.spent or self.total_budget.amount == 0:
            return 0.0

        return float((self.spent.amount / self.total_budget.amount) * 100)

    def is_over_budget(self) -> bool:
        """Check if spending exceeds budget."""
        if not self.spent:
            return False
        return self.spent.amount > self.total_budget.amount


class PaymentInfo(TripSageModel):
    """Payment information and metadata."""

    amount: Price = Field(description="Payment amount")
    payment_method: Optional[str] = Field(None, description="Payment method")
    transaction_id: Optional[str] = Field(None, description="Transaction identifier")
    reference: Optional[str] = Field(None, description="Payment reference")
    status: Optional[str] = Field(None, description="Payment status")

    @field_validator("transaction_id")
    @classmethod
    def validate_transaction_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate transaction ID format."""
        if v is None:
            return v

        # Basic validation - should not be empty and reasonable length
        if not v.strip() or len(v) > 100:
            raise ValueError(
                "Transaction ID must be non-empty and less than 100 characters"
            )

        return v.strip()


class ExchangeRate(TripSageModel):
    """Currency exchange rate information."""

    from_currency: CurrencyCode = Field(description="Source currency")
    to_currency: CurrencyCode = Field(description="Target currency")
    rate: Decimal = Field(description="Exchange rate", gt=0)
    timestamp: Optional[str] = Field(None, description="Rate timestamp")
    source: Optional[str] = Field(None, description="Rate source")

    @field_validator("rate")
    @classmethod
    def validate_rate(cls, v: Decimal) -> Decimal:
        """Validate exchange rate is positive."""
        if v <= 0:
            raise ValueError("Exchange rate must be positive")
        return v

    def convert(self, amount: Decimal) -> Decimal:
        """Convert amount using this exchange rate."""
        return amount * self.rate

    def inverse(self) -> "ExchangeRate":
        """Get the inverse exchange rate."""
        return ExchangeRate(
            from_currency=self.to_currency,
            to_currency=self.from_currency,
            rate=1 / self.rate,
            timestamp=self.timestamp,
            source=self.source,
        )


class TaxInfo(TripSageModel):
    """Tax information for prices."""

    tax_type: str = Field(description="Type of tax (VAT, GST, etc.)")
    rate: Decimal = Field(description="Tax rate as decimal (0.20 for 20%)", ge=0, le=1)
    amount: Price = Field(description="Tax amount")
    included: bool = Field(False, description="Whether tax is included in base price")

    @field_validator("rate")
    @classmethod
    def validate_tax_rate(cls, v: Decimal) -> Decimal:
        """Validate tax rate is between 0 and 100%."""
        if not 0 <= v <= 1:
            raise ValueError("Tax rate must be between 0 and 1 (0% to 100%)")
        return v


class Deal(TripSageModel):
    """Deal or discount information."""

    title: str = Field(description="Deal title")
    description: Optional[str] = Field(None, description="Deal description")
    discount_amount: Optional[Price] = Field(None, description="Discount amount")
    discount_percentage: Optional[Decimal] = Field(
        None, description="Discount percentage", ge=0, le=100
    )
    original_price: Price = Field(description="Original price before discount")
    final_price: Price = Field(description="Final price after discount")
    valid_until: Optional[str] = Field(None, description="Deal expiration")

    @field_validator("discount_percentage")
    @classmethod
    def validate_discount_percentage(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """Validate discount percentage is reasonable."""
        if v is None:
            return v

        if not 0 <= v <= 100:
            raise ValueError("Discount percentage must be between 0 and 100")
        return v

    @field_validator("final_price")
    @classmethod
    def validate_final_price(cls, v: Price, info) -> Price:
        """Validate final price is less than or equal to original price."""
        if "original_price" in info.data:
            original_price = info.data["original_price"]
            if v.currency != original_price.currency:
                raise ValueError("Original and final prices must use the same currency")
            if v.amount > original_price.amount:
                raise ValueError("Final price cannot be greater than original price")
        return v
