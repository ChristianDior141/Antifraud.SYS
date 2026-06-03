from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime
from app.models.transaction import TransactionType, TransactionStatus


class TransactionCreate(BaseModel):
    type: TransactionType
    amount: float
    currency: str = "USD"
    counterparty_name: Optional[str] = None
    counterparty_account: Optional[str] = None
    counterparty_country: Optional[str] = None
    counterparty_bank: Optional[str] = None
    description: Optional[str] = None
    transaction_date: datetime

    @validator("amount")
    def amount_positive(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v


class TransactionResponse(BaseModel):
    id: int
    client_id: int
    transaction_ref: str
    type: TransactionType
    status: TransactionStatus
    amount: float
    currency: str
    counterparty_name: Optional[str] = None
    counterparty_country: Optional[str] = None
    is_flagged: bool
    flag_reason: Optional[str] = None
    risk_score: float
    transaction_date: datetime
    created_at: datetime

    class Config:
        from_attributes = True
