"""Edge case tests for financial schemas.

This module provides edge case testing for financial models
including price calculations, currency conversions, budget tracking, and
complex financial scenarios that occur in production travel booking systems.
"""

from decimal import Decimal

import pytest
from hypothesis import given, settings, strategies as st
from pydantic import ValidationError

from tripsage_core.models.schemas_common.enums import CurrencyCode
from tripsage_core.models.schemas_common.financial import (
    Budget,
    Currency,
    Deal,
    ExchangeRate,
    PaymentInfo,
    Price,
    PriceBreakdown,
    PriceRange,
    TaxInfo,
)


class TestPriceEdgeCases:
    """Test edge cases for Price model."""

    def test_price_precision_handling(self):
        """Test price handling with various decimal precisions."""
        # Test with high precision
        high_precision = Decimal("123.123456789")
        price = Price(amount=high_precision, currency=CurrencyCode.USD)
        assert price.amount == high_precision

        # Test with zero
        zero_price = Price(amount=Decimal(0), currency=CurrencyCode.USD)
        assert zero_price.amount == Decimal(0)

        # Test with very small amount
        tiny_amount = Decimal("0.000001")
        tiny_price = Price(amount=tiny_amount, currency=CurrencyCode.USD)
        assert tiny_price.amount == tiny_amount

        # Test with very large amount
        large_amount = Decimal("999999999.99")
        large_price = Price(amount=large_amount, currency=CurrencyCode.USD)
        assert large_price.amount == large_amount

    def test_price_conversion_edge_cases(self):
        """Test price conversion with edge case exchange rates."""
        base_price = Price(amount=Decimal(100), currency=CurrencyCode.USD)

        # Test conversion with rate of 1 (no change)
        same_currency = base_price.convert_to(CurrencyCode.EUR, Decimal(1))
        assert same_currency.amount == Decimal(100)
        assert same_currency.currency == CurrencyCode.EUR

        # Test conversion with very small rate
        tiny_rate = Decimal("0.0001")
        tiny_result = base_price.convert_to(CurrencyCode.JPY, tiny_rate)
        assert tiny_result.amount == Decimal("0.01")

        # Test conversion with very large rate
        huge_rate = Decimal(10000)
        huge_result = base_price.convert_to(CurrencyCode.JPY, huge_rate)
        assert huge_result.amount == Decimal(1000000)

        # Test conversion with precise rate
        precise_rate = Decimal("1.23456789")
        precise_result = base_price.convert_to(CurrencyCode.EUR, precise_rate)
        expected = Decimal(100) * precise_rate
        assert precise_result.amount == expected

    def test_price_formatting_edge_cases(self):
        """Test price formatting with various scenarios."""
        # Test with no symbol provided
        price = Price(amount=Decimal("99.99"), currency=CurrencyCode.USD)
        formatted = price.format()
        assert formatted == "USD99.99"

        # Test with custom symbol
        formatted_custom = price.format("$")
        assert formatted_custom == "$99.99"

        # Test with zero amount
        zero_price = Price(amount=Decimal(0), currency=CurrencyCode.USD)
        formatted_zero = zero_price.format("$")
        assert formatted_zero == "$0.00"

        # Test with pre-formatted price
        preformatted = Price(
            amount=Decimal("99.99"), currency=CurrencyCode.USD, formatted="$99.99 USD"
        )
        assert preformatted.format() == "$99.99 USD"
        assert preformatted.format("€") == "$99.99 USD"  # Should ignore new symbol

    def test_price_float_conversion(self):
        """Test price to float conversion edge cases."""
        # Test with various decimal amounts
        test_cases = [
            Decimal(0),
            Decimal("0.01"),
            Decimal("999.99"),
            Decimal("123.456"),
            Decimal("0.000001"),
        ]

        for amount in test_cases:
            price = Price(amount=amount, currency=CurrencyCode.USD)
            float_value = price.to_float()
            assert abs(float_value - float(amount)) < 1e-10


