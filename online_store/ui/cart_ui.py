import os
import streamlit as st
import requests
import pandas as pd
from online_store.otel.otel import configure_telemetry, trace_span

SERVICE_VERSION = "1.0.0"
instruments = configure_telemetry(None, "Cart UI", SERVICE_VERSION)

# Get instruments
tracer = instruments["tracer"]
logger = instruments["logger"]

# Service URLs from environment variables (with defaults)
CART_SERVICE_URL = os.environ.get("CART_SERVICE_URL", "http://127.0.0.1:5002")
USER_SERVICE_URL = os.environ.get("USER_SERVICE_URL", "http://127.0.0.1:5000")
PRODUCT_SERVICE_URL = os.environ.get(
    "PRODUCT_SERVICE_URL", "http://127.0.0.1:5001")
ORDER_SERVICE_URL = os.environ.get(
    "ORDER_SERVICE_URL", "http://127.0.0.1:5003")


@trace_span("run_cart_ui", tracer)
def run_cart_ui():
    st.title("Cart Service")

    # Two main actions: List Cart Items (and implicitly Add Cart Item is available in a form)
    action = st.selectbox("Select Action", [
        "Select Action...",
        "List Cart Items"
        # "Add Cart Item" is omitted due to known UI persistence bug.
    ], index=0)

    if action == "List Cart Items":
        st.subheader("List Cart Items")
        #  Instead of a text input for user ID, we call the User Service to fetch users.
        try:
            user_response = requests.get(
                f"{USER_SERVICE_URL}/users", timeout=10)
            if user_response.status_code != 200:
                st.error("Error fetching users: " + user_response.text)
                return
            users_list = user_response.json()
            if not users_list:
                st.error("No users found.")
                return
            # Build options like "12: John Doe"
            user_options = [
                f"{u['id']}: {u['firstName']} {u['lastName']}" for u in users_list]
            selected_user = st.selectbox(
                "Select User", user_options)  # [ADDED]
            user_id = selected_user.split(":")[0].strip()  # [ADDED]
        except Exception as e:
            logger.error(f"Error retrieving users: {e}")
            st.error(f"Failed to retrieve users: {e}")
            return

        # Save the selected user id in session state for order creation.
        st.session_state["cart_user_id"] = user_id  # [CHANGED]

        # --- Retrieve cart items for this user ---
        params = {"userId": user_id}
        with tracer.start_as_current_span("get_cart_items") as span_get_cart_items:
            span_get_cart_items.set_attribute("userId", user_id)
            # Call the Cart Service to get cart items for the selected user.
            cart_response = requests.get(
                f"{CART_SERVICE_URL}/cart", params=params, timeout=10)
            if cart_response.status_code != 200:
                logger.error(
                    "Error fetching cart items for user ID %s: %s", user_id, cart_response.text, exc_info=True)
                st.error("Error fetching cart items: " + cart_response.text)
                return
            items = cart_response.json()
            # Use the user’s full name in the header if available.
            user_detail = next(
                (u for u in users_list if str(u.get("id")) == user_id), {})
            full_name = f"{user_detail.get('firstName', 'Unknown')} {user_detail.get('lastName', '')}"
            st.markdown(f"### Cart Items for {full_name}")
            if not items:
                st.info("No cart items found.")
                return

        # Create a full DataFrame (df_full) from the API response.
        df_full = pd.DataFrame(items)
        if "id" not in df_full.columns:
            st.error("Cart items do not include an 'id' field.")
            return

        # Build a display DataFrame (df_display) with only the columns we want,
        # plus a new 'Delete' column.
        df_display = df_full[["productId", "productName", "quantity"]].copy()
        df_display["Delete"] = False

        # Save both DataFrames in session state for persistence.
        st.session_state["cart_df_full"] = df_full
        st.session_state["cart_df_display_original"] = df_display.copy()

    # Only show the editor if cart data is loaded.
    if "cart_df_display_original" in st.session_state:
        original_df_display = st.session_state["cart_df_display_original"]

        # Show an inline editor.
        edited_df = st.data_editor(
            original_df_display,
            hide_index=True,
            use_container_width=True,
            key="cart_editor"
        )

        # Warn if user changes non-updatable fields.
        for idx, edited_row in edited_df.iterrows():
            original_row = original_df_display.iloc[idx]
            if edited_row["productId"] != original_row["productId"]:
                st.warning(
                    f"Row {idx+1}: Changing 'Product ID' is not allowed. This change will be ignored!")
            if edited_row["productName"] != original_row["productName"]:
                st.warning(
                    f"Row {idx+1}: Changing 'Product Name' is not allowed. This change will be ignored!")

        # Save Changes button for updating/deleting individual cart items.
        if st.button("Save Changes"):
            full_df = st.session_state["cart_df_full"]
            changes_done = False
            with tracer.start_as_current_span("save_cart_changes"):
                # Process each row.
                for idx, edited_row in edited_df.iterrows():
                    try:
                        cart_item_id = full_df.iloc[idx]["id"]
                    except IndexError:
                        st.error(
                            "Row index out of range. Please do not add new rows.")
                        logger.error(
                            "Row index out of range. Please do not add new rows.")
                        continue

                    # If Delete is checked, update product stock and then delete the cart item.
                    if edited_row["Delete"]:
                        # When deleting, add the quantity back to the product stock.
                        update_payload = {
                            "productName": edited_row["productName"],
                            # positive value increases stock
                            "qty_change": int(edited_row["quantity"])
                        }
                        with tracer.start_as_current_span("return_product_to_stock") as span_update_stock:
                            span_update_stock.set_attribute(
                                "productName", edited_row["productName"])
                            span_update_stock.set_attribute(
                                "qty_change", int(edited_row["quantity"]))
                    
                            r_stock = requests.post(f"{PRODUCT_SERVICE_URL}/products/update_stock",
                                                json=update_payload, timeout=10)
                            if r_stock.status_code != 200:
                                error_msg = r_stock.json().get("error", r_stock.text)
                                logger.error(
                                    "Failed to update stock for product %s: %s", edited_row['productName'], error_msg, exc_info=True)
                                st.error(
                                    f"Failed to update stock for product {edited_row['productName']}: {error_msg}")
                                continue
                        # Delete the cart item.
                        with tracer.start_as_current_span("delete_cart_item") as span_delete_cart_item:
                            span_delete_cart_item.set_attribute(
                                "cart_item_id", cart_item_id)
                            span_delete_cart_item.set_attribute(
                                "productName", edited_row["productName"])
                            r = requests.delete(
                                f"{CART_SERVICE_URL}/cart/{cart_item_id}", timeout=60)
                            if r.status_code != 200:
                                logger.error(
                                    "Failed to delete cart item with ID %s: %s", cart_item_id, r.text, exc_info=True)
                                st.error(
                                    f"Failed to delete cart item with ID {cart_item_id}")
                                break
                        changes_done = True

                    # Otherwise, if the quantity has changed, update product stock accordingly.
                    elif edited_row["quantity"] != original_df_display.iloc[idx]["quantity"]:
                        old_qty = int(original_df_display.iloc[idx]["quantity"])
                        new_qty = int(edited_row["quantity"])
                        diff = new_qty - old_qty
                        # The change in product stock is the negative of the change in cart quantity.
                        # If diff > 0, then more items have been added to the cart, so stock decreases.
                        # If diff < 0, fewer items in cart means stock increases.
                        update_payload = {
                            "productName": edited_row["productName"],
                            "qty_change": -diff
                        }
                        with tracer.start_as_current_span("update_product_stock") as span_update_stock:
                            span_update_stock.set_attribute(
                                "productName", edited_row["productName"])
                            span_update_stock.set_attribute(
                                "qty_change", -diff)
                            r_stock = requests.post(f"{PRODUCT_SERVICE_URL}/products/update_stock",
                                                    json=update_payload, timeout=10)
                            if r_stock.status_code != 200:
                                error_msg = r_stock.json().get("error", r_stock.text)
                                logger.error(
                                    "Failed to update stock for product %s: %s", edited_row['productName'], error_msg, exc_info=True)
                                st.error(
                                    f"Failed to update stock for product {edited_row['productName']}: {error_msg}")
                                break
                            
                        # Update the cart item quantity.
                        payload = {"quantity": new_qty}
                        with tracer.start_as_current_span("update_cart_item") as span_update_cart_item:
                            span_update_cart_item.set_attribute(
                                "cart_item_id", cart_item_id)
                            span_update_cart_item.set_attribute(
                                "quantity", new_qty)
                            
                            r = requests.put(f"{CART_SERVICE_URL}/cart/{cart_item_id}",
                                             json=payload, timeout=60)
                            if r.status_code != 200:
                                logger.error("Failed to update cart item with ID %s: %s", cart_item_id, r.text)
                                st.error(
                                    f"Failed to update cart item with ID {cart_item_id}")
                                break
                        changes_done = True

                if changes_done:
                    st.success("Changes saved successfully!")
                else:
                    st.info("No changes to save.")

            # Clear cart-related session state so the grid reloads next time.
            for key in list(st.session_state.keys()):
                if key.startswith("cart_"):
                    del st.session_state[key]

        # Create Order Button remains as-is.
        if st.button("Create Order"):
            if "cart_user_id" not in st.session_state:
                st.error("User ID not found in session state.")
            else:
                with tracer.start_as_current_span("create_order_from_cart_ui"):
                    payload = {"userId": st.session_state["cart_user_id"]}
                    with tracer.start_as_current_span("create_order") as span_create_order:
                        span_create_order.set_attribute(
                            "userId", st.session_state["cart_user_id"])
                        response = requests.post(
                            f"{ORDER_SERVICE_URL}/orders", json=payload, timeout=10)
                        if response.status_code == 201:
                            order_details = response.json()
                            st.success(
                                f"Order created successfully! Order ID: {order_details.get('orderId')}")
                            # After order creation, clear the cart by deleting each cart item.
                            if "cart_df_full" in st.session_state:
                                df_full = st.session_state["cart_df_full"]
                                for idx, row in df_full.iterrows():
                                    cart_item_id = row["id"]
                                    with tracer.start_as_current_span("delete_cart_item") as span_delete_cart_item:
                                        span_delete_cart_item.set_attribute(
                                            "cart_item_id", cart_item_id)
                                        r_del = requests.delete(
                                            f"{CART_SERVICE_URL}/cart/{cart_item_id}", timeout=10)
                                        if r_del.status_code != 200:
                                            st.error(
                                                f"Failed to delete cart item with ID {cart_item_id}")
                                            logger.error("Failed to delete cart item with ID %s: %s", cart_item_id, r_del.text, exc_info=True)
                                # Clear cart-related session state.
                                for key in list(st.session_state.keys()):
                                    if key.startswith("cart_"):
                                        del st.session_state[key]
                                st.info("Cart cleared successfully.")
                        else:
                            error_msg = response.json().get("error", response.text)
                            logger.error("Error creating order: %s", error_msg, exc_info=True)
                            st.error(f"Error creating order: {error_msg}")
    
    #this option is not available yet 
    elif action == "Add Cart Item":
        st.subheader("Add Cart Item")
        # Clear any existing cart session state.
        for key in list(st.session_state.keys()):
            if key.startswith("cart_"):
                del st.session_state[key]
        with st.form("add_cart_item_form"):
            user_id = st.text_input("User ID")
            product_id = st.text_input("Product ID")
            product_name = st.text_input("Product Name")
            quantity = st.number_input("Quantity", min_value=0, step=1)
            submitted = st.form_submit_button("Add to Cart")
            if submitted:
                if not user_id or not product_id:
                    logger.error("User ID or Product ID is empty.")
                    st.error("Please provide both User ID and Product ID.")
                else:
                    payload = {
                        "userId": user_id,
                        "productId": product_id,
                        "productName": product_name,
                        "quantity": quantity
                    }
                    try:
                        response = requests.post(
                            f"{CART_SERVICE_URL}/cart", json=payload, timeout=60)
                        if response.status_code == 201:
                            # Update product stock by removing the quantity.
                            update_payload = {
                                "productName": product_name,
                                # [CHANGED] Use unified parameter for stock update.
                                "qty_change": -quantity
                            }
                            r_stock = requests.post(f"{PRODUCT_SERVICE_URL}/products/update_stock",
                                                    json=update_payload, timeout=60)
                            if r_stock.status_code != 200:
                                error_msg = r_stock.json().get("error", r_stock.text)
                                logger.error(
                                    f"Failed to update stock for product {product_name}: {error_msg}")
                                st.error(
                                    f"Error updating product stock: {error_msg}")
                            else:
                                st.success(
                                    "Cart item added successfully and product stock updated!")
                        else:
                            try:
                                error_msg = response.json().get("error", response.text)
                            except Exception:
                                logger.error(
                                    f"Error adding cart item: {response.text}")
                                error_msg = response.text
                            st.error(f"Error adding cart item: {error_msg}")
                    except Exception as e:
                        logger.error(f"Error adding cart item: {str(e)}")
                        st.error(f"An error occurred: {str(e)}")


def main():
    run_cart_ui()


if __name__ == "__main__":
    main()
