import datetime as dt
import pandas as pd
import plotly.express as px
import streamlit as st

import db
from utils import session as ss


ss.init_app()
ss.auth_sidebar()

st.title("Welcome 👋")
st.caption("A clean, resume-ready Expense Tracker with Streamlit + SQLite")

if not st.session_state.auth["logged_in"]:
    st.info("Use the sidebar to register or sign in. Once logged in, explore the pages: Transaction Log, View Transactions, and Reports.")
    st.stop()

filters = ss.render_filters()

rows = db.list_transactions(
    user_id=st.session_state.auth["user_id"],
    start_date=filters["start_date"],
    end_date=filters["end_date"],
    category=None if filters["category"] == "All" else filters["category"],
    txn_type=None if filters["txn_type"] == "All" else filters["txn_type"],
)
df = pd.DataFrame(rows)
if df.empty:
    st.info("No transactions for the selected period.")
else:
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["amount"] = df["amount"].astype(float)
    total_expense = df.loc[df["type"] == "Expense", "amount"].sum()
    total_income = df.loc[df["type"] == "Income", "amount"].sum()
    ss.show_kpis(total_expense, total_income)

    left, right = st.columns([2, 1])
    with left:
        daily = df.groupby(["date", "type"], as_index=False)["amount"].sum()
        fig_line = px.line(daily, x="date", y="amount", color="type", markers=True, title="Daily Trend")
        st.plotly_chart(fig_line, use_container_width=True)
    with right:
        cat = df[df["type"] == "Expense"].groupby("category", as_index=False)["amount"].sum()
        if not cat.empty:
            fig_pie = px.pie(cat, names="category", values="amount", hole=0.5, title="Expenses by Category")
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No expense data by category.")