class TestPriceRangeEdgeCases:
    """Test edge cases for PriceRange model."""

    def test_price_range_boundary_conditions(self):
        """Test price range with boundary conditions."""
        # Test with same min and max (single price point)
        single_price = Price(amount=Decimal(100), currency=CurrencyCode.USD)
        single_range = PriceRange(min_price=single_price, max_price=single_price)
        assert single_range.min_price.amount == single_range.max_price.amount

        # Test average of single price point
        avg = single_range.average()
        assert avg.amount == Decimal(100)

        # Test contains with exact boundary values
        assert single_range.contains(single_price)

        # Test with very small range
        min_price = Price(amount=Decimal("99.99"), currency=CurrencyCode.USD)
        max_price = Price(amount=Decimal("100.01"), currency=CurrencyCode.USD)
        small_range = PriceRange(min_price=min_price, max_price=max_price)

        test_price = Price(amount=Decimal("100.00"), currency=CurrencyCode.USD)
        assert small_range.contains(test_price)

    def test_price_range_currency_mismatch(self):
        """Test price range validation with currency mismatches."""
        min_usd = Price(amount=Decimal(100), currency=CurrencyCode.USD)
        max_eur = Price(amount=Decimal(120), currency=CurrencyCode.EUR)

        with pytest.raises(ValidationError, match="same currency"):
            PriceRange(min_price=min_usd, max_price=max_eur)

    def test_price_range_invalid_order(self):
        """Test price range with max < min."""
        min_price = Price(amount=Decimal(200), currency=CurrencyCode.USD)
        max_price = Price(amount=Decimal(100), currency=CurrencyCode.USD)

        with pytest.raises(ValidationError, match="greater than or equal to min"):
            PriceRange(min_price=min_price, max_price=max_price)

    def test_price_range_contains_edge_cases(self):
        """Test price range contains with edge cases."""
        min_price = Price(amount=Decimal(100), currency=CurrencyCode.USD)
        max_price = Price(amount=Decimal(200), currency=CurrencyCode.USD)
        price_range = PriceRange(min_price=min_price, max_price=max_price)

        # Test with different currency
        eur_price = Price(amount=Decimal(150), currency=CurrencyCode.EUR)
        assert not price_range.contains(eur_price)

        # Test with boundary values
        assert price_range.contains(min_price)
        assert price_range.contains(max_price)

        # Test just outside boundaries
        below_min = Price(amount=Decimal("99.99"), currency=CurrencyCode.USD)
        above_max = Price(amount=Decimal("200.01"), currency=CurrencyCode.USD)
        assert not price_range.contains(below_min)
        assert not price_range.contains(above_max)


class TestPriceBreakdownEdgeCases:
    """Test edge cases for PriceBreakdown model."""

    def test_price_breakdown_rounding_tolerance(self):
        """Test price breakdown with rounding differences."""
        base = Price(amount=Decimal("100.00"), currency=CurrencyCode.USD)
        tax = Price(amount=Decimal("8.33"), currency=CurrencyCode.USD)  # 1/3 of 25
        fee = Price(amount=Decimal("5.67"), currency=CurrencyCode.USD)
        # Total should be 114.00, but due to rounding might be 113.99 or 114.01

        # Test with total that's 0.01 off (within tolerance)
        total_close = Price(amount=Decimal("114.01"), currency=CurrencyCode.USD)
        breakdown = PriceBreakdown(
            base_price=base, taxes=tax, fees=fee, total=total_close
        )
        assert breakdown.total.amount == Decimal("114.01")

        # Test with total that's exactly correct
        total_exact = Price(amount=Decimal("114.00"), currency=CurrencyCode.USD)
        breakdown_exact = PriceBreakdown(
            base_price=base, taxes=tax, fees=fee, total=total_exact
        )
        assert breakdown_exact.total.amount == Decimal("114.00")

        # Test with total that's too far off (should fail)
        total_wrong = Price(amount=Decimal("120.00"), currency=CurrencyCode.USD)
        with pytest.raises(ValidationError, match="does not match breakdown"):
            PriceBreakdown(base_price=base, taxes=tax, fees=fee, total=total_wrong)

    def test_price_breakdown_with_discounts(self):
        """Test price breakdown with discount calculations."""
        base = Price(amount=Decimal("200.00"), currency=CurrencyCode.USD)
        discount = Price(amount=Decimal("50.00"), currency=CurrencyCode.USD)
        tax = Price(amount=Decimal("15.00"), currency=CurrencyCode.USD)
        total = Price(
            amount=Decimal("165.00"), currency=CurrencyCode.USD
        )  # 200 - 50 + 15

        breakdown = PriceBreakdown(
            base_price=base, taxes=tax, discounts=discount, total=total
        )
        assert breakdown.discounts.amount == Decimal("50.00")

    def test_price_breakdown_minimal_components(self):
        """Test price breakdown with minimal required components."""
        base = Price(amount=Decimal("100.00"), currency=CurrencyCode.USD)
        total = Price(amount=Decimal("100.00"), currency=CurrencyCode.USD)

        # Only base price and total
        minimal = PriceBreakdown(base_price=base, total=total)
        assert minimal.taxes is None
        assert minimal.fees is None
        assert minimal.discounts is None

    def test_price_breakdown_currency_consistency(self):
        """Test price breakdown currency consistency validation."""
        base_usd = Price(amount=Decimal(100), currency=CurrencyCode.USD)
        tax_eur = Price(amount=Decimal(20), currency=CurrencyCode.EUR)
        total_usd = Price(amount=Decimal(120), currency=CurrencyCode.USD)

        with pytest.raises(ValidationError, match="same currency"):
            PriceBreakdown(base_price=base_usd, taxes=tax_eur, total=total_usd)


