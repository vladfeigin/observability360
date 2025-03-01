import os
import streamlit as st
import requests
import pandas as pd

# Order Service URL (default to port 5003)
ORDER_SERVICE_URL = os.environ.get("ORDER_SERVICE_URL", "http://127.0.0.1:5003")

def run_order_ui():
    st.title("Order Service")
    st.subheader("List My Orders")

    user_id = st.text_input("User ID", help="Enter your User ID")
    
    if st.button("List My Orders"):
        if not user_id:
            st.error("Please enter a valid User ID.")
            return

        # Call the Order service to list orders for this user.
        response = requests.get(f"{ORDER_SERVICE_URL}/orders", params={"userId": user_id})
        if response.status_code != 200:
            st.error("Error fetching orders: " + response.text)
            return

        orders = response.json()
        if not orders:
            st.info("No orders found for this user.")
            return

        # Instead of combining product details into one cell,
        # iterate over orders and display each order in an expander.
        for order in orders:
            # Display order header in the expander title.
            expander_title = f"Order ID: {order.get('orderId')} | Date: {order.get('orderDate')}"
            with st.expander(expander_title):
                products = order.get("products", [])
                if products:
                    # Create a DataFrame for the product list.
                    df_products = pd.DataFrame(products)
                    st.table(df_products)
                else:
                    st.write("No products in this order.")

if __name__ == "__main__":
    run_order_ui()