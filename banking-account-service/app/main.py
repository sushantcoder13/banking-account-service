from datetime import datetime

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import Dict, List

from app.config import settings
from app.database import Base, engine, get_db
from app.events import publish_event
from app.models import Account, AccountStatus, AccountType
from app.observability import ObservabilityMiddleware, metrics_response
from app.schemas import AccountCreate, AccountOut, AccountStatusUpdate, AccountUpdate, BalanceOut, MoneyMovement

app = FastAPI(title="Banking Account Service", version="0.1.0")
app.add_middleware(ObservabilityMiddleware, service_name="account-service")


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "account-service"}


@app.get("/metrics")
def metrics():
    return metrics_response()


@app.post("/accounts", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(payload: AccountCreate, db: Session = Depends(get_db)):
    account_data = payload.model_dump()
    if not account_data.get("customer_name"):
        account_data["customer_name"] = _fetch_customer_name(payload.customer_id)
    account = Account(**account_data)
    db.add(account)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Account number already exists")
    db.refresh(account)
    return account


def _fetch_customer_name(customer_id: int) -> str:
    try:
        response = httpx.get(f"{settings.customer_service_url}/customers/{customer_id}", timeout=3.0)
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Customer Service is unavailable")
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Customer not found")
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail="Customer Service request failed")
    return response.json()["name"]


@app.get("/accounts", response_model=List[AccountOut])
def list_accounts(db: Session = Depends(get_db)):
    return db.query(Account).order_by(Account.account_id).all()


@app.get("/accounts/{account_id}", response_model=AccountOut)
def get_account(account_id: int, db: Session = Depends(get_db)):
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@app.get("/accounts/customer/{customer_id}", response_model=List[AccountOut])
def get_accounts_by_customer(customer_id: int, db: Session = Depends(get_db)):
    return db.query(Account).filter(Account.customer_id == customer_id).order_by(Account.account_id).all()


@app.get("/accounts/{account_id}/balance", response_model=BalanceOut)
def get_balance(account_id: int, db: Session = Depends(get_db)):
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return BalanceOut(account_id=account.account_id, balance=account.balance, currency=account.currency, status=account.status)


def _get_active_account(account_id: int, db: Session) -> Account:
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if account.status != AccountStatus.ACTIVE:
        raise HTTPException(status_code=400, detail=f"Transactions are not allowed on {account.status.value} accounts")
    return account


@app.post("/accounts/{account_id}/credit", response_model=AccountOut)
def credit_account(account_id: int, payload: MoneyMovement, db: Session = Depends(get_db)):
    account = _get_active_account(account_id, db)
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")
    account.balance = account.balance + payload.amount
    db.commit()
    db.refresh(account)
    return account


@app.post("/accounts/{account_id}/debit", response_model=AccountOut)
def debit_account(account_id: int, payload: MoneyMovement, db: Session = Depends(get_db)):
    account = _get_active_account(account_id, db)
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")
    if account.account_type == AccountType.BASIC and account.balance < payload.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance: overdraft is not allowed for BASIC accounts")
    if account.balance < payload.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    account.balance = account.balance - payload.amount
    db.commit()
    db.refresh(account)
    return account


@app.put("/accounts/{account_id}", response_model=AccountOut)
def update_account(account_id: int, payload: AccountUpdate, db: Session = Depends(get_db)):
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(account, key, value)
    db.commit()
    db.refresh(account)
    return account


@app.patch("/accounts/{account_id}/status", response_model=AccountOut)
def update_account_status(account_id: int, payload: AccountStatusUpdate, db: Session = Depends(get_db)):
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    old_status = account.status
    account.status = payload.status
    db.commit()
    db.refresh(account)
    publish_event("account.status_changed", {
        "event_type": "AccountStatusChanged",
        "account_id": account.account_id,
        "customer_id": account.customer_id,
        "customer_name": account.customer_name,
        "old_status": old_status.value,
        "new_status": account.status.value,
        "created_at": datetime.utcnow().isoformat(),
    })
    return account


@app.post("/accounts/{account_id}/close", response_model=AccountOut)
def close_account(account_id: int, db: Session = Depends(get_db)):
    return update_account_status(account_id, AccountStatusUpdate(status=AccountStatus.CLOSED), db)


@app.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    db.delete(account)
    db.commit()
    return None
