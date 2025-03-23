import os
import streamlit as st
import requests
import pandas as pd
from online_store.otel.otel import configure_telemetry, trace_span


SERVICE_VERSION = "1.0.0"
instruments = configure_telemetry(None, "Order UI", SERVICE_VERSION)

# Get instruments and logger
tracer = instruments["tracer"]
logger = instruments["logger"]

# Order Service URL (default to port 5003)
ORDER_SERVICE_URL = os.environ.get("ORDER_SERVICE_URL", "http://127.0.0.1:5003")
# [NEW] User Service URL (default to port 5000)
USER_SERVICE_URL = os.environ.get("USER_SERVICE_URL", "http://127.0.0.1:5000")

@trace_span("run_order_ui", tracer)
def run_order_ui():
    logger.info("Order UI - run_order_ui.")
    st.header("Order Service")
    st.subheader("List My Orders", divider="blue")

    # [NEW] Fetch users from the User Service
    try:
        user_response = requests.get(f"{USER_SERVICE_URL}/users", timeout=10)
        if user_response.status_code != 200:
            st.error("Error fetching users: " + user_response.text)
            logger.error(f"Error fetching users: {user_response.text}")
            return
        users_list = user_response.json()
        if not users_list:
            st.error("No users found.")
            logger.info("No users found.")
            return
        # Build options like "12: John Doe"
        user_options = [f"{u['id']}: {u['firstName']} {u['lastName']}" for u in users_list]
    except Exception as e:
        st.error("Error retrieving users: " + str(e))
        logger.error(f"Error retrieving users: {e}")
        return

    # [NEW] Use a combo box for user selection instead of text input
    selected_user = st.selectbox("Select User", user_options)
    # Extract user id from the selected string (assumes format "id: Name")
    user_id = selected_user.split(":")[0].strip()

    if st.button("List My Orders"):
        if not user_id:
            st.error("Please select a valid User ID.")
            logger.error("User ID is empty.")
            return

        logger.info(f"Calling Order Service for user ID: {user_id}")
        # Call the Order service to list orders for this user.
        response = requests.get(f"{ORDER_SERVICE_URL}/orders", params={"userId": user_id}, timeout=10)
        if response.status_code != 200:
            logger.error(f"Error fetching orders for user ID {user_id}: {response.text}")
            st.error("Error fetching orders: " + response.text)
            return

        orders = response.json()
        if not orders:
            st.info("No orders found for this user.")
            logger.info(f"No orders found for user ID {user_id}.")
            return

        # Instead of combining product details into one cell,
        # iterate over orders and display each order in an expander.
        for order in orders:
            expander_title = f"Order ID: {order.get('orderId')} | Date: {order.get('orderDate')}"
            with st.expander(expander_title):
                products = order.get("products", [])
                if products:
                    df_products = pd.DataFrame(products)
                    st.table(df_products)
                else:
                    st.write("No products in this order.")

if __name__ == "__main__":
    run_order_ui()