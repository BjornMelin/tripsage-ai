"""Financial models and schemas for TripSage AI.

This module contains price, currency, budget, and payment-related models
used across the application for consistent financial data handling.
"""

from decimal import Decimal

from pydantic import Field, model_validator

from tripsage_core.models.base_core_model import TripSageModel

from .enums import CurrencyCode


class Currency(TripSageModel):
    """Currency information with metadata."""

    code: CurrencyCode = Field(description="ISO 4217 currency code")
    symbol: str | None = Field(None, description="Currency symbol")
    name: str | None = Field(None, description="Currency name")
    decimal_places: int = Field(2, ge=0, le=4, description="Number of decimal places")


class Price(TripSageModel):
    """Price with currency and optional breakdown."""

    amount: Decimal = Field(description="Price amount", ge=0)
    currency: CurrencyCode = Field(description="Currency code")
    formatted: str | None = Field(None, description="Formatted price string")

    def to_float(self) -> float:
        """Convert amount to float for calculations."""
        return float(self.amount)

    def format(self, currency_symbol: str | None = None) -> str:
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

    @model_validator(mode="after")
    def validate_price_range(self) -> "PriceRange":
        """Validate max price is greater than or equal to min price."""
        if self.min_price.currency != self.max_price.currency:
            raise ValueError("Min and max prices must use the same currency")
        if self.max_price.amount < self.min_price.amount:
            raise ValueError("Max price must be greater than or equal to min price")
        return self

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
    taxes: Price | None = Field(None, description="Tax amount")
    fees: Price | None = Field(None, description="Additional fees")
    discounts: Price | None = Field(None, description="Discount amount")
    total: Price = Field(description="Total price")

    @model_validator(mode="after")
    def validate_price_breakdown(self) -> "PriceBreakdown":
        """Validate total price matches breakdown components."""
        # Validate currency consistency
        currencies = {self.base_price.currency}
        if self.taxes:
            currencies.add(self.taxes.currency)
        if self.fees:
            currencies.add(self.fees.currency)
        if self.discounts:
            currencies.add(self.discounts.currency)
        currencies.add(self.total.currency)

        if len(currencies) > 1:
            raise ValueError("All price components must use the same currency")

        # Calculate expected total
        expected_total = self.base_price.amount
        if self.taxes:
            expected_total += self.taxes.amount
        if self.fees:
            expected_total += self.fees.amount
        if self.discounts:
            expected_total -= self.discounts.amount

        # Allow small rounding differences
        if abs(self.total.amount - expected_total) > Decimal("0.01"):
            raise ValueError("Total price does not match breakdown components")

        return self


class Budget(TripSageModel):
    """Budget allocation and tracking."""

    total_budget: Price = Field(description="Total budget amount")
    allocated: Price | None = Field(None, description="Allocated amount")
    spent: Price | None = Field(None, description="Spent amount")
    remaining: Price | None = Field(None, description="Remaining amount")
    categories: dict[str, Price] | None = Field(None, description="Budget by category")

    @model_validator(mode="after")
    def validate_budget_currencies(self) -> "Budget":
        """Validate all amounts use the same currency."""
        base_currency = self.total_budget.currency

        if self.allocated and self.allocated.currency != base_currency:
            raise ValueError("All budget amounts must use the same currency")
        if self.spent and self.spent.currency != base_currency:
            raise ValueError("All budget amounts must use the same currency")
        if self.remaining and self.remaining.currency != base_currency:
            raise ValueError("All budget amounts must use the same currency")

        # Validate category currencies
        if self.categories:
            for category, price in self.categories.items():
                if price.currency != base_currency:
                    raise ValueError(f"Category '{category}' uses different currency")

        return self

    def calculate_remaining(self) -> Price:
        """Calculate remaining budget."""
        if self.spent:
            remaining_amount = self.total_budget.amount - self.spent.amount
        elif self.allocated:
            remaining_amount = self.total_budget.amount - self.allocated.amount
        else:
            remaining_amount = self.total_budget.amount

        return Price(
            amount=max(Decimal(0), remaining_amount),
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
    payment_method: str | None = Field(None, description="Payment method")
    transaction_id: str | None = Field(None, description="Transaction identifier")
    reference: str | None = Field(None, description="Payment reference")
    status: str | None = Field(None, description="Payment status")


class ExchangeRate(TripSageModel):
    """Currency exchange rate information."""

    from_currency: CurrencyCode = Field(description="Source currency")
    to_currency: CurrencyCode = Field(description="Target currency")
    rate: Decimal = Field(description="Exchange rate", gt=0)
    timestamp: str | None = Field(None, description="Rate timestamp")
    source: str | None = Field(None, description="Rate source")

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


class Deal(TripSageModel):
    """Deal or discount information."""

    title: str = Field(description="Deal title")
    description: str | None = Field(None, description="Deal description")
    discount_amount: Price | None = Field(None, description="Discount amount")
    discount_percentage: Decimal | None = Field(
        None, description="Discount percentage", ge=0, le=100
    )
    original_price: Price = Field(description="Original price before discount")
    final_price: Price = Field(description="Final price after discount")
    valid_until: str | None = Field(None, description="Deal expiration")

    @model_validator(mode="after")
    def validate_deal(self) -> "Deal":
        """Validate deal consistency."""
        # Validate currency consistency
        if self.original_price.currency != self.final_price.currency:
            raise ValueError("Original and final prices must use the same currency")

        # Validate final price is not greater than original
        if self.final_price.amount > self.original_price.amount:
            raise ValueError("Final price cannot be greater than original price")

        # Validate discount amount if provided
        if (
            self.discount_amount
            and self.discount_amount.currency != self.original_price.currency
        ):
            raise ValueError("Discount amount must use the same currency as prices")

        return self
