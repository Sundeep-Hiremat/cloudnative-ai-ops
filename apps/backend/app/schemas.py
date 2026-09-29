from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class OrderCreate(BaseModel):
    customer_name: str = Field(..., min_length=2, json_schema_extra={"example": "John Doe"})
    item_name: str = Field(..., min_length=2, json_schema_extra={"example": "Cloud Native Laptop"})
    quantity: int = Field(default=1, gt=0, json_schema_extra={"example": 2})
    total_price: float = Field(default=0.0, ge=0.0, json_schema_extra={"example": 1500.0})


class OrderUpdate(BaseModel):
    status: str = Field(..., json_schema_extra={"example": "COMPLETED"})  # PENDING, PROCESSING, COMPLETED, CANCELLED


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_name: str
    item_name: str
    quantity: int
    total_price: float
    status: str
    created_at: datetime
