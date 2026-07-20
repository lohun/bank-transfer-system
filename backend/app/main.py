from fastapi import FastAPI

from .database import Base, engine
from .routes import router
from sqlalchemy import text

Base.metadata.create_all(bind=engine)

with engine.connect() as conn:
    conn.execute(text("""
        CREATE OR REPLACE PROCEDURE process_batch_transactions(transaction_ids INT[])
        LANGUAGE plpgsql
        AS $$
        BEGIN
            -- Pre-lock accounts in sorted order to avoid deadlocks across multiple workers
            PERFORM id FROM public.accounts 
            WHERE id IN (
                SELECT DISTINCT account_id FROM public.transactions WHERE id = ANY(transaction_ids)
            )
            ORDER BY id FOR UPDATE;

            DROP TABLE IF EXISTS credit_transactions;
            DROP TABLE IF EXISTS debit_transactions;

            CREATE TEMP TABLE credit_transactions AS 
            SELECT t."account_id", SUM(t."amount") AS amount 
            FROM public.transactions t 
            WHERE t."id" = ANY(transaction_ids) AND t."type" = 'credit' AND t."status" = 'pending'
            GROUP BY t."account_id";

            CREATE TEMP TABLE debit_transactions AS 
            SELECT t."account_id", SUM(t."amount") AS amount 
            FROM public.transactions t JOIN public.accounts a ON t.account_id = a.id 
            WHERE t."id" = ANY(transaction_ids) AND t."type" = 'debit' AND t."status" = 'pending' AND t."amount" <= a."balance" 
            GROUP BY t."account_id";

            UPDATE public.transactions as t
            SET status = CASE
                WHEN t."type" = 'credit' THEN 'completed'
                WHEN t."type" = 'debit' AND t."amount" <= a."balance" THEN 'completed'
                ELSE 'failed'
            END,
            reason = CASE
                WHEN t."type" = 'debit' AND a.balance < t."amount" THEN 'Insufficient Funds'
                ELSE t.reason
            END
            FROM public.accounts a 
            WHERE t.account_id = a.id AND t."id" = ANY(transaction_ids) AND t."status" = 'pending';

            UPDATE public.accounts as a
            SET balance = a."balance" + c."amount"
            FROM credit_transactions c
            WHERE a.id = c.account_id;

            UPDATE public.accounts as a
            SET balance = a."balance" - d."amount"
            FROM debit_transactions d
            WHERE a.id = d.account_id;

            DROP TABLE credit_transactions;
            DROP TABLE debit_transactions;
        END;
        $$;
    """))
    conn.commit()

app = FastAPI(title="Bank Transfer System")
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
