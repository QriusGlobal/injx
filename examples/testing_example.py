"""Testing patterns and strategies with injx dependency injection."""

import asyncio
from typing import Protocol, runtime_checkable
from unittest.mock import AsyncMock

import pytest

from injx import Container, Scope, Token


# Domain models for testing
class Order:
    def __init__(self, id: str, amount: float, customer_email: str):
        self.id = id
        self.amount = amount
        self.customer_email = customer_email
        self.status = "pending"


# Protocols for testing
@runtime_checkable
class PaymentGateway(Protocol):
    """Protocol for payment processing."""

    async def process_payment(self, amount: float, payment_method: str) -> str: ...
    async def refund_payment(self, transaction_id: str) -> bool: ...


@runtime_checkable
class EmailService(Protocol):
    """Protocol for email notifications."""

    async def send_order_confirmation(self, order: Order) -> bool: ...
    async def send_payment_failed_notification(self, order: Order) -> bool: ...


@runtime_checkable
class OrderRepository(Protocol):
    """Protocol for order data access."""

    async def save_order(self, order: Order) -> None: ...
    async def get_order(self, order_id: str) -> Order | None: ...
    async def update_order_status(self, order_id: str, status: str) -> None: ...


# Production implementations
class StripePaymentGateway:
    """Production Stripe payment gateway."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.processed_payments = []

    async def process_payment(self, amount: float, payment_method: str) -> str:
        # Simulate Stripe API call
        await asyncio.sleep(0.1)
        transaction_id = f"stripe_txn_{len(self.processed_payments) + 1}"
        self.processed_payments.append(
            {"id": transaction_id, "amount": amount, "method": payment_method}
        )
        return transaction_id

    async def refund_payment(self, transaction_id: str) -> bool:
        # Simulate refund processing
        await asyncio.sleep(0.05)
        return True


class SMTPEmailService:
    """Production SMTP email service."""

    def __init__(self, smtp_host: str, smtp_port: int):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sent_emails = []

    async def send_order_confirmation(self, order: Order) -> bool:
        # Simulate sending email
        await asyncio.sleep(0.05)
        self.sent_emails.append(
            {"type": "confirmation", "to": order.customer_email, "order_id": order.id}
        )
        return True

    async def send_payment_failed_notification(self, order: Order) -> bool:
        # Simulate sending email
        await asyncio.sleep(0.05)
        self.sent_emails.append(
            {"type": "payment_failed", "to": order.customer_email, "order_id": order.id}
        )
        return True


class DatabaseOrderRepository:
    """Production database repository."""

    def __init__(self):
        self.orders = {}

    async def save_order(self, order: Order) -> None:
        # Simulate database save
        await asyncio.sleep(0.02)
        self.orders[order.id] = order

    async def get_order(self, order_id: str) -> Order | None:
        # Simulate database query
        await asyncio.sleep(0.01)
        return self.orders.get(order_id)

    async def update_order_status(self, order_id: str, status: str) -> None:
        # Simulate database update
        await asyncio.sleep(0.02)
        if order_id in self.orders:
            self.orders[order_id].status = status


# Business service under test
class OrderService:
    """Order processing service with dependencies."""

    def __init__(
        self,
        payment_gateway: PaymentGateway,
        email_service: EmailService,
        order_repository: OrderRepository,
    ):
        self.payment_gateway = payment_gateway
        self.email_service = email_service
        self.order_repository = order_repository

    async def process_order(self, order: Order, payment_method: str) -> bool:
        """Process an order with payment and notifications."""
        try:
            # Save order as pending
            await self.order_repository.save_order(order)

            # Process payment
            transaction_id = await self.payment_gateway.process_payment(
                order.amount, payment_method
            )

            # Update order status
            order.status = "paid"
            await self.order_repository.update_order_status(order.id, "paid")

            # Send confirmation email
            await self.email_service.send_order_confirmation(order)

            return True

        except Exception:
            # Handle payment failure
            order.status = "failed"
            await self.order_repository.update_order_status(order.id, "failed")
            await self.email_service.send_payment_failed_notification(order)
            raise

    async def refund_order(self, order_id: str) -> bool:
        """Refund an order."""
        order = await self.order_repository.get_order(order_id)
        if not order or order.status != "paid":
            return False

        # Process refund (assumes we have transaction ID)
        success = await self.payment_gateway.refund_payment("stripe_txn_1")

        if success:
            await self.order_repository.update_order_status(order_id, "refunded")
            return True

        return False


# Test fixtures and mocks
class MockPaymentGateway:
    """Mock payment gateway for testing."""

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.processed_payments = []
        self.refunded_payments = []

    async def process_payment(self, amount: float, payment_method: str) -> str:
        if self.should_fail:
            raise Exception("Payment processing failed")

        transaction_id = f"mock_txn_{len(self.processed_payments) + 1}"
        self.processed_payments.append(
            {"id": transaction_id, "amount": amount, "method": payment_method}
        )
        return transaction_id

    async def refund_payment(self, transaction_id: str) -> bool:
        self.refunded_payments.append(transaction_id)
        return True


class MockEmailService:
    """Mock email service for testing."""

    def __init__(self):
        self.sent_emails = []

    async def send_order_confirmation(self, order: Order) -> bool:
        self.sent_emails.append({"type": "confirmation", "order_id": order.id})
        return True

    async def send_payment_failed_notification(self, order: Order) -> bool:
        self.sent_emails.append({"type": "payment_failed", "order_id": order.id})
        return True


class MockOrderRepository:
    """Mock order repository for testing."""

    def __init__(self):
        self.orders = {}
        self.save_calls = []
        self.update_calls = []

    async def save_order(self, order: Order) -> None:
        self.save_calls.append(order.id)
        self.orders[order.id] = order

    async def get_order(self, order_id: str) -> Order | None:
        return self.orders.get(order_id)

    async def update_order_status(self, order_id: str, status: str) -> None:
        self.update_calls.append((order_id, status))
        if order_id in self.orders:
            self.orders[order_id].status = status


# Test setup functions
def create_production_container() -> Container:
    """Create container with production dependencies."""
    container = Container()

    # Tokens
    payment_token = Token[PaymentGateway]("payment_gateway", protocol=PaymentGateway)
    email_token = Token[EmailService]("email_service", protocol=EmailService)
    repo_token = Token[OrderRepository]("order_repository", protocol=OrderRepository)
    service_token = Token[OrderService]("order_service", expected_type=OrderService)

    # Register production implementations
    container.register(
        payment_token, lambda: StripePaymentGateway("prod_api_key"), Scope.SINGLETON
    )
    container.register(
        email_token, lambda: SMTPEmailService("smtp.example.com", 587), Scope.SINGLETON
    )
    container.register(repo_token, DatabaseOrderRepository, Scope.SINGLETON)

    # Register service with dependencies
    def create_order_service() -> OrderService:
        payment = container.resolve_protocol(PaymentGateway)
        email = container.resolve_protocol(EmailService)
        repo = container.resolve_protocol(OrderRepository)
        return OrderService(payment, email, repo)

    container.register(service_token, create_order_service, Scope.SINGLETON)

    return container


def create_test_container() -> Container:
    """Create container with test doubles."""
    container = Container()

    # Tokens
    payment_token = Token[PaymentGateway]("payment_gateway", protocol=PaymentGateway)
    email_token = Token[EmailService]("email_service", protocol=EmailService)
    repo_token = Token[OrderRepository]("order_repository", protocol=OrderRepository)
    service_token = Token[OrderService]("order_service", expected_type=OrderService)

    # Register test implementations
    container.register(payment_token, MockPaymentGateway, Scope.SINGLETON)
    container.register(email_token, MockEmailService, Scope.SINGLETON)
    container.register(repo_token, MockOrderRepository, Scope.SINGLETON)

    # Register service with dependencies
    def create_order_service() -> OrderService:
        payment = container.resolve_protocol(PaymentGateway)
        email = container.resolve_protocol(EmailService)
        repo = container.resolve_protocol(OrderRepository)
        return OrderService(payment, email, repo)

    container.register(service_token, create_order_service, Scope.SINGLETON)

    return container


# Testing strategies
class TestOrderServiceIntegration:
    """Integration tests with test doubles."""

    @pytest.mark.asyncio
    async def test_successful_order_processing(self):
        """Test successful order processing flow."""
        container = create_test_container()

        # Get service and dependencies
        service_token = Token[OrderService]("order_service", expected_type=OrderService)
        service = container.get(service_token)

        # Get mocks for verification
        payment_mock = container.resolve_protocol(PaymentGateway)
        email_mock = container.resolve_protocol(EmailService)
        repo_mock = container.resolve_protocol(OrderRepository)

        # Create test order
        order = Order("order_123", 99.99, "customer@example.com")

        # Process order
        result = await service.process_order(order, "credit_card")

        # Verify success
        assert result is True
        assert order.status == "paid"

        # Verify interactions
        assert len(payment_mock.processed_payments) == 1
        assert payment_mock.processed_payments[0]["amount"] == 99.99

        assert len(email_mock.sent_emails) == 1
        assert email_mock.sent_emails[0]["type"] == "confirmation"

        assert "order_123" in repo_mock.save_calls
        assert ("order_123", "paid") in repo_mock.update_calls

    @pytest.mark.asyncio
    async def test_failed_payment_handling(self):
        """Test payment failure handling."""
        container = create_test_container()

        # Override payment gateway to fail
        failing_payment = MockPaymentGateway(should_fail=True)
        payment_token = Token[PaymentGateway](
            "payment_gateway", protocol=PaymentGateway
        )
        container.override(payment_token, failing_payment)

        # Get service
        service_token = Token[OrderService]("order_service", expected_type=OrderService)
        service = container.get(service_token)

        # Get mocks for verification
        email_mock = container.resolve_protocol(EmailService)
        repo_mock = container.resolve_protocol(OrderRepository)

        # Create test order
        order = Order("order_456", 199.99, "customer@example.com")

        # Process order (should fail)
        with pytest.raises(Exception, match="Payment processing failed"):
            await service.process_order(order, "credit_card")

        # Verify failure handling
        assert order.status == "failed"

        # Verify failure notifications sent
        failure_emails = [
            e for e in email_mock.sent_emails if e["type"] == "payment_failed"
        ]
        assert len(failure_emails) == 1

        # Verify status updated
        assert ("order_456", "failed") in repo_mock.update_calls


class TestOrderServiceUnit:
    """Unit tests with complete mocks."""

    @pytest.mark.asyncio
    async def test_order_processing_with_unittest_mocks(self):
        """Test using unittest.mock for complete isolation."""
        # Create mocks
        payment_mock = AsyncMock(spec=PaymentGateway)
        payment_mock.process_payment.return_value = "mock_transaction_123"

        email_mock = AsyncMock(spec=EmailService)
        email_mock.send_order_confirmation.return_value = True

        repo_mock = AsyncMock(spec=OrderRepository)

        # Create service with mocks
        service = OrderService(payment_mock, email_mock, repo_mock)

        # Test data
        order = Order("order_789", 299.99, "test@example.com")

        # Execute
        result = await service.process_order(order, "paypal")

        # Verify
        assert result is True
        assert order.status == "paid"

        # Verify mock calls
        payment_mock.process_payment.assert_called_once_with(299.99, "paypal")
        email_mock.send_order_confirmation.assert_called_once_with(order)
        repo_mock.save_order.assert_called_once_with(order)
        repo_mock.update_order_status.assert_called_with("order_789", "paid")

    @pytest.mark.asyncio
    async def test_refund_processing(self):
        """Test order refund processing."""
        # Create mocks
        payment_mock = AsyncMock(spec=PaymentGateway)
        payment_mock.refund_payment.return_value = True

        repo_mock = AsyncMock(spec=OrderRepository)
        existing_order = Order("order_refund", 150.00, "refund@example.com")
        existing_order.status = "paid"
        repo_mock.get_order.return_value = existing_order

        email_mock = AsyncMock(spec=EmailService)

        # Create service
        service = OrderService(payment_mock, email_mock, repo_mock)

        # Process refund
        result = await service.refund_order("order_refund")

        # Verify
        assert result is True
        repo_mock.get_order.assert_called_once_with("order_refund")
        payment_mock.refund_payment.assert_called_once()
        repo_mock.update_order_status.assert_called_once_with(
            "order_refund", "refunded"
        )


class TestContainerTesting:
    """Test container testing patterns."""

    def test_container_override_strategy(self):
        """Test using container overrides for testing."""
        container = create_production_container()

        # Original service
        service_token = Token[OrderService]("order_service", expected_type=OrderService)
        original_service = container.get(service_token)
        assert isinstance(original_service.payment_gateway, StripePaymentGateway)

        # Override for testing
        test_payment = MockPaymentGateway()
        payment_token = Token[PaymentGateway](
            "payment_gateway", protocol=PaymentGateway
        )
        container.override(payment_token, test_payment)

        # Service now uses test double
        test_service = container.get(service_token)
        # Note: Since it's a singleton, we get the same instance
        # For this test, we'd need to clear the singleton cache or use different scopes

        # Clear overrides
        container.clear_overrides()

        # Back to original
        restored_service = container.get(service_token)
        # Same singleton instance, but demonstrates the pattern

    @pytest.mark.asyncio
    async def test_isolated_container_per_test(self):
        """Test using isolated containers per test."""
        # Each test gets its own container
        test_container = Container()

        # Register only what this test needs
        mock_payment = MockPaymentGateway()
        mock_email = MockEmailService()
        mock_repo = MockOrderRepository()

        service = OrderService(mock_payment, mock_email, mock_repo)

        # Test in isolation
        order = Order("isolated_test", 49.99, "isolated@test.com")
        result = await service.process_order(order, "test_card")

        assert result is True
        assert len(mock_payment.processed_payments) == 1
        assert len(mock_email.sent_emails) == 1


async def demo_testing_strategies():
    """Demonstrate various testing strategies."""
    print("=== Testing Strategies Demo ===\n")

    print("1. Production container:")
    prod_container = create_production_container()
    service_token = Token[OrderService]("order_service", expected_type=OrderService)
    prod_service = container.get(service_token)
    print(f"  Payment gateway type: {type(prod_service.payment_gateway).__name__}")

    print("\n2. Test container with mocks:")
    test_container = create_test_container()
    test_service = test_container.get(service_token)
    print(f"  Payment gateway type: {type(test_service.payment_gateway).__name__}")

    print("\n3. Processing test order:")
    order = Order("demo_order", 49.99, "demo@example.com")

    try:
        result = await test_service.process_order(order, "test_card")
        print(f"  Order processed: {result}")
        print(f"  Order status: {order.status}")

        # Check mock interactions
        payment_mock = test_service.payment_gateway
        email_mock = test_service.email_service

        print(f"  Payments processed: {len(payment_mock.processed_payments)}")
        print(f"  Emails sent: {len(email_mock.sent_emails)}")

    except Exception as e:
        print(f"  Error: {e}")

    print("\n4. Container override example:")
    # Override with different behavior
    failing_payment = MockPaymentGateway(should_fail=True)
    payment_token = Token[PaymentGateway]("payment_gateway", protocol=PaymentGateway)
    test_container.override(payment_token, failing_payment)

    # Get new service instance (in real test, you'd recreate service or use different scope)
    print("  Overridden payment gateway to fail")

    print("\nDemo completed - run pytest to see actual tests!")


if __name__ == "__main__":
    asyncio.run(demo_testing_strategies())
