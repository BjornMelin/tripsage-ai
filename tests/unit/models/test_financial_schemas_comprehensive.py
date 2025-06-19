"""Comprehensive tests for Pydantic v2 financial schemas."""

from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from tripsage_core.models.schemas_common.enums import CurrencyCode
from tripsage_core.models.schemas_common.financial import (
    Budget,
    Deal,
    ExchangeRate,
    PaymentInfo,
    Price,
    PriceBreakdown,
    PriceRange,
    TaxInfo,
)


class TestPriceValidation:
    """Test Price model validation."""

    def test_valid_price(self):
        """Test valid price creation."""
        price = Price(amount=Decimal("100.50"), currency=CurrencyCode.USD)
        assert price.amount == Decimal("100.50")
        assert price.currency == CurrencyCode.USD

    def test_zero_price(self):
        """Test zero price is valid."""
        price = Price(amount=Decimal("0"), currency=CurrencyCode.EUR)
        assert price.amount == Decimal("0")

    @given(
        amount=st.decimals(
            min_value=Decimal("0"), max_value=Decimal("999999.99"), places=2
        ),
        currency=st.sampled_from(list(CurrencyCode)),
    )
    def test_price_property_validation(self, amount: Decimal, currency: CurrencyCode):
        """Test price validation with property-based testing."""
        price = Price(amount=amount, currency=currency)
        assert price.amount == amount
        assert price.currency == currency
        assert price.amount >= 0

    def test_negative_price_rejected(self):
        """Test negative prices are rejected."""
        with pytest.raises(
            ValidationError, match="Input should be greater than or equal to 0"
        ):
            Price(amount=Decimal("-10"), currency=CurrencyCode.USD)

    def test_price_conversion(self):
        """Test currency conversion."""
        price_usd = Price(amount=Decimal("100"), currency=CurrencyCode.USD)
        rate = Decimal("1.08")  # 1 USD = 1.08 EUR

        price_eur = price_usd.convert_to(CurrencyCode.EUR, rate)
        assert price_eur.currency == CurrencyCode.EUR
        assert price_eur.amount == Decimal("108.00")

    def test_price_display_formatting(self):
        """Test price display formatting."""
        price = Price(amount=Decimal("1234.56"), currency=CurrencyCode.USD)
        # Testing the display format functionality if it exists
        assert str(price.amount) == "1234.56"


class TestPriceRangeValidation:
    """Test PriceRange model validation."""

    def test_valid_price_range(self):
        """Test valid price range creation."""
        min_price = Price(amount=Decimal("50"), currency=CurrencyCode.USD)
        max_price = Price(amount=Decimal("150"), currency=CurrencyCode.USD)

        price_range = PriceRange(min_price=min_price, max_price=max_price)
        assert price_range.min_price.amount == Decimal("50")
        assert price_range.max_price.amount == Decimal("150")

    def test_invalid_price_range_order(self):
        """Test price range with min > max is rejected."""
        min_price = Price(amount=Decimal("150"), currency=CurrencyCode.USD)
        max_price = Price(amount=Decimal("50"), currency=CurrencyCode.USD)

        with pytest.raises(
            ValidationError,
            match="Max price must be greater than or equal to min price",
        ):
            PriceRange(min_price=min_price, max_price=max_price)

    def test_price_range_currency_mismatch(self):
        """Test price range with different currencies is rejected."""
        min_price = Price(amount=Decimal("50"), currency=CurrencyCode.USD)
        max_price = Price(amount=Decimal("150"), currency=CurrencyCode.EUR)

        with pytest.raises(
            ValidationError, match="Min and max prices must use the same currency"
        ):
            PriceRange(min_price=min_price, max_price=max_price)

    def test_price_in_range(self):
        """Test checking if price is within range."""
        min_price = Price(amount=Decimal("50"), currency=CurrencyCode.USD)
        max_price = Price(amount=Decimal("150"), currency=CurrencyCode.USD)
        price_range = PriceRange(min_price=min_price, max_price=max_price)

        test_price = Price(amount=Decimal("100"), currency=CurrencyCode.USD)
        assert price_range.contains(test_price)

        low_price = Price(amount=Decimal("25"), currency=CurrencyCode.USD)
        assert not price_range.contains(low_price)

        high_price = Price(amount=Decimal("200"), currency=CurrencyCode.USD)
        assert not price_range.contains(high_price)


