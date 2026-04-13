from pydantic import BaseModel, Field
from typing import Literal, Optional

class ParseInputSchema(BaseModel):
    intent: Optional[Literal["buy_stock", "sell_stock", "get_portfolio", "get_transactions", "get_stock_price", "unknown"]] = None
    stock: Optional[str] = None
    quantity: Optional[int] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
