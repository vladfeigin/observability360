import os
import streamlit as st
import requests
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

PRODUCT_SERVICE_URL = os.environ.get('PRODUCT_SERVICE_URL', 'http://127.0.0.1:5001')
CART_SERVICE_URL = os.environ.get('CART_SERVICE_URL', 'http://127.0.0.1:5002')

def run_product_ui():
    """ Product Service UI. 
    This UI allows users to add products and list products.
    It also allows users to add products to the cart.
    """
    
    st.header("Product Service")

    action = st.selectbox(
        "Select Action",
        ["Select Action...", "List Products", "Add Product"],
        index=0
    )

    # ------------------- ADD PRODUCT -------------------
    if action == "Add Product":
        st.subheader("Add a New Product")
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
                response = requests.post(f"{PRODUCT_SERVICE_URL}/products", json=payload)
                if response.status_code == 201:
                    st.success("Product added successfully!")
                else:
                    st.error("Error adding product: " + response.text)

    # ------------------- LIST PRODUCTS -------------------
    elif action == "List Products":
        st.subheader("List and Select Products")

        # Fetch products from the Product service
        response = requests.get(f"{PRODUCT_SERVICE_URL}/products", timeout=10)
        if response.status_code == 200:
            products = response.json()
            if products:
                df = pd.DataFrame(products, columns=[
                    'productId',
                    'name',
                    'description',
                    'numberItemsInStock',
                    'price'
                ])

                # Use AgGrid to display interactive table
                st.write("Select a row to add product to cart.")
                gb = GridOptionsBuilder.from_dataframe(df)
                gb.configure_selection(selection_mode="single", use_checkbox=True)
                grid_options = gb.build()

                grid_response = AgGrid(
                    df,
                    gridOptions=grid_options,
                    update_mode=GridUpdateMode.SELECTION_CHANGED,
                    theme='streamlit',
                    height=300
                )

                # Get selected rows
                selected_rows = grid_response.get("selected_rows")
                if selected_rows is None:
                    selected_rows = []
                elif isinstance(selected_rows, pd.DataFrame):
                    # Convert DF to list of dict if AgGrid returns a DF
                    selected_rows = selected_rows.to_dict('records')

                if len(selected_rows) > 0:
                    selected_product = selected_rows[0]
                    st.markdown(
                        f"**Selected Product**: `{selected_product['productId']}` "
                        f"- {selected_product['name']}"
                    )

                    # Show form to add selected product to cart
                    with st.form("add_to_cart_form"):
                        user_id = st.text_input("User ID", help="ID of the user who will own this cart item")
                        quantity = st.number_input("Quantity", min_value=1, step=1)
                        add_cart_submitted = st.form_submit_button("Add to Cart")

                        if add_cart_submitted:
                            if not user_id:
                                st.warning("Please provide a User ID.")
                            else:
                                # 1) Call Cart Service to add item
                                cart_payload = {
                                    "userId": user_id,
                                    "productId": selected_product['productId'],
                                    "productName": selected_product['name'],
                                    "quantity": quantity
                                }
                                try:
                                    cart_response = requests.post(f"{CART_SERVICE_URL}/cart", json=cart_payload, timeout=10)
                                    if cart_response.status_code == 201:
                                        # 2) Now call Product Service to remove stock
                                        # NOTE: productName must match the 'name' column if that's how your DB is queried
                                        remove_stock_payload = {
                                            "productName": selected_product['name'],
                                            "required_qty": quantity
                                        }
                                        remove_stock_response = requests.post(
                                            f"{PRODUCT_SERVICE_URL}/products/remove_stock",
                                            json=remove_stock_payload, timeout=10)
                                        if remove_stock_response.status_code == 200:
                                            st.success("Product added to cart and stock updated successfully!")
                                        else:
                                            error_msg = remove_stock_response.json().get("error", remove_stock_response.text)
                                            st.error(f"Error updating stock: {error_msg}")
                                    else:
                                        error_msg = cart_response.json().get("error", cart_response.text)
                                        st.error(f"Error adding to cart: {error_msg}")
                                except requests.exceptions.RequestException as e:
                                    st.error(f"Failed to connect to Cart Service: {e}")
                else:
                    st.info("No product selected. Select a row in the table above to add it to the cart.")
            else:
                st.info("No products found.")
        else:
            st.error("Error fetching products: " + response.text)

def main():
    run_product_ui()

if __name__ == "__main__":
    main()