import os
import logging
import streamlit as st
import requests
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from online_store.otel.otel import configure_telemetry, trace_span

logger = logging.getLogger(__name__)

SERVICE_VERSION = "1.0.0"
instruments = configure_telemetry(None, "Product UI", SERVICE_VERSION)

# Get instruments
tracer = instruments["tracer"]

PRODUCT_SERVICE_URL = os.environ.get('PRODUCT_SERVICE_URL', 'http://127.0.0.1:5001')
CART_SERVICE_URL = os.environ.get('CART_SERVICE_URL', 'http://127.0.0.1:5002')
USER_SERVICE_URL = os.environ.get('USER_SERVICE_URL', 'http://127.0.0.1:5000')

@trace_span("run_product_ui", tracer)
def run_product_ui():
    """ Product Service UI. 
    This UI allows users to add products, list products, update products, delete products,
    and add products to the cart.
    """
    logger.info("Product UI - run_product_ui.")
    st.header("Product Service")

    # [CHANGED NEW] Modified the action selectbox to include "Delete Product"
    action = st.selectbox(
        "Select Action",
        ["Select Action...", "List Products", "Add Product", "Update Product", "Delete Product"],
        index=0
    )

    # ------------------- ADD PRODUCT -------------------
    if action == "Add Product":
        logger.info("Product UI - Add Product.")
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
                with tracer.start_as_current_span("add_product_ui") as add_product_span:
                    add_product_span.set_attribute("product_id", product_id)
                    add_product_span.set_attribute("name", name)
                    add_product_span.set_attribute("description", description)
                    add_product_span.set_attribute("number_items_in_stock", number_items_in_stock)
                    response = requests.post(f"{PRODUCT_SERVICE_URL}/products", json=payload, timeout=10)
                    if response.status_code == 201:
                        st.success("Product added successfully!")
                    else:
                        st.error("Error adding product: " + response.text)
                        logger.error("Error adding product: %s", response.text, exc_info=True)

    # ------------------- LIST PRODUCTS -------------------
    elif action == "List Products":
        logger.info("Product UI - List Product.")
        st.subheader("List and Select Products")

        logger.info("Fetching products from Product Service.")
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

                # [FIXED AGAIN] Ensure selected_rows is a list
                selected_rows = grid_response.get("selected_rows")
                if isinstance(selected_rows, pd.DataFrame):
                    if selected_rows.empty:
                        selected_rows = []
                    else:
                        selected_rows = selected_rows.to_dict('records')
                elif selected_rows is None:
                    selected_rows = []

                if len(selected_rows) == 0:
                    st.info("No product selected. Please select a product by clicking the checkbox in the grid.")
                    logger.info("No product selected. User needs to click the checkbox in the grid.")
                else:
                    selected_product = selected_rows[0]
                    st.markdown(
                        f"**Selected Product**: `{selected_product['productId']}` - {selected_product['name']}"
                    )
                    try:
                        user_response = requests.get(f"{USER_SERVICE_URL}/users", timeout=10)
                        if user_response.status_code != 200:
                            st.error("Error fetching users: " + user_response.text)
                            logger.error("Error fetching users: %s", user_response.text, exc_info=True)
                        else:
                            users_list = user_response.json()
                            if users_list:
                                user_options = [f"{u['id']}: {u['firstName']} {u['lastName']}" for u in users_list]
                                selected_user = st.selectbox("Select User", user_options)
                                user_id = selected_user.split(":")[0].strip()
                            else:
                                st.error("No users found.")
                                logger.info("No users found.")
                                return
                    except Exception as e:
                            st.error(f"Failed to retrieve users: {e}")
                            logger.error("Failed to retrieve users: %s", e, exc_info=True)
                            return

                    with st.form("add_to_cart_form"):
                        quantity = st.number_input("Quantity", min_value=1, step=1)
                        add_cart_submitted = st.form_submit_button("Add to Cart")
                        if add_cart_submitted:
                            if not user_id:
                                st.warning("Please select a user.")
                            else:
                                cart_payload = {
                                    "userId": user_id,
                                    "productId": selected_product['productId'],
                                    "productName": selected_product['name'],
                                    "quantity": quantity
                                }
                                with tracer.start_as_current_span("add_to_cart_ui") as add_to_cart_span:
                                    add_to_cart_span.set_attribute("user_id", user_id)
                                    add_to_cart_span.set_attribute("product_id", selected_product['productId'])
                                    add_to_cart_span.set_attribute("product_name", selected_product['name'])
                                    add_to_cart_span.set_attribute("quantity", quantity)
                                    try:
                                        with tracer.start_as_current_span("add_to_cart_ui_request"):
                                            cart_response = requests.post(f"{CART_SERVICE_URL}/cart", json=cart_payload, timeout=10)
                                            if cart_response.status_code == 201:
                                                # [CHANGED] Use new unified stock update endpoint:
                                                update_stock_payload = {
                                                    "productName": selected_product['name'],
                                                    "qty_change": -quantity   # Negative value to decrease stock
                                                }
                                                with tracer.start_as_current_span("update_stock_ui_request"):
                                                    update_stock_response = requests.post(
                                                        f"{PRODUCT_SERVICE_URL}/products/update_stock",
                                                        json=update_stock_payload, timeout=10)
                                                    if update_stock_response.status_code == 200:
                                                        st.success("Product added to cart and stock updated successfully!")
                                                    else:
                                                        error_msg = update_stock_response.json().get("error", update_stock_response.text)
                                                        st.error(f"Error updating stock: {error_msg}")
                                                        logger.error("Error updating stock: %s", error_msg, exc_info=True)
                                            else:
                                                error_msg = cart_response.json().get("error", cart_response.text)
                                                st.error(f"Error adding to cart: {error_msg}")
                                                logger.error("Error adding to cart: %s", error_msg, exc_info=True)
                                    except requests.exceptions.RequestException as e:
                                                    logger.error("Failed to connect to Cart Service: %s", e, exc_info=True)
                                                    st.error(f"Failed to connect to Cart Service: {e}")
            else:
                st.info("No products found.")
                logger.info("No products found in the Product Service.")
        else:
            st.error("Error fetching products: " + response.text)
            logger.error("Error fetching products: %s", response.text, exc_info=True)

    # ------------------- UPDATE PRODUCT -------------------
    elif action == "Update Product":  # [CHANGED NEW] New Update Product action added
        logger.info("Product UI - Update Product.")
        st.subheader("Update Product Quantity")
        
        # Fetch products to update
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

                st.write("Edit the 'Number of Items in Stock' field directly in the table below. Then select the row by clicking its checkbox.")
                gb = GridOptionsBuilder.from_dataframe(df)
                gb.configure_column("numberItemsInStock", editable=True)  # [CHANGED NEW] Enable editing for quantity
                gb.configure_selection(selection_mode="single", use_checkbox=True)
                grid_options = gb.build()

                grid_response = AgGrid(
                    df,
                    gridOptions=grid_options,
                    update_mode=GridUpdateMode.SELECTION_CHANGED,  # [CHANGED NEW] Use SELECTION_CHANGED for immediate selection updates
                    theme='streamlit',
                    height=300
                )

                # [FIXED AGAIN] Ensure selected_rows is a list
                selected_rows = grid_response.get("selected_rows")
                if isinstance(selected_rows, pd.DataFrame):
                    if selected_rows.empty:
                        selected_rows = []
                    else:
                        selected_rows = selected_rows.to_dict('records')
                elif selected_rows is None:
                    selected_rows = []
                
                logger.info("Update Product - Grid response: %s", grid_response)

                if st.button("Update Selected Product"):  # [CHANGED NEW] New button for updating product
                    if len(selected_rows) == 0:
                        st.error("Please select a product to update.")
                        logger.info("No product selected for update.")
                    else:
                        selected_product = selected_rows[0]
                        updated_stock = selected_product.get("numberItemsInStock")
                        product_id = selected_product.get("productId")
                        update_payload = {"numberItemsInStock": updated_stock}
                        with tracer.start_as_current_span("update_product_ui"):
                            response = requests.put(f"{PRODUCT_SERVICE_URL}/products/{product_id}", json=update_payload, timeout=10)
                            if response.status_code == 200:
                                st.success("Product updated successfully!")
                            else:
                                st.error("Error updating product: " + response.text)
                                logger.error("Error updating product: %s", response.text, exc_info=True)
            else:
                st.info("No products available for update.")
                logger.info("No products available for update.")
        else:
            st.error("Error fetching products: " + response.text)
            logger.error("Error fetching products: %s", response.text, exc_info=True)

    # ------------------- DELETE PRODUCT -------------------
    elif action == "Delete Product":  # [CHANGED NEW] New Delete Product action added
        logger.info("Product UI - Delete Product.")
        st.subheader("Delete Product")
        
        # Fetch products to delete
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

                st.write("Select the product(s) to delete by clicking the checkbox in the table below.")
                gb = GridOptionsBuilder.from_dataframe(df)
                gb.configure_selection(selection_mode="multiple", use_checkbox=True)  # Allow multiple deletions
                grid_options = gb.build()

                grid_response = AgGrid(
                    df,
                    gridOptions=grid_options,
                    update_mode=GridUpdateMode.SELECTION_CHANGED,
                    theme='streamlit',
                    height=300
                )

                # [FIXED AGAIN] Ensure selected_rows is a list
                selected_rows = grid_response.get("selected_rows")
                if isinstance(selected_rows, pd.DataFrame):
                    if selected_rows.empty:
                        selected_rows = []
                    else:
                        selected_rows = selected_rows.to_dict('records')
                elif selected_rows is None:
                    selected_rows = []
                
                logger.info("Delete Product - Grid response: %s", grid_response)

                if st.button("Delete Selected Product"):  # [CHANGED NEW] New button for deleting products
                    if len(selected_rows) == 0:
                        st.error("Please select at least one product to delete.")
                        logger.info("No product selected for deletion.")
                    else:
                        deletion_errors = []
                        for product in selected_rows:
                            product_id = product.get("productId")
                            with tracer.start_as_current_span("delete_product_ui"):
                                delete_response = requests.delete(f"{PRODUCT_SERVICE_URL}/products/{product_id}", timeout=10)
                                if delete_response.status_code != 200:
                                    deletion_errors.append(f"Failed to delete product {product_id}: {delete_response.text}")
                        if deletion_errors:
                            st.error("Some deletions failed: " + "; ".join(deletion_errors))
                            logger.error("Deletion errors: %s", "; ".join(deletion_errors), exc_info=True)
                        else:
                            st.success("Selected products deleted successfully!")
            else:
                st.info("No products available for deletion.")
                logger.info("No products available for deletion.")
        else:
            st.error("Error fetching products: " + response.text)
            logger.error("Error fetching products: %s", response.text, exc_info=True)

def main():
    logger.info("Product UI - main.")
    run_product_ui()

if __name__ == "__main__":
    main()