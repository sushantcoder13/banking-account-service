import csv
from decimal import Decimal
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database import Base, SessionLocal, engine
from app.models import Account, AccountStatus, AccountType


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    csv_path = Path(__file__).resolve().parents[1] / "seed" / "accounts.csv"
    db = SessionLocal()
    try:
        with csv_path.open() as handle:
            for row in csv.DictReader(handle):
                account = db.get(Account, int(row["account_id"]))
                if not account:
                    account = Account(account_id=int(row["account_id"]))
                    db.add(account)
                account.customer_id = int(row["customer_id"])
                account.customer_name = row["customer_name"]
                account.account_number = row["account_number"]
                account.account_type = AccountType(row["account_type"])
                account.balance = Decimal(row["balance"])
                account.currency = row["currency"]
                account.status = AccountStatus(row["status"])
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    print("Seeded accounts")
