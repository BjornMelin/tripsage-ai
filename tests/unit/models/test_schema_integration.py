"""Integration tests for Pydantic v2 schemas across the application.

This module tests how different schemas work together, including
serialization, deserialization, and cross-module validation.
"""

import json
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from hypothesis import given, settings, strategies as st
from pydantic import BaseModel

from tripsage.api.schemas.auth import (
    AuthResponse,
    RegisterRequest,
    Token,
    UserResponse,
)
from tripsage.api.schemas.config import ModelName
from tripsage_core.models.db.trip_collaborator import (
    PermissionLevel,
    TripCollaboratorCreate,
    TripCollaboratorDB,
)
from tripsage_core.models.schemas_common.enums import CurrencyCode
from tripsage_core.models.schemas_common.financial import (
    Budget,
    Deal,
    ExchangeRate,
    PaymentInfo,
    Price,
    PriceBreakdown,
    PriceRange,
)


class TestCompleteUserFlow:
    """Test complete user registration and authentication flow."""

    def test_user_registration_to_auth_response(self):
        """Test flow from registration request to auth response."""
        # 1. User submits registration
        register_data = RegisterRequest(
            username="newuser123",
            email="newuser@example.com",
            password="SecurePass123!",
            password_confirm="SecurePass123!",
            full_name="New User",
        )

        # Validate registration data
        assert register_data.username == "newuser123"
        assert register_data.email == "newuser@example.com"

        # 2. Simulate user creation (would happen in service layer)
        user_id = str(uuid4())
        now = datetime.utcnow()

        # 3. Create user response
        user_response = UserResponse(
            id=user_id,
            username=register_data.username,
            email=register_data.email,
            full_name=register_data.full_name,
            created_at=now,
            updated_at=now,
            is_active=True,
            is_verified=False,  # Email not verified yet
            preferences={},
        )

        # 4. Create authentication tokens
        tokens = Token(
            access_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            refresh_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.refresh...",
            token_type="bearer",
            expires_at=now + timedelta(hours=1),
        )

        # 5. Create complete auth response
        auth_response = AuthResponse(user=user_response, tokens=tokens)

        # Verify complete flow
        assert auth_response.user.username == register_data.username
        assert auth_response.user.email == register_data.email
        assert auth_response.tokens.token_type == "bearer"

        # 6. Test JSON serialization (for API response)
        json_response = auth_response.model_dump_json()
        parsed = json.loads(json_response)

        assert parsed["user"]["username"] == "newuser123"
        assert "access_token" in parsed["tokens"]
        assert "refresh_token" in parsed["tokens"]


