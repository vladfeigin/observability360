import os
import streamlit as st
import requests
import pandas as pd

# Use environment variable for product service URL, with a default port if needed.
BASE_URL = os.environ.get('PRODUCT_SERVICE_URL', 'http://127.0.0.1:5001')

def run_product_ui():
    st.header("Product Service")
    action = st.selectbox("Select Action", ["Select Action...", "Add Product", "List Products"], index=0)
    
    if action == "Add Product":
        with st.form("add_product_form"):
            product_id = st.text_input("Product ID")
            name = st.text_input("Name")
            description = st.text_area("Description", help="Optional description")
            number_items_in_stock = st.number_input("Number of Items in Stock", min_value=0, step=1)
            price = st.number_input("Price", min_value=0.0, format="%.2f")
            submitted = st.form_submit_button("Add Product")
            if submitted:
                payload = {
                    "productId": product_id,
                    "name": name,
                    "description": description,
                    "numberItemsInStock": number_items_in_stock,
                    "price": price
                }
                response = requests.post(f"{BASE_URL}/products", json=payload)
                if response.status_code == 201:
                    st.success("Product added successfully!")
                else:
                    st.error("Error adding product: " + response.text)

    elif action == "List Products":
        #if st.button("Refresh Product List"):
            response = requests.get(f"{BASE_URL}/products")
            if response.status_code == 200:
                products = response.json()
                if products:
                    df = pd.DataFrame(products, columns=['productId', 'name', 'description', 'numberItemsInStock', 'price'])
                    st.table(df)
                else:
                    st.info("No products found.")
            else:
                st.error("Error fetching products: " + response.text)