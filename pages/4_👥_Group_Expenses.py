import datetime as dt
import pandas as pd
import streamlit as st

import db
from utils import session as ss


ss.init_app()
ss.auth_sidebar()
ss.require_login()

st.title("👥 Group Expenses")

# Split view into tabs
tab_view, tab_add, tab_settle = st.tabs(["View Expenses", "Add Expense", "Settle Up"])

with tab_add:
    st.subheader("Add Group Expense")
    with st.form("add_group_expense"):
        title = st.text_input("Title", placeholder="Dinner, Trip, etc.")
        amount = st.number_input("Total Amount (₹)", min_value=0.0, step=100.0)
        category = st.text_input("Category", placeholder="Food, Travel, etc.")
        date = st.date_input("Date", value=dt.date.today())
        description = st.text_area("Description")
        
        # Get all users for splitting
        all_users = db.get_all_users()
        selected_users = st.multiselect(
            "Split With",
            options=[(u["id"], u["name"]) for u in all_users if u["id"] != st.session_state.auth["user_id"]],
            format_func=lambda x: x[1]
        )
        
        split_type = st.radio("Split Type", ["Equal", "Custom"])
        shares = []
        
        if split_type == "Equal" and selected_users:
            share_amount = amount / (len(selected_users) + 1)  # +1 for current user
            for user_id, _ in selected_users:
                shares.append({"user_id": user_id, "amount": share_amount})
            shares.append({"user_id": st.session_state.auth["user_id"], "amount": share_amount})
            st.info(f"Each person's share: ₹{share_amount:,.2f}")
        
        elif split_type == "Custom" and selected_users:
            st.write("Enter share amounts:")
            total = 0
            for user_id, name in selected_users:
                share = st.number_input(f"Amount for {name}", 
                                     min_value=0.0, 
                                     max_value=amount,
                                     step=10.0)
                if share > 0:
                    shares.append({"user_id": user_id, "amount": share})
                    total += share
            
            remaining = amount - total
            if remaining > 0:
                shares.append({"user_id": st.session_state.auth["user_id"], 
                             "amount": remaining})
            st.write(f"Your share: ₹{remaining:,.2f}")
        
        if st.form_submit_button("Add Group Expense"):
            if not title or amount <= 0 or not selected_users:
                st.error("Please fill in all required fields.")
            elif sum(s["amount"] for s in shares) != amount:
                st.error("Share amounts must equal total amount.")
            else:
                db.add_group_expense(
                    title=title,
                    amount=amount,
                    payer_id=st.session_state.auth["user_id"],
                    category=category,
                    date=date,
                    description=description,
                    shares=shares
                )
                st.success("Group expense added successfully!")
                st.rerun()

with tab_view:
    expenses = db.get_group_expenses(st.session_state.auth["user_id"])
    if not expenses:
        st.info("No group expenses found.")
    else:
        # Convert to DataFrame and handle date
        df = pd.DataFrame(expenses)
        df["date"] = pd.to_datetime(df["date"]).dt.date
        
        st.subheader("Your Group Expenses")
        
        # Calculate metrics safely
        total_owed = 0
        total_paid = 0
        
        # Calculate amount owed (where you're not the payer and haven't settled)
        for exp in expenses:
            if exp["payer_id"] != st.session_state.auth["user_id"]:
                if not exp.get("is_settled", False):
                    total_owed += exp["share_amount"]
            else:
                total_paid += exp["amount"]
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("You Owe", f"₹ {total_owed:,.2f}")
        with col2:
            st.metric("You Paid", f"₹ {total_paid:,.2f}")
        with col3:
            net = total_paid - total_owed
            st.metric("Net Balance", f"₹ {net:,.2f}")
        
        # Display expenses
        st.write("#### Recent Expenses")
        for exp in expenses:
            with st.expander(f"{exp['title']} - ₹{exp['amount']:,.2f} ({exp['date']})"):
                st.write(f"**Category:** {exp['category']}")
                st.write(f"**Paid by:** {exp['payer_name']}")
                st.write(f"**Your share:** ₹{exp['share_amount']:,.2f}")
                st.write(f"**Status:** {'Settled' if exp['is_settled'] else 'Pending'}")
                if exp['description']:
                    st.write(f"**Description:** {exp['description']}")

with tab_settle:
    st.subheader("Settle Up")
    # Filter expenses where you're not the payer and haven't settled
    unsettled = [
        e for e in expenses 
        if e["payer_id"] != st.session_state.auth["user_id"] 
        and not e.get("is_settled", False)
    ]
    
    if not unsettled:
        st.success("You're all settled up! No pending payments.")
    else:
        st.write("Select expenses to settle:")
        for exp in unsettled:
            with st.expander(f"{exp['title']} - ₹{exp['share_amount']:,.2f}", expanded=True):
                st.write(f"**Amount:** ₹{exp['share_amount']:,.2f}")
                st.write(f"**Paid by:** {exp['payer_name']}")
                st.write(f"**Date:** {exp['date']}")
                if exp.get('description'):
                    st.write(f"**Description:** {exp['description']}")
                if st.button(f"Mark as Settled", key=f"settle_{exp['id']}"):
                    db.settle_expense_share(exp["id"], st.session_state.auth["user_id"])
                    st.success(f"Marked {exp['title']} as settled!")
                    st.rerun()
