from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MachineType = Literal["WASHER", "DRYER"]
MachineStatus = Literal["AVAILABLE", "RESERVED", "IN_USE", "OUT_OF_SERVICE"]


class Machine(BaseModel):
    id: int
    type: MachineType
    capacity: int
    price: float
    status: MachineStatus
    active: bool


class MachineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: MachineType
    capacity: int = Field(gt=0, le=100, description="Capacity in kg")
    price: Decimal = Field(ge=0, le=1000, max_digits=6, decimal_places=2)
    status: MachineStatus = "AVAILABLE"
    active: bool = True


class MachineUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: MachineType | None = None
    capacity: int | None = Field(default=None, gt=0, le=100)
    price: Decimal | None = Field(default=None, ge=0, le=1000, max_digits=6, decimal_places=2)
    active: bool | None = None

    @model_validator(mode="after")
    def at_least_one_field(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")
        return self


class MachineStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: MachineStatus


class BusySlot(BaseModel):
    start_time: datetime
    end_time: datetime


class MachineAvailability(BaseModel):
    machine_id: int
    from_time: datetime
    to_time: datetime
    busy: list[BusySlot]


def to_db_values(model: BaseModel, only_sent: bool = True) -> dict:
    """Model values converted to JSON-friendly types. With only_sent, fields the
    client did not send are left out (so an update only changes those)."""
    values = model.model_dump(exclude_unset=only_sent)
    if isinstance(values.get("price"), Decimal):
        values["price"] = float(values["price"])
    return values
