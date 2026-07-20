from pydantic import BaseModel


class AccountCreate(BaseModel):
    owner_name: str
    initial_balance: float = 0.0


class AccountOut(BaseModel):
    id: int
    owner_name: str
    balance: float

    class Config:
        from_attributes = True


class CreditRequest(BaseModel):
    account_id: int
    amount: float


class DebitRequest(BaseModel):
    account_id: int
    amount: float


class TransactionOut(BaseModel):
    id: int
    account_id: int
    type: str
    amount: float
    status: str
    reason: str | None = None

    class Config:
        from_attributes = True