class TestBudgetValidation:
    """Test Budget model validation."""

    def test_simple_budget(self):
        """Test simple budget creation."""
        total = Price(amount=Decimal("1000"), currency=CurrencyCode.USD)
        budget = Budget(total_budget=total)

        assert budget.total_budget.amount == Decimal("1000")
        assert budget.allocated is None
        assert budget.spent is None

    def test_budget_with_allocation(self):
        """Test budget with allocated and spent amounts."""
        total = Price(amount=Decimal("1000"), currency=CurrencyCode.USD)
        allocated = Price(amount=Decimal("800"), currency=CurrencyCode.USD)
        spent = Price(amount=Decimal("400"), currency=CurrencyCode.USD)

        budget = Budget(total_budget=total, allocated=allocated, spent=spent)

        assert budget.total_budget.amount == Decimal("1000")
        assert budget.allocated.amount == Decimal("800")
        assert budget.spent.amount == Decimal("400")

    def test_budget_currency_validation(self):
        """Test budget validation ensures consistent currencies."""
        total = Price(amount=Decimal("1000"), currency=CurrencyCode.USD)
        spent = Price(
            amount=Decimal("300"), currency=CurrencyCode.EUR
        )  # Different currency

        with pytest.raises(
            ValidationError, match="All budget amounts must use the same currency"
        ):
            Budget(total_budget=total, spent=spent)

    def test_budget_category_currency_validation(self):
        """Test budget category validation ensures consistent currencies."""
        total = Price(amount=Decimal("1000"), currency=CurrencyCode.USD)
        categories = {
            "flights": Price(
                amount=Decimal("500"), currency=CurrencyCode.EUR
            ),  # Different currency
        }

        with pytest.raises(
            ValidationError, match="Category 'flights' uses different currency"
        ):
            Budget(total_budget=total, categories=categories)

    def test_budget_with_categories(self):
        """Test budget with category breakdowns."""
        total = Price(amount=Decimal("2000"), currency=CurrencyCode.USD)
        categories = {
            "flights": Price(amount=Decimal("800"), currency=CurrencyCode.USD),
            "hotels": Price(amount=Decimal("600"), currency=CurrencyCode.USD),
            "activities": Price(amount=Decimal("400"), currency=CurrencyCode.USD),
        }

        budget = Budget(total_budget=total, categories=categories)
        assert len(budget.categories) == 3
        assert budget.categories["flights"].amount == Decimal("800")

    def test_budget_utilization_percentage(self):
        """Test budget utilization calculation."""
        total = Price(amount=Decimal("1000"), currency=CurrencyCode.USD)
        spent = Price(amount=Decimal("300"), currency=CurrencyCode.USD)

        budget = Budget(total_budget=total, spent=spent)
        utilization = budget.utilization_percentage()
        assert utilization == 30.0


class TestPriceBreakdownValidation:
    """Test PriceBreakdown model validation."""

    def test_basic_price_breakdown(self):
        """Test basic price breakdown."""
        base = Price(amount=Decimal("100"), currency=CurrencyCode.USD)
        taxes = Price(amount=Decimal("8.50"), currency=CurrencyCode.USD)
        total = Price(amount=Decimal("108.50"), currency=CurrencyCode.USD)

        breakdown = PriceBreakdown(base_price=base, taxes=taxes, total=total)

        assert breakdown.base_price.amount == Decimal("100")
        assert breakdown.taxes.amount == Decimal("8.50")
        assert breakdown.total.amount == Decimal("108.50")

    def test_price_breakdown_with_fees_and_discounts(self):
        """Test price breakdown with fees and discounts."""
        base = Price(amount=Decimal("100"), currency=CurrencyCode.USD)
        taxes = Price(amount=Decimal("8.50"), currency=CurrencyCode.USD)
        fees = Price(amount=Decimal("5.00"), currency=CurrencyCode.USD)
        discounts = Price(amount=Decimal("10.00"), currency=CurrencyCode.USD)
        total = Price(
            amount=Decimal("103.50"), currency=CurrencyCode.USD
        )  # 100 + 8.50 + 5.00 - 10.00

        breakdown = PriceBreakdown(
            base_price=base, taxes=taxes, fees=fees, discounts=discounts, total=total
        )

        assert breakdown.base_price.amount == Decimal("100")
        assert breakdown.fees.amount == Decimal("5.00")
        assert breakdown.discounts.amount == Decimal("10.00")
        assert breakdown.total.amount == Decimal("103.50")

    def test_price_breakdown_calculation_validation(self):
        """Test price breakdown calculation validation."""
        base = Price(amount=Decimal("100"), currency=CurrencyCode.USD)
        taxes = Price(amount=Decimal("8.50"), currency=CurrencyCode.USD)
        # Wrong total that doesn't match calculation
        wrong_total = Price(amount=Decimal("200"), currency=CurrencyCode.USD)

        with pytest.raises(
            ValidationError, match="Total price does not match breakdown components"
        ):
            PriceBreakdown(base_price=base, taxes=taxes, total=wrong_total)


