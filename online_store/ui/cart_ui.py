import os
from opentelemetry import propagate
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
PRODUCT_SERVICE_URL = os.environ.get("PRODUCT_SERVICE_URL", "http://127.0.0.1:5001")
ORDER_SERVICE_URL = os.environ.get("ORDER_SERVICE_URL", "http://127.0.0.1:5003")

@trace_span("run_cart_ui", tracer)
def run_cart_ui():
    st.header("Cart Service", divider="blue")

    # Two main actions: List Cart Items (and implicitly Add Cart Item is available in a form)
    action = st.selectbox("Select Cart Action", [
        "Select Action...",
        "List Cart Items",
        "Add Cart Item"], index=0)

    # ----------------------------------------------------------------
    # LIST CART ITEMS
    # ----------------------------------------------------------------
    if action == "List Cart Items":
        with tracer.start_as_current_span("list_cart_items") as list_span:  # CHANGED
            st.subheader("List Cart Items")

            # CHANGED: Create a child span for fetching user info
            with tracer.start_as_current_span("fetch_users") as fetch_users_span:
                try:
                    headers = {}
                    propagate.inject(headers)  # CHANGED: Propagate current context
                    user_response = requests.get(f"{USER_SERVICE_URL}/users", timeout=10, headers=headers)
                    if user_response.status_code != 200:
                        st.error("Error fetching users: " + user_response.text)
                        return
                    users_list = user_response.json()
                    if not users_list:
                        st.error("No users found.")
                        return
                except Exception as e:
                    logger.error(f"Error retrieving users: {e}")
                    st.error(f"Failed to retrieve users: {e}")
                    return

            # Build user select box
            user_options = [f"{u['id']}: {u['firstName']} {u['lastName']}" for u in users_list]
            selected_user = st.selectbox("Select User", user_options)
            user_id = selected_user.split(":")[0].strip()
            st.session_state["cart_user_id"] = user_id

            # CHANGED: Create a child span for fetching cart items
            with tracer.start_as_current_span("fetch_cart_items") as fetch_cart_span:
                headers = {}
                propagate.inject(headers)  # CHANGED: Propagate context
                params = {"userId": user_id}
                cart_response = requests.get(f"{CART_SERVICE_URL}/cart", params=params, timeout=10, headers=headers)
                if cart_response.status_code != 200:
                    logger.error(f"Error fetching cart items for user ID {user_id}: {cart_response.text}")
                    st.error("Error fetching cart items: " + cart_response.text)
                    return
                items = cart_response.json()

            user_detail = next((u for u in users_list if str(u.get("id")) == user_id), {})
            full_name = f"{user_detail.get('firstName', 'Unknown')} {user_detail.get('lastName', '')}"
            st.markdown(f"### Cart Items for {full_name}")

            if not items:
                st.info("No cart items found.")
                return

            # Prepare DataFrame for display
            df_full = pd.DataFrame(items)
            if "id" not in df_full.columns:
                st.error("Cart items do not include an 'id' field.")
                return

            df_display = df_full[["productId", "productName", "quantity"]].copy()
            df_display["Delete"] = False

            st.session_state["cart_df_full"] = df_full
            st.session_state["cart_df_display_original"] = df_display.copy()

    # ----------------------------------------------------------------
    # SHOW EDITOR IF CART DATA LOADED
    # ----------------------------------------------------------------
    if "cart_df_display_original" in st.session_state:
        original_df_display = st.session_state["cart_df_display_original"]

        # Inline editor for the cart items
        edited_df = st.data_editor(
            original_df_display,
            hide_index=True,
            use_container_width=True,
            key="cart_editor"
        )

        # Warn if user changes non-updatable fields
        for idx, edited_row in edited_df.iterrows():
            original_row = original_df_display.iloc[idx]
            if edited_row["productId"] != original_row["productId"]:
                st.warning(f"Row {idx+1}: Changing 'Product ID' is not allowed. This change will be ignored!")
            if edited_row["productName"] != original_row["productName"]:
                st.warning(f"Row {idx+1}: Changing 'Product Name' is not allowed. This change will be ignored!")

        # ----------------------------------------------------------------
        # SAVE CHANGES
        # ----------------------------------------------------------------
        if st.button("Save Changes"):
            with tracer.start_as_current_span("save_cart_changes") as save_changes_span:  # CHANGED
                full_df = st.session_state["cart_df_full"]
                changes_done = False

                for idx, edited_row in edited_df.iterrows():
                    try:
                        cart_item_id = full_df.iloc[idx]["id"]
                    except IndexError:
                        st.error("Row index out of range. Please do not add new rows.")
                        logger.error("Row index out of range. Please do not add new rows.")
                        continue

                    # If Delete is checked, add stock back, then delete cart item
                    if edited_row["Delete"]:
                        with tracer.start_as_current_span("delete_cart_item") as delete_span:  # CHANGED
                            update_payload = {
                                "productName": edited_row["productName"],
                                "qty_change": int(edited_row["quantity"])
                            }
                            headers = {}
                            propagate.inject(headers)  # CHANGED
                            r_stock = requests.post(
                                f"{PRODUCT_SERVICE_URL}/products/update_stock",
                                json=update_payload, timeout=10, headers=headers
                            )
                            if r_stock.status_code != 200:
                                error_msg = r_stock.json().get("error", r_stock.text)
                                logger.error(f"Failed to update stock for product {edited_row['productName']}: {error_msg}")
                                st.error(f"Failed to update stock for product {edited_row['productName']}: {error_msg}")
                                continue

                            headers = {}
                            propagate.inject(headers)
                            r = requests.delete(
                                f"{CART_SERVICE_URL}/cart/{cart_item_id}",
                                timeout=60,
                                headers=headers
                            )
                            if r.status_code != 200:
                                logger.error(f"Failed to delete cart item with ID {cart_item_id}: {r.text}")
                                st.error(f"Failed to delete cart item with ID {cart_item_id}")
                                break
                            changes_done = True

                    # Otherwise, if quantity changed, update stock + cart item
                    elif edited_row["quantity"] != original_df_display.iloc[idx]["quantity"]:
                        old_qty = int(original_df_display.iloc[idx]["quantity"])
                        new_qty = int(edited_row["quantity"])
                        diff = new_qty - old_qty
                        with tracer.start_as_current_span("update_cart_item") as update_cart_item_span: 
                           
                            update_payload = {
                                "productName": edited_row["productName"],
                                "qty_change": -diff
                            }
                            update_cart_item_span.set_attribute("product_name", edited_row["productName"])
                            update_cart_item_span.set_attribute("quantity_change", -diff)
                            headers = {}
                            propagate.inject(headers)
                            r_stock = requests.post(
                                f"{PRODUCT_SERVICE_URL}/products/update_stock",
                                json=update_payload, timeout=10, headers=headers
                            )
                            if r_stock.status_code != 200:
                                error_msg = r_stock.json().get("error", r_stock.text)
                                logger.error(f"Failed to update stock for product {edited_row['productName']}: {error_msg}",exc_info=True) 
                                st.error(f"Failed to update stock for product {edited_row['productName']}: {error_msg}")
                                break

                            # Update the cart item quantity
                            payload = {"quantity": new_qty}
                            headers = {}
                            propagate.inject(headers)
                            r = requests.put(
                                f"{CART_SERVICE_URL}/cart/{cart_item_id}",
                                json=payload,
                                timeout=60,
                                headers=headers
                            )
                            if r.status_code != 200:
                                logger.error(f"Failed to update cart item with ID {cart_item_id}: {r.text}")
                                st.error(f"Failed to update cart item with ID {cart_item_id}")
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

        # ----------------------------------------------------------------
        # CREATE ORDER
        # ----------------------------------------------------------------
        if st.button("Create Order"):
            with tracer.start_as_current_span("create_order_flow") as order_flow_span:  # CHANGED
                if "cart_user_id" not in st.session_state:
                    st.error("User ID not found in session state.")
                else:
                    headers = {}
                    propagate.inject(headers)  # CHANGED
                    payload = {"userId": st.session_state["cart_user_id"]}

                    # Child span for calling the Order Service
                    with tracer.start_as_current_span("call_order_service") as call_order_service_span:
                        call_order_service_span.set_attribute("user_id", st.session_state["cart_user_id"])
                        response = requests.post(
                            f"{ORDER_SERVICE_URL}/orders",
                            json=payload,
                            headers=headers,
                            timeout=10
                        )

                    if response.status_code == 201:
                        order_details = response.json()
                        st.success(f"Order created successfully! Order ID: {order_details.get('orderId')}")

                        # Child span for deleting cart items post-order
                        with tracer.start_as_current_span("cleanup_cart_items") as cart_cleanup_span:
                            if "cart_df_full" in st.session_state:
                                df_full = st.session_state["cart_df_full"]
                                for idx, row in df_full.iterrows():
                                    cart_item_id = row["id"]
                                    headers = {}
                                    propagate.inject(headers)  
                                    r_del = requests.delete(
                                        f"{CART_SERVICE_URL}/cart/{cart_item_id}",
                                        headers=headers,
                                        timeout=10
                                    )
                                    if r_del.status_code != 200:
                                        st.error(f"Failed to delete cart item with ID {cart_item_id}")
                                # Clear cart-related session state.
                                for key in list(st.session_state.keys()):
                                    if key.startswith("cart_"):
                                        del st.session_state[key]
                            st.info("Cart cleared successfully.")
                    else:
                        try:
                            error_msg = response.json().get("error", response.text)
                        except Exception:
                            logger.error(f"Error creating order: {response.text}", exc_info=True)
                            error_msg = response.text
                        st.error(f"Error creating order: {error_msg}")

    # ----------------------------------------------------------------
    # ADD CART ITEM (Disabled by default in your code)
    # ----------------------------------------------------------------
    elif action == "Add Cart Item":
        with tracer.start_as_current_span("add_cart_item_flow") as add_item_span:  
            logger.error("Add Cart Item Action is not supported.")
            st.error("Add Cart Item Action is not supported.")
            raise Exception("Add Cart Item Action is not supported")
        
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
                        headers = {}
                        propagate.inject(headers)  # CHANGED
                        try:
                            response = requests.post(f"{CART_SERVICE_URL}/cart", json=payload, timeout=60, headers=headers)
                            if response.status_code == 201:
                                # Update product stock by removing the quantity.
                                update_payload = {
                                    "productName": product_name,
                                    "qty_change": -quantity
                                }
                                headers = {}
                                propagate.inject(headers)  # CHANGED
                                r_stock = requests.post(
                                    f"{PRODUCT_SERVICE_URL}/products/update_stock",
                                    json=update_payload,
                                    timeout=60,
                                    headers=headers
                                )
                                if r_stock.status_code != 200:
                                    error_msg = r_stock.json().get("error", r_stock.text)
                                    logger.error(f"Failed to update stock for product {product_name}: {error_msg}")
                                    st.error(f"Error updating product stock: {error_msg}")
                                else:
                                    st.success("Cart item added successfully and product stock updated!")
                            else:
                                try:
                                    error_msg = response.json().get("error", response.text)
                                except Exception:
                                    logger.error(f"Error adding cart item: {response.text}")
                                    error_msg = response.text
                                st.error(f"Error adding cart item: {error_msg}")
                        except Exception as e:
                            logger.error(f"Error adding cart item: {str(e)}")
                            st.error(f"An error occurred: {str(e)}")

def main():
    run_cart_ui()

if __name__ == "__main__":
    main()