class TestCompletePurchaseFlow:
    """Test complete purchase flow with financial schemas."""

    def test_product_purchase_with_budget(self):
        """Test purchasing a product with budget constraints."""
        # 1. User has a travel budget
        user_budget = Budget(
            total_budget=Price(amount=Decimal(5000), currency=CurrencyCode.USD),
            allocated=Price(amount=Decimal(3000), currency=CurrencyCode.USD),
            spent=Price(amount=Decimal(1500), currency=CurrencyCode.USD),
            categories={
                "flights": Price(amount=Decimal(2000), currency=CurrencyCode.USD),
                "accommodation": Price(amount=Decimal(1500), currency=CurrencyCode.USD),
                "activities": Price(amount=Decimal(500), currency=CurrencyCode.USD),
            },
        )

        # 2. Flight search returns price range
        flight_price_range = PriceRange(
            min_price=Price(amount=Decimal(350), currency=CurrencyCode.USD),
            max_price=Price(amount=Decimal(750), currency=CurrencyCode.USD),
        )

        # 3. User selects a flight
        selected_flight_price = Price(amount=Decimal(450), currency=CurrencyCode.USD)
        assert flight_price_range.contains(selected_flight_price)

        # 4. Apply a deal/discount
        flight_deal = Deal(
            title="Early Bird Special - 15% off",
            description="Book 30 days in advance for 15% discount",
            original_price=selected_flight_price,
            discount_percentage=Decimal(15),
            final_price=Price(
                amount=selected_flight_price.amount * Decimal("0.85"),
                currency=CurrencyCode.USD,
            ),
            valid_until="2024-12-31",
        )

        # 5. Calculate taxes and fees
        tax_rate = Decimal("0.075")  # 7.5% tax
        airport_fee = Decimal("25.00")

        price_breakdown = PriceBreakdown(
            base_price=flight_deal.final_price,
            taxes=Price(
                amount=(flight_deal.final_price.amount * tax_rate),
                currency=CurrencyCode.USD,
            ),
            fees=Price(amount=airport_fee, currency=CurrencyCode.USD),
            total=Price(
                amount=(
                    flight_deal.final_price.amount
                    + (flight_deal.final_price.amount * tax_rate)
                    + airport_fee
                ),
                currency=CurrencyCode.USD,
            ),
        )

        # 6. Check against budget
        remaining_flight_budget = (
            user_budget.categories["flights"].amount - user_budget.spent.amount
        )
        can_afford = price_breakdown.total.amount <= remaining_flight_budget
        assert can_afford, "User cannot afford this flight within budget"

        # 7. Create payment
        payment = PaymentInfo(
            amount=price_breakdown.total,
            payment_method="Credit Card",
            transaction_id=f"TXN-{uuid4().hex[:12].upper()}",
            reference=f"FLIGHT-{selected_flight_price.amount}",
            status="completed",
        )

        # 8. Update budget
        new_spent = Price(
            amount=user_budget.spent.amount + payment.amount.amount,
            currency=CurrencyCode.USD,
        )

        # Verify budget constraints still hold
        assert new_spent.amount <= user_budget.total_budget.amount

        # Complete flow validation
        assert payment.amount == price_breakdown.total
        assert (
            price_breakdown.base_price.amount < selected_flight_price.amount
        )  # Discount applied
        assert user_budget.utilization_percentage() < 100  # Not over budget


class TestMultiCurrencyScenarios:
    """Test multi-currency handling across schemas."""

    def test_currency_conversion_flow(self):
        """Test currency conversion in international purchases."""
        # 1. User budget in USD
        usd_budget = Budget(
            total_budget=Price(amount=Decimal(3000), currency=CurrencyCode.USD)
        )

        # 2. Hotel price in EUR
        hotel_price_eur = Price(amount=Decimal(150), currency=CurrencyCode.EUR)

        # 3. Exchange rate
        exchange_rate = ExchangeRate(
            from_currency=CurrencyCode.EUR,
            to_currency=CurrencyCode.USD,
            rate=Decimal("1.08"),  # 1 EUR = 1.08 USD
            timestamp=datetime.utcnow().isoformat(),
            source="European Central Bank",
        )

        # 4. Convert to user's currency
        hotel_price_usd = hotel_price_eur.convert_to(
            CurrencyCode.USD, exchange_rate.rate
        )

        assert hotel_price_usd.currency == CurrencyCode.USD
        assert hotel_price_usd.amount == hotel_price_eur.amount * exchange_rate.rate

        # 5. Create price breakdown with conversion fee
        conversion_fee = hotel_price_usd.amount * Decimal("0.02")  # 2% conversion fee

        total_breakdown = PriceBreakdown(
            base_price=hotel_price_usd,
            fees=Price(amount=conversion_fee, currency=CurrencyCode.USD),
            total=Price(
                amount=hotel_price_usd.amount + conversion_fee,
                currency=CurrencyCode.USD,
            ),
        )

        # 6. Verify can afford with budget
        assert total_breakdown.total.amount <= usd_budget.total_budget.amount

        # 7. Create multi-currency payment record
        payment = PaymentInfo(
            amount=total_breakdown.total,
            payment_method="International Credit Card",
            transaction_id=f"INTL-{uuid4().hex[:12].upper()}",
            reference=json.dumps(
                {
                    "original_amount": str(hotel_price_eur.amount),
                    "original_currency": hotel_price_eur.currency.value,
                    "exchange_rate": str(exchange_rate.rate),
                    "conversion_fee": str(conversion_fee),
                }
            ),
            status="completed",
        )

        # Validate complete flow
        assert payment.amount.currency == usd_budget.total_budget.currency
        assert json.loads(payment.reference)["original_currency"] == "EUR"


