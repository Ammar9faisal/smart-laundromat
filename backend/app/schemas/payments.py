from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PaymentStatus = Literal["PENDING", "SUCCEEDED", "FAILED", "REFUNDED"]

# Only test payment methods are accepted, so real card details can never be
# submitted. The names follow Stripe's test payment methods.
TestPaymentMethod = Literal[
    "pm_card_visa",
    "pm_card_mastercard",
    "pm_card_chargeDeclined",
    "pm_card_chargeDeclinedInsufficientFunds",
]


class PaymentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reservation_id: int = Field(gt=0)
    payment_method: TestPaymentMethod
    idempotency_key: str | None = Field(
        default=None,
        min_length=8,
        max_length=100,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Repeating a request with the same key returns the original payment",
    )


class Payment(BaseModel):
    id: int
    reservation_id: int
    user_id: str
    amount: float
    currency: str
    status: PaymentStatus
    provider: str
    provider_ref: str | None = None
    failure_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class PaymentFailed(BaseModel):
    detail: str
    payment: Payment
