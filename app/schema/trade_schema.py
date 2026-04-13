from typing import Literal, Optional

from pydantic import BaseModel


class ProposedTradeSchema(BaseModel):
    action: Literal["buy", "sell"]
    stock: str
    quantity: int
    unit_price: float
    total_value: float
    currency: str


class TradeResultSchema(BaseModel):
    status: Literal["executed", "rejected", "invalid"]
    action: str
    stock: Optional[str] = None
    quantity: Optional[int] = None
    unit_price: Optional[float] = None
    total_value: Optional[float] = None
    message: str