class TestBudgetEdgeCases:
    """Test edge cases for Budget model."""

    def test_budget_calculation_edge_cases(self):
        """Test budget calculation methods with edge cases."""
        total = Price(amount=Decimal(1000), currency=CurrencyCode.USD)
        spent = Price(
            amount=Decimal(1000), currency=CurrencyCode.USD
        )  # Exactly on budget

        budget = Budget(total_budget=total, spent=spent)

        # Test utilization at 100%
        utilization = budget.utilization_percentage()
        assert utilization == 100.0

        # Test remaining calculation when fully spent
        remaining = budget.calculate_remaining()
        assert remaining.amount == Decimal(0)

        # Test over budget scenario
        over_spent = Price(amount=Decimal(1200), currency=CurrencyCode.USD)
        over_budget = Budget(total_budget=total, spent=over_spent)

        assert over_budget.is_over_budget()
        over_utilization = over_budget.utilization_percentage()
        assert over_utilization == 120.0

        # Remaining should be 0 when over budget (not negative)
        over_remaining = over_budget.calculate_remaining()
        assert over_remaining.amount == Decimal(0)

    def test_budget_with_allocated_vs_spent(self):
        """Test budget calculations with both allocated and spent amounts."""
        total = Price(amount=Decimal(1000), currency=CurrencyCode.USD)
        allocated = Price(amount=Decimal(800), currency=CurrencyCode.USD)
        spent = Price(amount=Decimal(600), currency=CurrencyCode.USD)

        # When both allocated and spent are present, spent takes precedence
        budget_both = Budget(total_budget=total, allocated=allocated, spent=spent)
        remaining = budget_both.calculate_remaining()
        assert remaining.amount == Decimal(400)  # 1000 - 600

        # When only allocated is present
        budget_allocated = Budget(total_budget=total, allocated=allocated)
        remaining_allocated = budget_allocated.calculate_remaining()
        assert remaining_allocated.amount == Decimal(200)  # 1000 - 800

    def test_budget_zero_amounts(self):
        """Test budget with zero amounts."""
        total_zero = Price(amount=Decimal(0), currency=CurrencyCode.USD)
        budget_zero = Budget(total_budget=total_zero)

        # Zero budget utilization
        utilization = budget_zero.utilization_percentage()
        assert utilization == 0.0

        # Not over budget with zero amounts
        assert not budget_zero.is_over_budget()

        # Remaining should be zero
        remaining = budget_zero.calculate_remaining()
        assert remaining.amount == Decimal(0)

    def test_budget_category_validation(self):
        """Test budget category currency validation."""
        total = Price(amount=Decimal(1000), currency=CurrencyCode.USD)
        categories = {
            "flights": Price(amount=Decimal(400), currency=CurrencyCode.USD),
            "hotels": Price(
                amount=Decimal(300), currency=CurrencyCode.EUR
            ),  # Wrong currency
            "food": Price(amount=Decimal(200), currency=CurrencyCode.USD),
        }

        with pytest.raises(ValidationError, match="different currency"):
            Budget(total_budget=total, categories=categories)


