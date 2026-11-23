from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.schemas.machines import MachineStatus, MachineType

ReservationStatus = Literal[
    "PENDING_PAYMENT", "CONFIRMED", "IN_PROGRESS", "COMPLETED", "CANCELLED", "EXPIRED"
]

# Business rules for a single booking.
MIN_DURATION = timedelta(minutes=15)
MAX_DURATION = timedelta(hours=3)
MAX_DAYS_AHEAD = 30


class ReservationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    machine_id: int = Field(gt=0)
    start_time: AwareDatetime = Field(description="ISO 8601 with a time zone offset")
    end_time: AwareDatetime = Field(description="ISO 8601 with a time zone offset")

    @model_validator(mode="after")
    def check_times(self):
        duration = self.end_time - self.start_time

        if duration <= timedelta(0):
            raise ValueError("end_time must be after start_time")
        if duration < MIN_DURATION:
            raise ValueError("A reservation must be at least 15 minutes long")
        if duration > MAX_DURATION:
            raise ValueError("A reservation cannot be longer than 3 hours")

        now = datetime.now(timezone.utc)
        if self.start_time <= now:
            raise ValueError("Reservations cannot start in the past")
        if self.start_time > now + timedelta(days=MAX_DAYS_AHEAD):
            raise ValueError(f"Reservations can be made at most {MAX_DAYS_AHEAD} days ahead")

        return self


class ReservationMachine(BaseModel):
    id: int
    type: MachineType
    capacity: int
    price: float
    status: MachineStatus


class Reservation(BaseModel):
    id: int
    user_id: str
    machine_id: int
    start_time: datetime
    end_time: datetime
    status: ReservationStatus
    price: float
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    machine: ReservationMachine | None = None
