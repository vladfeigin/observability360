import os
import streamlit as st
import requests
import pandas as pd

# Service URLs from environment variables (with defaults)
CART_SERVICE_URL = os.environ.get("CART_SERVICE_URL", "http://127.0.0.1:5002")
USER_SERVICE_URL = os.environ.get("USER_SERVICE_URL", "http://127.0.0.1:5000")
PRODUCT_SERVICE_URL = os.environ.get("PRODUCT_SERVICE_URL", "http://127.0.0.1:5001")

def run_cart_ui():
    st.title("Cart Service")

    # Two main actions: List Cart Items (with inline editing) and Add Cart Item.
    action = st.selectbox("Select Action", [
        "Select Action...",
        "List Cart Items",
        "Add Cart Item"
    ], index=0)

    if action == "List Cart Items":
        st.subheader("List Cart Items")
        user_id_input = st.text_input("User ID", help="Provide a valid User ID")

        if st.button("List Items"):
            if not user_id_input.strip():
                st.error("User ID cannot be empty.")
                return

            # --- Retrieve user details from User Service ---
            user_response = requests.get(f"{USER_SERVICE_URL}/users")
            if user_response.status_code != 200:
                st.error("Error fetching user details: " + user_response.text)
                return

            all_users = user_response.json()
            try:
                user_id_int = int(user_id_input.strip())
            except ValueError:
                st.error("User ID must be a valid integer.")
                return

            user_detail = next((u for u in all_users if u.get("id") == user_id_int), None)
            if not user_detail:
                st.error("User not found.")
                return

            # --- Retrieve cart items for this user ---
            params = {"userId": user_id_input.strip()}
            cart_response = requests.get(f"{CART_SERVICE_URL}/cart", params=params)
            if cart_response.status_code != 200:
                st.error("Error fetching cart items: " + cart_response.text)
                return

            items = cart_response.json()
            st.markdown(f"### Cart Items for {user_detail['firstName']} {user_detail['lastName']}")
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
            # Also store a copy of the original display for later comparison.
            st.session_state["cart_df_display_original"] = df_display.copy()

    # Only show the editor if we have loaded cart data.
    if "cart_df_display_original" in st.session_state:
        # Use the original display as the starting point.
        original_df_display = st.session_state["cart_df_display_original"]

        # Show an inline editor that does not allow adding new rows.
        edited_df = st.data_editor(
            original_df_display,
            hide_index=True,
            use_container_width=True,
            key="cart_editor"
        )

        # Warn if non-quantity fields are changed.
        for idx, edited_row in edited_df.iterrows():
            original_row = original_df_display.iloc[idx]
            if edited_row["productId"] != original_row["productId"]:
                st.warning(f"Row {idx+1}: Changing 'Product ID' is not allowed. This change will be ignored!")
            if edited_row["productName"] != original_row["productName"]:
                st.warning(f"Row {idx+1}: Changing 'Product Name' is not allowed. This change will be ignored!")

        if st.button("Save Changes"):
            full_df = st.session_state["cart_df_full"]
            changes_done = False
            # Loop through each row of the edited DataFrame.
            for idx, edited_row in edited_df.iterrows():
                try:
                    cart_item_id = full_df.iloc[idx]["id"]
                except IndexError:
                    st.error("Row index out of range. Please do not add new rows.")
                    continue

                # If the Delete checkbox is checked, update product stock then delete the cart item.
                if edited_row["Delete"]:
                    # Prepare payload to add back stock.
                    payload_stock = {
                        "productName": edited_row["productName"],
                        "added_qty": edited_row["quantity"]
                    }
                    r_stock = requests.post(f"{PRODUCT_SERVICE_URL}/products/add_stock", json=payload_stock, timeout=60)
                    if r_stock.status_code != 200:
                        error_msg = r_stock.json().get("error", r_stock.text)
                        st.error(f"Failed to add stock for product {edited_row['productName']}: {error_msg}")
                        continue  # Skip deletion if stock update fails
                    r = requests.delete(f"{CART_SERVICE_URL}/cart/{cart_item_id}", timeout=60)
                    if r.status_code != 200:
                        st.error(f"Failed to delete cart item with ID {cart_item_id}")
                        break
                    changes_done = True

                # Otherwise, if the quantity has changed, update the cart item.
                elif edited_row["quantity"] != original_df_display.iloc[idx]["quantity"]:
                    payload = {"quantity": edited_row["quantity"]}
                    r = requests.put(f"{CART_SERVICE_URL}/cart/{cart_item_id}", json=payload, timeout=60)
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

    elif action == "Add Cart Item":
        st.subheader("Add Cart Item")
        with st.form("add_cart_item_form"):
            user_id = st.text_input("User ID")
            product_id = st.text_input("Product ID")
            quantity = st.number_input("Quantity", min_value=1, step=1)
            submitted = st.form_submit_button("Add to Cart")
            if submitted:
                if not user_id or not product_id:
                    st.error("Please provide both User ID and Product ID.")
                else:
                    payload = {
                        "userId": user_id,
                        "productId": product_id,
                        "quantity": quantity
                    }
                    try:
                        response = requests.post(f"{CART_SERVICE_URL}/cart", json=payload)
                        if response.status_code == 201:
                            st.success("Cart item added successfully!")
                        else:
                            error_msg = response.json().get("error", response.text)
                            st.error(f"Error adding cart item: {error_msg}")
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")

def main():
    run_cart_ui()

if __name__ == "__main__":
    main()