class TestExchangeRateEdgeCases:
    """Test edge cases for ExchangeRate model."""

    def test_exchange_rate_conversion_precision(self):
        """Test exchange rate conversion with high precision."""
        # Test with very precise rate
        precise_rate = Decimal("1.23456789012345")
        rate = ExchangeRate(
            from_currency=CurrencyCode.USD,
            to_currency=CurrencyCode.EUR,
            rate=precise_rate,
        )

        amount = Decimal("100.00")
        converted = rate.convert(amount)
        expected = amount * precise_rate
        assert converted == expected

    def test_exchange_rate_inverse_precision(self):
        """Test exchange rate inverse calculation precision."""
        original_rate = Decimal("1.5")
        rate = ExchangeRate(
            from_currency=CurrencyCode.USD,
            to_currency=CurrencyCode.EUR,
            rate=original_rate,
        )

        inverse = rate.inverse()
        assert inverse.from_currency == CurrencyCode.EUR
        assert inverse.to_currency == CurrencyCode.USD

        # Inverse of 1.5 should be approximately 0.666...
        expected_inverse = 1 / original_rate
        assert abs(inverse.rate - expected_inverse) < Decimal("0.000001")

        # Test round-trip conversion
        amount = Decimal(100)
        converted = rate.convert(amount)
        back_converted = inverse.convert(converted)
        assert abs(back_converted - amount) < Decimal(
            "0.01"
        )  # Allow small rounding error

    def test_exchange_rate_extreme_values(self):
        """Test exchange rate with extreme values."""
        # Test with very small rate (e.g., USD to Japanese Yen in fractional terms)
        tiny_rate = Decimal("0.0001")
        tiny_rate_exchange = ExchangeRate(
            from_currency=CurrencyCode.USD, to_currency=CurrencyCode.JPY, rate=tiny_rate
        )

        amount = Decimal(1000)
        converted = tiny_rate_exchange.convert(amount)
        assert converted == Decimal("0.1")

        # Test with very large rate
        huge_rate = Decimal(10000)
        huge_rate_exchange = ExchangeRate(
            from_currency=CurrencyCode.JPY, to_currency=CurrencyCode.USD, rate=huge_rate
        )

        converted_huge = huge_rate_exchange.convert(Decimal(1))
        assert converted_huge == Decimal(10000)


class TestDealEdgeCases:
    """Test edge cases for Deal model."""

    def test_deal_validation_edge_cases(self):
        """Test deal validation with edge cases."""
        original = Price(amount=Decimal(100), currency=CurrencyCode.USD)
        final = Price(amount=Decimal(80), currency=CurrencyCode.USD)
        discount_amount = Price(amount=Decimal(20), currency=CurrencyCode.USD)

        # Valid deal
        deal = Deal(
            title="Test Deal",
            original_price=original,
            final_price=final,
            discount_amount=discount_amount,
            discount_percentage=Decimal(20),
        )
        assert deal.discount_percentage == Decimal(20)

        # Test with zero discount (no savings)
        no_discount = Deal(
            title="No Discount Deal",
            original_price=original,
            final_price=original,  # Same as original
        )
        assert no_discount.final_price.amount == no_discount.original_price.amount

        # Test with 100% discount (free)
        free_deal = Deal(
            title="Free Deal",
            original_price=original,
            final_price=Price(amount=Decimal(0), currency=CurrencyCode.USD),
            discount_percentage=Decimal(100),
        )
        assert free_deal.final_price.amount == Decimal(0)

    def test_deal_currency_mismatch_validation(self):
        """Test deal validation with currency mismatches."""
        original_usd = Price(amount=Decimal(100), currency=CurrencyCode.USD)
        final_eur = Price(amount=Decimal(80), currency=CurrencyCode.EUR)

        with pytest.raises(ValidationError, match="same currency"):
            Deal(
                title="Invalid Deal", original_price=original_usd, final_price=final_eur
            )

        # Test discount amount currency mismatch
        original = Price(amount=Decimal(100), currency=CurrencyCode.USD)
        final = Price(amount=Decimal(80), currency=CurrencyCode.USD)
        discount_eur = Price(amount=Decimal(20), currency=CurrencyCode.EUR)

        with pytest.raises(ValidationError, match="same currency"):
            Deal(
                title="Invalid Discount Currency",
                original_price=original,
                final_price=final,
                discount_amount=discount_eur,
            )

    def test_deal_invalid_final_price(self):
        """Test deal with final price greater than original."""
        original = Price(amount=Decimal(100), currency=CurrencyCode.USD)
        final_higher = Price(amount=Decimal(120), currency=CurrencyCode.USD)

        with pytest.raises(ValidationError, match="cannot be greater than original"):
            Deal(
                title="Invalid Deal", original_price=original, final_price=final_higher
            )