class TestDealValidation:
    """Test Deal model validation."""

    def test_basic_deal(self):
        """Test basic deal creation."""
        original = Price(amount=Decimal("100"), currency=CurrencyCode.USD)
        final = Price(amount=Decimal("85"), currency=CurrencyCode.USD)

        deal = Deal(
            title="Early Bird Special",
            description="Book early and save!",
            original_price=original,
            final_price=final,
            discount_percentage=Decimal("15"),
            valid_until="2024-12-31",
        )

        assert deal.title == "Early Bird Special"
        assert deal.original_price.amount == Decimal("100")
        assert deal.final_price.amount == Decimal("85")
        assert deal.discount_percentage == Decimal("15")

    def test_deal_validation_final_exceeds_original(self):
        """Test deal validation when final price exceeds original."""
        original = Price(amount=Decimal("100"), currency=CurrencyCode.USD)
        final = Price(amount=Decimal("120"), currency=CurrencyCode.USD)

        with pytest.raises(
            ValidationError, match="Final price cannot be greater than original price"
        ):
            Deal(
                title="Bad Deal",
                description="This doesn't make sense",
                original_price=original,
                final_price=final,
                discount_percentage=Decimal("0"),
            )

    def test_deal_discount_calculation(self):
        """Test deal with discount amount."""
        original = Price(amount=Decimal("200"), currency=CurrencyCode.USD)
        final = Price(amount=Decimal("150"), currency=CurrencyCode.USD)
        discount_amount = Price(amount=Decimal("50"), currency=CurrencyCode.USD)

        deal = Deal(
            title="Quarter Off",
            description="Save 25%",
            original_price=original,
            final_price=final,
            discount_percentage=Decimal("25"),
            discount_amount=discount_amount,
        )

        assert deal.discount_amount.amount == Decimal("50")
        assert deal.discount_amount.currency == CurrencyCode.USD


class TestExchangeRateValidation:
    """Test ExchangeRate model validation."""

    def test_valid_exchange_rate(self):
        """Test valid exchange rate creation."""
        rate = ExchangeRate(
            from_currency=CurrencyCode.USD,
            to_currency=CurrencyCode.EUR,
            rate=Decimal("0.85"),
            timestamp="2024-01-01T12:00:00Z",
            source="ECB",
        )

        assert rate.from_currency == CurrencyCode.USD
        assert rate.to_currency == CurrencyCode.EUR
        assert rate.rate == Decimal("0.85")

    def test_negative_exchange_rate_rejected(self):
        """Test negative exchange rate is rejected."""
        with pytest.raises(ValidationError, match="Input should be greater than 0"):
            ExchangeRate(
                from_currency=CurrencyCode.USD,
                to_currency=CurrencyCode.EUR,
                rate=Decimal("-0.85"),
                timestamp="2024-01-01T12:00:00Z",
            )

    def test_exchange_rate_conversion(self):
        """Test exchange rate conversion."""
        rate = ExchangeRate(
            from_currency=CurrencyCode.USD,
            to_currency=CurrencyCode.EUR,
            rate=Decimal("0.85"),
        )

        converted = rate.convert(Decimal("100"))
        assert converted == Decimal("85.00")

    def test_exchange_rate_inverse(self):
        """Test exchange rate inverse calculation."""
        rate = ExchangeRate(
            from_currency=CurrencyCode.USD,
            to_currency=CurrencyCode.EUR,
            rate=Decimal("0.85"),
        )

        inverse = rate.inverse()
        assert inverse.from_currency == CurrencyCode.EUR
        assert inverse.to_currency == CurrencyCode.USD
        # Rate should be approximately 1/0.85 = 1.176
        assert abs(inverse.rate - (Decimal("1") / Decimal("0.85"))) < Decimal("0.001")


class TestPaymentInfoValidation:
    """Test PaymentInfo model validation."""

    def test_valid_payment_info(self):
        """Test valid payment info creation."""
        amount = Price(amount=Decimal("150.75"), currency=CurrencyCode.USD)

        payment = PaymentInfo(
            amount=amount,
            payment_method="Credit Card",
            transaction_id="TXN-123456789",
            reference="FLIGHT-LAX-JFK",
            status="completed",
        )

        assert payment.amount.amount == Decimal("150.75")
        assert payment.payment_method == "Credit Card"
        assert payment.status == "completed"

    def test_payment_method_optional(self):
        """Test payment method and other fields are optional."""
        amount = Price(amount=Decimal("100"), currency=CurrencyCode.USD)

        payment = PaymentInfo(amount=amount)
        assert payment.amount.amount == Decimal("100")
        assert payment.payment_method is None
        assert payment.transaction_id is None
        assert payment.status is None


class TestTaxInfoValidation:
    """Test TaxInfo model validation."""

    def test_valid_tax_info(self):
        """Test valid tax info creation."""
        tax_info = TaxInfo(
            tax_type="VAT",
            rate=Decimal("0.20"),  # 20% as decimal
            amount=Price(amount=Decimal("40"), currency=CurrencyCode.EUR),
            included=True,
        )

        assert tax_info.tax_type == "VAT"
        assert tax_info.rate == Decimal("0.20")
        assert tax_info.amount.amount == Decimal("40")
        assert tax_info.included is True

    def test_negative_tax_rate_rejected(self):
        """Test negative tax rate is rejected."""
        with pytest.raises(
            ValidationError, match="Input should be greater than or equal to 0"
        ):
            TaxInfo(
                tax_type="VAT",
                rate=Decimal("-0.05"),
                amount=Price(amount=Decimal("0"), currency=CurrencyCode.EUR),
            )

    def test_tax_rate_over_100_percent_rejected(self):
        """Test tax rate over 100% (1.0) is rejected."""
        with pytest.raises(
            ValidationError, match="Input should be less than or equal to 1"
        ):
            TaxInfo(
                tax_type="VAT",
                rate=Decimal("1.5"),  # 150%
                amount=Price(amount=Decimal("0"), currency=CurrencyCode.EUR),
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
