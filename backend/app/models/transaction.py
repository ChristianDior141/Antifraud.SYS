from sqlalchemy import Column, Integer, String, Enum, DateTime, Text, ForeignKey, Float, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class TransactionType(str, enum.Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    PAYMENT = "payment"
    EXCHANGE = "exchange"


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    FLAGGED = "flagged"
    BLOCKED = "blocked"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("client_profiles.id"), nullable=False)
    transaction_ref = Column(String(100), unique=True, nullable=False)

    type = Column(Enum(TransactionType), nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)

    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    counterparty_name = Column(String(255), nullable=True)
    counterparty_account = Column(String(100), nullable=True)
    counterparty_country = Column(String(100), nullable=True)
    counterparty_bank = Column(String(255), nullable=True)

    description = Column(Text, nullable=True)
    is_flagged = Column(Boolean, default=False)
    flag_reason = Column(Text, nullable=True)
    risk_score = Column(Float, default=0.0)

    ip_address = Column(String(45), nullable=True)
    device_id = Column(String(255), nullable=True)

    transaction_date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    client = relationship("ClientProfile", back_populates="transactions")
    aml_alerts = relationship("AMLAlert", back_populates="transaction")
