from pydantic import BaseModel


class HoldingDetails(BaseModel):
    stock: str
    quantity: int
    current_price: float
    total_value: float


class PortfolioDetailsSchema(BaseModel):
    currency: str
    total_portfolio_value: float
    holdings: list[HoldingDetails]
    message: str
