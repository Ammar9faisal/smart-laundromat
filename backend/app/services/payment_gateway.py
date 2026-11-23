"""Simulated payment gateway.

No real card is ever charged. The outcome is decided by the test payment
method the customer picks, modelled on Stripe's test payment methods so the
simulator can later be replaced by Stripe test mode behind the same interface.
"""

from dataclasses import dataclass
from uuid import uuid4

# payment method -> failure reason (None means the charge succeeds)
TEST_PAYMENT_METHODS: dict[str, str | None] = {
    "pm_card_visa": None,
    "pm_card_mastercard": None,
    "pm_card_chargeDeclined": "Your card was declined.",
    "pm_card_chargeDeclinedInsufficientFunds": "Your card has insufficient funds.",
}


@dataclass(frozen=True)
class ChargeResult:
    succeeded: bool
    provider_ref: str
    failure_reason: str | None = None


class SimulatedPaymentGateway:
    def charge(self, amount: float, currency: str, payment_method: str) -> ChargeResult:
        if payment_method not in TEST_PAYMENT_METHODS:
            raise ValueError(f"Unsupported payment method: {payment_method}")
        if amount < 0:
            raise ValueError("Amount cannot be negative")

        failure_reason = TEST_PAYMENT_METHODS[payment_method]
        return ChargeResult(
            succeeded=failure_reason is None,
            provider_ref=f"sim_{uuid4().hex}",
            failure_reason=failure_reason,
        )


_gateway = SimulatedPaymentGateway()


def get_payment_gateway() -> SimulatedPaymentGateway:
    """FastAPI dependency, so tests (or a future Stripe gateway) can replace it."""
    return _gateway