class TestTaxInfoEdgeCases:
    """Test edge cases for TaxInfo model."""

    def test_tax_rate_boundary_values(self):
        """Test tax rate validation with boundary values."""
        tax_amount = Price(amount=Decimal(20), currency=CurrencyCode.USD)

        # Test with 0% tax rate
        zero_tax = TaxInfo(tax_type="VAT", rate=Decimal(0), amount=tax_amount)
        assert zero_tax.rate == Decimal(0)

        # Test with 100% tax rate
        full_tax = TaxInfo(tax_type="VAT", rate=Decimal(1), amount=tax_amount)
        assert full_tax.rate == Decimal(1)

        # Test with invalid tax rate (> 100%)
        with pytest.raises(ValidationError):
            TaxInfo(
                tax_type="VAT",
                rate=Decimal("1.1"),  # 110%
                amount=tax_amount,
            )

        # Test with negative tax rate
        with pytest.raises(ValidationError):
            TaxInfo(tax_type="VAT", rate=Decimal("-0.1"), amount=tax_amount)


class TestCurrencyEdgeCases:
    """Test edge cases for Currency model."""

    def test_currency_decimal_places_validation(self):
        """Test currency decimal places validation."""
        # Test valid decimal places
        for places in range(5):  # 0 to 4
            currency = Currency(code=CurrencyCode.USD, decimal_places=places)
            assert currency.decimal_places == places

        # Test invalid decimal places (too many)
        with pytest.raises(ValidationError):
            Currency(code=CurrencyCode.USD, decimal_places=5)

        # Test negative decimal places
        with pytest.raises(ValidationError):
            Currency(code=CurrencyCode.USD, decimal_places=-1)


class TestPaymentInfoEdgeCases:
    """Test edge cases for PaymentInfo model."""

    def test_payment_info_with_various_amounts(self):
        """Test payment info with various amount scenarios."""
        # Test with zero amount
        zero_payment = PaymentInfo(
            amount=Price(amount=Decimal(0), currency=CurrencyCode.USD),
            payment_method="credit_card",
            status="pending",
        )
        assert zero_payment.amount.amount == Decimal(0)

        # Test with very large amount
        large_amount = Decimal("999999999.99")
        large_payment = PaymentInfo(
            amount=Price(amount=large_amount, currency=CurrencyCode.USD),
            payment_method="bank_transfer",
            status="completed",
        )
        assert large_payment.amount.amount == large_amount

        # Test with very precise amount
        precise_amount = Decimal("123.456789")
        precise_payment = PaymentInfo(
            amount=Price(amount=precise_amount, currency=CurrencyCode.USD),
            payment_method="crypto",
            status="pending",
        )
        assert precise_payment.amount.amount == precise_amount


@given(
    amount=st.decimals(min_value=0, max_value=999999, places=2),
    currency=st.sampled_from(list(CurrencyCode)),
)
@settings(max_examples=50, deadline=None)
def test_price_property_based(amount: Decimal, currency: CurrencyCode):
    """Test Price model with property-based testing."""
    try:
        price = Price(amount=amount, currency=currency)

        # Verify basic properties
        assert price.amount >= 0
        assert price.currency == currency

        # Test float conversion
        float_val = price.to_float()
        assert isinstance(float_val, float)
        assert float_val >= 0

        # Test formatting
        formatted = price.format()
        assert isinstance(formatted, str)
        assert str(currency.value) in formatted

    except ValidationError:
        # Should only fail for negative amounts
        assert amount < 0


@given(
    base_amount=st.decimals(min_value=1, max_value=1000, places=2),
    tax_rate=st.decimals(min_value=0, max_value=1, places=4),
    fee_amount=st.decimals(min_value=0, max_value=100, places=2),
)
@settings(max_examples=30, deadline=None)
def test_price_breakdown_property_based(
    base_amount: Decimal, tax_rate: Decimal, fee_amount: Decimal
):
    """Test PriceBreakdown with property-based testing."""
    try:
        base = Price(amount=base_amount, currency=CurrencyCode.USD)
        tax_amount = base_amount * tax_rate
        tax = Price(amount=tax_amount, currency=CurrencyCode.USD)
        fee = Price(amount=fee_amount, currency=CurrencyCode.USD)

        # Calculate expected total
        expected_total = base_amount + tax_amount + fee_amount
        total = Price(amount=expected_total, currency=CurrencyCode.USD)

        breakdown = PriceBreakdown(base_price=base, taxes=tax, fees=fee, total=total)

        # Verify the breakdown is valid
        assert breakdown.base_price.amount == base_amount
        assert breakdown.taxes.amount == tax_amount
        assert breakdown.fees.amount == fee_amount
        assert breakdown.total.amount == expected_total

    except ValidationError as e:
        # Should only fail due to rounding differences > 0.01
        assert "does not match breakdown" in str(e)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
