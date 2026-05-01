from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models import AccountStatus, AccountType


class AccountCreate(BaseModel):
    customer_id: int
    customer_name: Optional[str] = None
    account_number: str
    account_type: AccountType = AccountType.SAVINGS
    balance: Decimal = Decimal("0.00")
    currency: str = "INR"
    status: AccountStatus = AccountStatus.ACTIVE


class AccountUpdate(BaseModel):
    customer_name: Optional[str] = None
    account_type: Optional[AccountType] = None
    currency: Optional[str] = None


class AccountStatusUpdate(BaseModel):
    status: AccountStatus


class MoneyMovement(BaseModel):
    amount: Decimal
    reference: Optional[str] = None


class BalanceOut(BaseModel):
    account_id: int
    balance: Decimal
    currency: str
    status: AccountStatus


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_id: int
    customer_id: int
    customer_name: str
    account_number: str
    account_type: AccountType
    balance: Decimal
    currency: str
    status: AccountStatus
    created_at: datetime