class TestCollaboratorPermissionFlow:
    """Test trip collaborator permission flows."""

    def test_hierarchical_permission_validation(self):
        """Test permission hierarchy in collaborative scenarios."""
        # 1. Create trip owner (implicit admin)
        owner_id = uuid4()
        trip_id = 12345

        # 2. Owner adds collaborators with different permissions
        collaborators = []

        # Add viewer
        viewer = TripCollaboratorCreate(
            trip_id=trip_id,
            user_id=uuid4(),
            permission_level=PermissionLevel.VIEW,
            added_by=owner_id,
        )
        collaborators.append(viewer)

        # Add editor
        editor = TripCollaboratorCreate(
            trip_id=trip_id,
            user_id=uuid4(),
            permission_level=PermissionLevel.EDIT,
            added_by=owner_id,
        )
        collaborators.append(editor)

        # Add admin
        admin = TripCollaboratorCreate(
            trip_id=trip_id,
            user_id=uuid4(),
            permission_level=PermissionLevel.ADMIN,
            added_by=owner_id,
        )
        collaborators.append(admin)

        # 3. Simulate DB records
        db_collaborators = []
        for i, collab in enumerate(collaborators):
            db_collab = TripCollaboratorDB(
                id=i + 1,
                trip_id=collab.trip_id,
                user_id=collab.user_id,
                permission_level=collab.permission_level,
                added_by=collab.added_by,
                added_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db_collaborators.append(db_collab)

        # 4. Test permission checks
        viewer_db, editor_db, admin_db = db_collaborators

        # Viewer permissions
        assert viewer_db.can_view
        assert not viewer_db.can_edit
        assert not viewer_db.can_manage_collaborators

        # Editor permissions
        assert editor_db.can_view
        assert editor_db.can_edit
        assert not editor_db.can_manage_collaborators

        # Admin permissions
        assert admin_db.can_view
        assert admin_db.can_edit
        assert admin_db.can_manage_collaborators

        # 5. Test permission hierarchy
        assert viewer_db.has_permission(PermissionLevel.VIEW)
        assert not viewer_db.has_permission(PermissionLevel.EDIT)
        assert not viewer_db.has_permission(PermissionLevel.ADMIN)

        assert editor_db.has_permission(PermissionLevel.VIEW)
        assert editor_db.has_permission(PermissionLevel.EDIT)
        assert not editor_db.has_permission(PermissionLevel.ADMIN)

        assert admin_db.has_permission(PermissionLevel.VIEW)
        assert admin_db.has_permission(PermissionLevel.EDIT)
        assert admin_db.has_permission(PermissionLevel.ADMIN)


class TestSchemaVersioning:
    """Test schema compatibility and versioning."""

    def test_forward_compatible_serialization(self):
        """Test that schemas can handle forward compatibility."""

        # Create a model with optional fields that might be added in future
        class UserResponseV2(UserResponse):
            # Simulating a future version with additional fields
            avatar_url: str | None = None
            bio: str | None = None
            social_links: dict[str, str] | None = None

        # Create V2 instance
        user_v2 = UserResponseV2(
            id="user123",
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True,
            is_verified=True,
            avatar_url="https://example.com/avatar.jpg",
            bio="Software developer",
            social_links={"github": "https://github.com/testuser"},
        )

        # Serialize V2
        v2_data = user_v2.model_dump()

        # V1 should be able to load V2 data (ignoring extra fields)
        user_v1 = UserResponse.model_validate(v2_data)
        assert user_v1.id == "user123"
        assert user_v1.username == "testuser"

        # V1 serialization shouldn't include V2 fields
        v1_data = user_v1.model_dump()
        assert "avatar_url" not in v1_data
        assert "bio" not in v1_data

    def test_backward_compatible_deserialization(self):
        """Test that new schemas can handle old data formats."""
        # Simulate old data format
        old_format_data = {
            "id": "user123",
            "username": "olduser",
            "email": "old@example.com",
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00",
            # Missing some fields that have defaults in current schema
        }

        # Current schema should handle old format
        user = UserResponse.model_validate(old_format_data)
        assert user.id == "user123"
        assert user.full_name is None  # Optional field
        assert user.is_active is True  # Default value
        assert user.is_verified is False  # Default value


class TestComplexValidationScenarios:
    """Test complex validation scenarios across multiple schemas."""

    def test_nested_budget_validation(self):
        """Test complex budget validation with categories."""
        # Create a budget with multiple validation constraints
        total_amount = Decimal(10000)

        budget_data = {
            "total_budget": {"amount": total_amount, "currency": "USD"},
            "allocated": {"amount": "6000", "currency": "USD"},
            "spent": {"amount": "3000", "currency": "USD"},
            "categories": {
                "flights": {"amount": "3000", "currency": "USD"},
                "accommodation": {"amount": "2500", "currency": "USD"},
                "activities": {"amount": "1000", "currency": "USD"},
                "food": {"amount": "1000", "currency": "USD"},
                "transport": {"amount": "500", "currency": "USD"},
            },
        }

        # Budget model validates currency consistency but not amount constraints
        # This should pass validation (currency consistency is met)
        budget = Budget.model_validate(budget_data)

        # Verify all constraints
        assert budget.allocated.amount <= budget.total_budget.amount
        assert budget.spent.amount <= budget.total_budget.amount

        category_sum = sum(cat.amount for cat in budget.categories.values())
        assert category_sum <= budget.total_budget.amount

    def test_price_breakdown_rounding_issues(self):
        """Test price breakdown with potential rounding issues."""
        # Simulate a calculation that might have rounding issues
        base = Decimal("99.99")
        tax_rate = Decimal("0.0875")  # 8.75% tax

        # Calculate tax with proper rounding
        tax = (base * tax_rate).quantize(Decimal("0.01"))
        total = base + tax

        breakdown = PriceBreakdown(
            base_price=Price(amount=base, currency=CurrencyCode.USD),
            taxes=Price(amount=tax, currency=CurrencyCode.USD),
            total=Price(amount=total, currency=CurrencyCode.USD),
        )

        # Should pass validation despite potential rounding
        assert breakdown.total.amount == base + tax

        # Test with a small discrepancy (within tolerance)
        breakdown_with_rounding = PriceBreakdown(
            base_price=Price(amount=base, currency=CurrencyCode.USD),
            taxes=Price(amount=tax, currency=CurrencyCode.USD),
            total=Price(
                amount=total + Decimal("0.01"),  # 1 cent difference
                currency=CurrencyCode.USD,
            ),
        )
        # Should still validate due to rounding tolerance
        assert breakdown_with_rounding.total.amount == total + Decimal("0.01")


class TestAPIResponseIntegration:
    """Test how schemas work together in API responses."""

    def test_complete_trip_planning_response(self):
        """Test a complete trip planning response with multiple schemas."""
        # Simulate a complex API response for trip planning

        # 1. User info
        user = UserResponse(
            id="user123",
            username="traveler",
            email="traveler@example.com",
            full_name="John Traveler",
            created_at=datetime.utcnow() - timedelta(days=30),
            updated_at=datetime.utcnow(),
            is_active=True,
            is_verified=True,
            preferences={
                "currency": "USD",
                "language": "en",
                "notifications": True,
            },
        )

        # 2. Trip budget
        trip_budget = Budget(
            total_budget=Price(amount=Decimal(7500), currency=CurrencyCode.USD),
            allocated=Price(amount=Decimal(6000), currency=CurrencyCode.USD),
            spent=Price(amount=Decimal(0), currency=CurrencyCode.USD),
            categories={
                "flights": Price(amount=Decimal(2500), currency=CurrencyCode.USD),
                "accommodation": Price(amount=Decimal(2000), currency=CurrencyCode.USD),
                "activities": Price(amount=Decimal(1000), currency=CurrencyCode.USD),
                "food": Price(amount=Decimal(500), currency=CurrencyCode.USD),
            },
        )

        # 3. Flight options with deals
        flight_options = []
        for i in range(3):
            base_price = Decimal(400) + (i * Decimal(100))
            deal = Deal(
                title=f"Flight Option {i + 1}",
                description=(
                    f"Direct flight with {'Premium' if i == 2 else 'Standard'} airline"
                ),
                original_price=Price(amount=base_price, currency=CurrencyCode.USD),
                discount_percentage=Decimal(10) if i == 0 else Decimal(0),
                final_price=Price(
                    amount=base_price * (Decimal("0.9") if i == 0 else Decimal(1)),
                    currency=CurrencyCode.USD,
                ),
                valid_until="2024-12-31",
            )
            flight_options.append(deal)

        # 4. Create complete response
        class TripPlanningResponse(BaseModel):
            user: UserResponse
            budget: Budget
            flight_options: list[Deal]
            booking_model: ModelName = "gpt-4"  # AI model used for recommendations
            generated_at: datetime

        response = TripPlanningResponse(
            user=user,
            budget=trip_budget,
            flight_options=flight_options,
            booking_model="gpt-4",
            generated_at=datetime.utcnow(),
        )

        # 5. Test JSON serialization (API response)
        json_response = response.model_dump_json()
        parsed = json.loads(json_response)

        # Verify structure
        assert parsed["user"]["username"] == "traveler"
        assert len(parsed["flight_options"]) == 3
        assert parsed["budget"]["total_budget"]["amount"] == "7500"
        assert parsed["booking_model"] == "gpt-4"

        # 6. Test deserialization
        restored = TripPlanningResponse.model_validate_json(json_response)
        assert restored.user.id == user.id
        assert len(restored.flight_options) == 3
        assert restored.budget.total_budget.amount == Decimal(7500)


class TestSchemaPropertyInvariants:
    """Test property invariants across schema interactions."""

    @settings(max_examples=50, deadline=None)
    @given(
        base_amount=st.decimals(
            min_value=Decimal(1), max_value=Decimal(1000), places=2
        ),
        tax_rate=st.floats(min_value=0.0, max_value=0.3),
        fee_rate=st.floats(min_value=0.0, max_value=0.1),
        discount_rate=st.floats(min_value=0.0, max_value=0.5),
    )
    def test_price_calculation_invariants(
        self,
        base_amount: Decimal,
        tax_rate: float,
        fee_rate: float,
        discount_rate: float,
    ):
        """Test that price calculations maintain invariants."""
        currency = CurrencyCode.USD

        # Create base price
        base_price = Price(amount=base_amount, currency=currency)

        # Calculate components
        tax_amount = base_amount * Decimal(str(tax_rate))
        fee_amount = base_amount * Decimal(str(fee_rate))
        discount_amount = base_amount * Decimal(str(discount_rate))

        # Ensure discount doesn't exceed base + tax + fees
        max_discount = base_amount + tax_amount + fee_amount
        if discount_amount > max_discount:
            discount_amount = max_discount * Decimal("0.9")

        # Calculate total
        total_amount = base_amount + tax_amount + fee_amount - discount_amount
        total_amount = max(Decimal(0), total_amount)  # Never negative

        # Create breakdown
        breakdown = PriceBreakdown(
            base_price=base_price,
            taxes=Price(amount=tax_amount, currency=currency)
            if tax_amount > 0
            else None,
            fees=Price(amount=fee_amount, currency=currency)
            if fee_amount > 0
            else None,
            discounts=Price(amount=discount_amount, currency=currency)
            if discount_amount > 0
            else None,
            total=Price(amount=total_amount, currency=currency),
        )

        # Invariants
        assert breakdown.total.amount >= 0  # Never negative
        assert breakdown.base_price.amount > 0  # Base is always positive

        # If there's a discount, it shouldn't exceed the sum of other components
        if breakdown.discounts:
            other_sum = breakdown.base_price.amount
            if breakdown.taxes:
                other_sum += breakdown.taxes.amount
            if breakdown.fees:
                other_sum += breakdown.fees.amount
            assert breakdown.discounts.amount <= other_sum


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
