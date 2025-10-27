from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class OrderStatus(BaseModel):
    status: str = Field(..., pattern="^(pending|processing|completed|cancelled)$")

class Order(BaseModel):
    customer_id: str
    amount: float = Field(..., gt=0)
    items: Optional[List[dict]] = []

class HealthCheck(BaseModel):
    status: str
    database: str
    cache: str
    uptime: float