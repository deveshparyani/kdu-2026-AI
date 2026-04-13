from typing import Optional

from pydantic import BaseModel


class TransactionHistorySchema(BaseModel):
    count: int
    transactions: list[dict]
    message: str


class StockPriceResponseSchema(BaseModel):
    stock: str
    current_price: Optional[float] = None
    currency: str
    message: str
