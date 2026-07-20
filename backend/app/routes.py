from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .models import Account, Transaction
from .redis_client import redis_client
from .schema import AccountCreate, AccountOut, CreditRequest, DebitRequest, TransactionOut
from .tasks import process_batch

TX_QUEUE_KEY = "tx_queue"
router = APIRouter()


@router.post("/accounts", status_code=201, response_model=AccountOut)
def create_account(body: AccountCreate, db: Session = Depends(get_db)):
    account = Account(owner_name=body.owner_name, balance=body.initial_balance)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/accounts/{account_id}", response_model=AccountOut)
def get_account(account_id: int, db: Session = Depends(get_db)):
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    return account


@router.get("/accounts", response_model=list[AccountOut])
def list_accounts(db: Session = Depends(get_db)):
    return db.query(Account).all()


@router.post("/credit", status_code=202)
def credit(body: CreditRequest, db: Session = Depends(get_db)):
    if not db.get(Account, body.account_id):
        raise HTTPException(404, "Account not found")
    txn = Transaction(account_id=body.account_id, type="credit", amount=body.amount, status="pending")
    db.add(txn)
    db.commit()
    db.refresh(txn)
    redis_client.rpush(TX_QUEUE_KEY, str(txn.id))
    process_batch.delay()
    return {"transaction_id": txn.id, "status": "pending"}


@router.post("/debit", status_code=202)
def debit(body: DebitRequest, db: Session = Depends(get_db)):
    if not db.get(Account, body.account_id):
        raise HTTPException(404, "Account not found")
    txn = Transaction(account_id=body.account_id, type="debit", amount=body.amount, status="pending")
    db.add(txn)
    db.commit()
    db.refresh(txn)
    redis_client.rpush(TX_QUEUE_KEY, str(txn.id))
    process_batch.delay()
    return {"transaction_id": txn.id, "status": "pending"}


@router.get("/transactions/{transaction_id}", response_model=TransactionOut)
def get_transaction(transaction_id: int, db: Session = Depends(get_db)):
    txn = db.get(Transaction, transaction_id)
    if not txn:
        raise HTTPException(404, "Transaction not found")
    return txn
