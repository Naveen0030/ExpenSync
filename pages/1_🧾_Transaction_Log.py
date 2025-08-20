import datetime as dt
import streamlit as st

import db
from utils import session as ss


ss.init_app()
ss.auth_sidebar()
ss.require_login()

st.title("🧾 Log Transactions")

# Current balance across all time
all_rows = db.list_transactions(
    user_id=st.session_state.auth["user_id"],
    start_date=dt.date(1970, 1, 1),
    end_date=dt.date.today(),
)
income_total = sum(r["amount"] for r in all_rows if r["type"] == "Income")
expense_total = sum(r["amount"] for r in all_rows if r["type"] == "Expense")
st.caption(f"Current Balance: ₹{income_total - expense_total:,.2f}")

with st.expander("Add New Expense", expanded=True):
    with st.form("add_expense"):
        c1, c2, c3 = st.columns(3)
        with c1:
            amount = st.number_input("Amount (₹)", min_value=0.0, step=100.0, format="%0.2f")
        with c2:
            date_val = st.date_input("Date", value=dt.date.today())
        with c3:
            category = st.text_input("Category", placeholder="Food, Rent, Travel…")
        description = st.text_area("Description", placeholder="Optional notes")
        payment_method = st.text_input("Payment Method", placeholder="UPI, Card, Cash")
        tags = st.text_input("Tags (comma-separated)")
        if st.form_submit_button("Save Expense"):
            if amount <= 0:
                st.error("Amount must be greater than 0.")
            else:
                db.add_transaction(
                    user_id=st.session_state.auth["user_id"],
                    amount=float(amount),
                    description=description.strip(),
                    category=category.strip() or "Uncategorized",
                    date=date_val,
                    txn_type="Expense",
                    payment_method=payment_method.strip() or None,
                    tags=tags.strip() or None,
                )
                st.success("Expense added.")
                st.rerun()

with st.expander("Add New Income", expanded=False):
    with st.form("add_income"):
        c1, c2 = st.columns(2)
        with c1:
            amount = st.number_input("Amount (₹)", min_value=0.0, step=500.0, format="%0.2f")
            source = st.text_input("Category / Source", placeholder="Salary, Bonus…")
        with c2:
            date_val = st.date_input("Date", value=dt.date.today(), key="income_date")
        description = st.text_area("Description", placeholder="Optional notes", key="income_desc")
        payment_method = st.text_input("Payment Method", placeholder="Bank, UPI", key="income_pay")
        if st.form_submit_button("Save Income"):
            if amount <= 0:
                st.error("Amount must be greater than 0.")
            else:
                db.add_transaction(
                    user_id=st.session_state.auth["user_id"],
                    amount=float(amount),
                    description=description.strip(),
                    category=source.strip() or "Income",
                    date=date_val,
                    txn_type="Income",
                    payment_method=payment_method.strip() or None,
                    tags=None,
                )
                st.success("Income added.")
                st.rerun()


