from pydantic import BaseModel


class MachineCounts(BaseModel):
    total: int
    active: int
    available: int
    out_of_service: int


class PaymentTotals(BaseModel):
    succeeded: int
    failed: int
    refunded: int
    revenue: float


class AdminSummary(BaseModel):
    machines: MachineCounts
    reservations_by_status: dict[str, int]
    payments: PaymentTotals
