import os
import streamlit as st
import requests
import pandas as pd
from online_store.otel.otel import configure_telemetry, trace_span

SERVICE_VERSION = "1.0.0"
instruments = configure_telemetry(None, "Cart UI", SERVICE_VERSION)

# Get instruments
tracer = instruments["tracer"]

# Service URLs from environment variables (with defaults)
CART_SERVICE_URL = os.environ.get("CART_SERVICE_URL", "http://127.0.0.1:5002")
USER_SERVICE_URL = os.environ.get("USER_SERVICE_URL", "http://127.0.0.1:5000")
PRODUCT_SERVICE_URL = os.environ.get("PRODUCT_SERVICE_URL", "http://127.0.0.1:5001")
ORDER_SERVICE_URL = os.environ.get("ORDER_SERVICE_URL", "http://127.0.0.1:5003")

@trace_span("run_cart_ui", tracer)
def run_cart_ui():
    st.title("Cart Service")

    # Two main actions: List Cart Items and Add Cart Item.
    action = st.selectbox("Select Action", [
        "Select Action...",
        "List Cart Items",
        #"Add Cart Item" - there is a bug that cart list persists in the page ...
    ], index=0)

    if action == "List Cart Items":
        st.subheader("List Cart Items")
        # [CHANGED] Instead of a text input for user ID, we call the User Service to fetch users.
        try:
            user_response = requests.get(f"{USER_SERVICE_URL}/users", timeout=10)
            if user_response.status_code != 200:
                st.error("Error fetching users: " + user_response.text)
                return
            users_list = user_response.json()
            if not users_list:
                st.error("No users found.")
                return
            # Build options like "12: John Doe"
            user_options = [f"{u['id']}: {u['firstName']} {u['lastName']}" for u in users_list]
            selected_user = st.selectbox("Select User", user_options)  # [ADDED]
            user_id = selected_user.split(":")[0].strip()  # [ADDED]
        except Exception as e:
            st.error(f"Failed to retrieve users: {e}")
            return

        # Save the selected user id in session state for order creation.
        st.session_state["cart_user_id"] = user_id  # [CHANGED]

        # --- Retrieve cart items for this user ---
        params = {"userId": user_id}  # [CHANGED]
        cart_response = requests.get(f"{CART_SERVICE_URL}/cart", params=params)
        if cart_response.status_code != 200:
            st.error("Error fetching cart items: " + cart_response.text)
            return
        items = cart_response.json()
        # [CHANGED] Use the user’s full name in the header if available.
        # Try to locate the user details from our fetched users_list.
        user_detail = next((u for u in users_list if str(u.get("id")) == user_id), {})
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
                st.warning(f"Row {idx+1}: Changing 'Product ID' is not allowed. This change will be ignored!")
            if edited_row["productName"] != original_row["productName"]:
                st.warning(f"Row {idx+1}: Changing 'Product Name' is not allowed. This change will be ignored!")

        # Save Changes button for updating/deleting individual cart items.
        if st.button("Save Changes"):
            full_df = st.session_state["cart_df_full"]
            changes_done = False
            # Process each row.
            for idx, edited_row in edited_df.iterrows():
                try:
                    cart_item_id = full_df.iloc[idx]["id"]
                except IndexError:
                    st.error("Row index out of range. Please do not add new rows.")
                    continue

                # If Delete is checked, update product stock then delete the cart item.
                if edited_row["Delete"]:
                    payload_stock = {
                        "productName": edited_row["productName"],
                        "added_qty": int(edited_row["quantity"])
                    }
                    r_stock = requests.post(f"{PRODUCT_SERVICE_URL}/products/add_stock",
                                            json=payload_stock, timeout=10)
                    if r_stock.status_code != 200:
                        error_msg = r_stock.json().get("error", r_stock.text)
                        st.error(f"Failed to add stock for product {edited_row['productName']}: {error_msg}")
                        continue
                    r = requests.delete(f"{CART_SERVICE_URL}/cart/{cart_item_id}", timeout=60)
                    if r.status_code != 200:
                        st.error(f"Failed to delete cart item with ID {cart_item_id}")
                        break
                    changes_done = True

                # Otherwise, if the quantity has changed, update product stock accordingly.
                elif edited_row["quantity"] != original_df_display.iloc[idx]["quantity"]:
                    old_qty = int(original_df_display.iloc[idx]["quantity"])
                    new_qty = int(edited_row["quantity"])
                    diff = new_qty - old_qty

                    if diff > 0:
                        payload_stock = {
                            "productName": edited_row["productName"],
                            "required_qty": int(diff)
                        }
                        r_stock = requests.post(f"{PRODUCT_SERVICE_URL}/products/remove_stock",
                                                json=payload_stock, timeout=10)
                        if r_stock.status_code != 200:
                            error_msg = r_stock.json().get("error", r_stock.text)
                            st.error(f"Failed to remove {diff} items from product {edited_row['productName']}: {error_msg}")
                            break
                    elif diff < 0:
                        payload_stock = {
                            "productName": edited_row["productName"],
                            "added_qty": int(-diff)
                        }
                        r_stock = requests.post(f"{PRODUCT_SERVICE_URL}/products/add_stock",
                                                json=payload_stock, timeout=10)
                        if r_stock.status_code != 200:
                            error_msg = r_stock.json().get("error", r_stock.text)
                            st.error(f"Failed to add {-diff} items back to product {edited_row['productName']}: {error_msg}")
                            break
                    payload = {"quantity": new_qty}
                    r = requests.put(f"{CART_SERVICE_URL}/cart/{cart_item_id}",
                                     json=payload, timeout=60)
                    if r.status_code != 200:
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

        # Create Order Button remains as-is.
        if st.button("Create Order"):
            if "cart_user_id" not in st.session_state:
                st.error("User ID not found in session state.")
            else:
                payload = {"userId": st.session_state["cart_user_id"]}
                response = requests.post(f"{ORDER_SERVICE_URL}/orders", json=payload, timeout=10)
                if response.status_code == 201:
                    order_details = response.json()
                    st.success(f"Order created successfully! Order ID: {order_details.get('orderId')}")
                    # After order creation, clear the cart by deleting each cart item.
                    if "cart_df_full" in st.session_state:
                        df_full = st.session_state["cart_df_full"]
                        for idx, row in df_full.iterrows():
                            cart_item_id = row["id"]
                            r_del = requests.delete(f"{CART_SERVICE_URL}/cart/{cart_item_id}", timeout=10)
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
                        error_msg = response.text
                    st.error(f"Error creating order: {error_msg}")

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
                    st.error("Please provide both User ID and Product ID.")
                else:
                    payload = {
                        "userId": user_id,
                        "productId": product_id,
                        "productName": product_name,
                        "quantity": quantity
                    }
                    try:
                        response = requests.post(f"{CART_SERVICE_URL}/cart", json=payload, timeout=60)
                        if response.status_code == 201:
                            # Update product stock by removing the quantity.
                            payload_stock = {
                                "productName": product_name,
                                "required_qty": int(quantity)
                            }
                            r_stock = requests.post(f"{PRODUCT_SERVICE_URL}/products/remove_stock",
                                                    json=payload_stock, timeout=60)
                            if r_stock.status_code != 200:
                                error_msg = r_stock.json().get("error", r_stock.text)
                                st.error(f"Error updating product stock: {error_msg}")
                            else:
                                st.success("Cart item added successfully and product stock updated!")
                        else:
                            try:
                                error_msg = response.json().get("error", response.text)
                            except Exception:
                                error_msg = response.text
                            st.error(f"Error adding cart item: {error_msg}")
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")

def main():
    run_cart_ui()

if __name__ == "__main__":
    main()