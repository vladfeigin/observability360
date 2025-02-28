import os
import streamlit as st
import requests
import pandas as pd

# Use environment variables for service URLs, with defaults if not set
CART_SERVICE_URL = os.environ.get("CART_SERVICE_URL", "http://127.0.0.1:5002")
USER_SERVICE_URL = os.environ.get("USER_SERVICE_URL", "http://127.0.0.1:5000")

def run_cart_ui():
    st.title("Cart Service")

    # Action selection
    action = st.selectbox("Select Action", [
        "Select Action...",
        "List Cart Items",
        "Add Cart Item",
        "Update Cart Item",
        "Delete Cart Item"
    ], index=0)

    # ------------------- LIST CART ITEMS -------------------
    if action == "List Cart Items":
        st.subheader("List Cart Items")
        user_id = st.text_input("User ID", help="Provide a valid User ID")

        if st.button("List Items"):
            try:
                if not user_id.strip():
                    raise ValueError("User ID cannot be empty.")

                # --- Get user details from User Service ---
                # (GET /users returns all users; here we filter by the provided ID)
                user_response = requests.get(f"{USER_SERVICE_URL}/users")
                if user_response.status_code == 200:
                    all_users = user_response.json()
                    try:
                        user_id_int = int(user_id.strip())
                    except ValueError:
                        st.error("User ID must be a valid integer.")
                        return
                    user_detail = next((u for u in all_users if u.get("id") == user_id_int), None)
                    if not user_detail:
                        st.error("User not found.")
                        return
                else:
                    st.error("Error fetching user details: " + user_response.text)
                    return

                # --- Get cart items for the given user ---
                params = {"userId": user_id.strip()}
                cart_response = requests.get(f"{CART_SERVICE_URL}/cart", params=params)
                if cart_response.status_code == 200:
                    items = cart_response.json()
                    st.markdown(f"##### Cart Items for: {user_detail['firstName']} {user_detail['lastName']}")
                    if items:
                        # Convert the JSON to a DataFrame
                        df = pd.DataFrame(items)

                        # Rename columns if they exist
                        rename_map = {}
                        if "productId" in df.columns:
                            rename_map["productId"] = "Product ID"
                        if "productName" in df.columns:
                            rename_map["productName"] = "Product Name"
                        if "quantity" in df.columns:
                            rename_map["quantity"] = "Quantity"
                        df.rename(columns=rename_map, inplace=True)

                        # Drop columns we do NOT want to display (e.g. 'id', 'userId')
                        for col_to_drop in ["id", "userId"]:
                            if col_to_drop in df.columns:
                                df.drop(col_to_drop, axis=1, inplace=True)

                        # Reset the DataFrame index to remove default row numbering
                        df.reset_index(drop=True, inplace=True)

                        # Display the table
                        st.table(df)
                    else:
                        st.info("No cart items found.")
                else:
                    st.error("Error fetching cart items: " + cart_response.text)
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

    # ------------------- ADD CART ITEM -------------------
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

    # ------------------- UPDATE CART ITEM -------------------
    elif action == "Update Cart Item":
        st.subheader("Update Cart Item Quantity")
        with st.form("update_cart_item_form"):
            item_id = st.text_input("Cart Item ID")
            new_quantity = st.number_input("New Quantity", min_value=1, step=1)
            submitted = st.form_submit_button("Update Cart Item")
            if submitted:
                if not item_id:
                    st.error("Please provide the Cart Item ID.")
                else:
                    payload = {"quantity": new_quantity}
                    try:
                        response = requests.put(f"{CART_SERVICE_URL}/cart/{item_id}", json=payload)
                        if response.status_code == 200:
                            st.success("Cart item updated successfully!")
                        else:
                            error_msg = response.json().get("error", response.text)
                            st.error(f"Error updating cart item: {error_msg}")
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")

    # ------------------- DELETE CART ITEM -------------------
    elif action == "Delete Cart Item":
        st.subheader("Delete Cart Item")
        with st.form("delete_cart_item_form"):
            item_id = st.text_input("Cart Item ID")
            submitted = st.form_submit_button("Delete Cart Item")
            if submitted:
                if not item_id:
                    st.error("Please provide the Cart Item ID.")
                else:
                    try:
                        response = requests.delete(f"{CART_SERVICE_URL}/cart/{item_id}")
                        if response.status_code == 200:
                            st.success("Cart item deleted successfully!")
                        else:
                            error_msg = response.json().get("error", response.text)
                            st.error(f"Error deleting cart item: {error_msg}")
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")

def main():
    run_cart_ui()

if __name__ == "__main__":
    main()