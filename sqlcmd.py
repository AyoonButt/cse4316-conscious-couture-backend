from sqlalchemy import create_engine, text
e = create_engine("sqlite:///clothing_swap.db")
with e.begin() as conn:
    conn.execute(text("DELETE FROM payments WHERE transaction_id = :tid"), {"tid": 123})
print("Deleted successfully")
