# to start run from CLI: streamlit run ./ui/user_ui.py

import streamlit as st
import requests

# Base URL for your Flask User service
BASE_URL = "http://127.0.0.1:5000"

# Sidebar menu for navigation
menu_option = st.sidebar.radio("Menu", ["Users List", "Add New User", "Remove User", "Update User"])

if menu_option == "Add New User":
    st.title("Add New User")
    with st.form("add_user_form"):
        first_name = st.text_input("First Name")
        last_name = st.text_input("Last Name")
        user_alias = st.text_input("User Alias")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Add User")
        if submitted:
            payload = {
                "firstName": first_name,
                "lastName": last_name,
                "userAlias": user_alias,
                "password": password
            }
            response = requests.post(f"{BASE_URL}/users", json=payload)
            if response.status_code == 201:
                st.success("User added successfully!")
            else:
                st.error("Error adding user: " + response.text)

elif menu_option == "Users List":
    st.title("User List")
    #if st.button("Refresh User List"):
    response = requests.get(f"{BASE_URL}/users")
    if response.status_code == 200:
            users = response.json()
            if users:
                #st.table(users)
                import pandas as pd
                # Specify columns in the desired order
                df = pd.DataFrame(users, columns=['id', 'firstName', 'lastName', 'userAlias'])
                st.table(df)
            else:
                st.info("No users found.")
    else:
        st.error("Error fetching users: " + response.text)

elif menu_option == "Remove User":
    st.title("Remove User")
    with st.form("remove_user_form"):
        first_name = st.text_input("First Name")
        last_name = st.text_input("Last Name")
        submitted = st.form_submit_button("Remove User")
        if submitted:
            payload = {"firstName": first_name, "lastName": last_name}
            response = requests.delete(f"{BASE_URL}/users", json=payload)
            if response.status_code == 200:
                st.success("User removed successfully!")
            else:
                st.error("Error removing user: " + response.text)

elif menu_option == "Update User":
    st.title("Update User")
    with st.form("update_user_form"):
        user_id = st.text_input("User ID")
        first_name = st.text_input("New First Name")
        last_name = st.text_input("New Last Name")
        user_alias = st.text_input("New User Alias")
        password = st.text_input("New Password (optional)", type="password")
        submitted = st.form_submit_button("Update User")
        if submitted:
            # Validate that user ID is an integer
            try:
                user_id_int = int(user_id)
            except ValueError:
                st.error("User ID must be a number")
            else:
                payload = {
                    "id": user_id_int,
                    "firstName": first_name,
                    "lastName": last_name,
                    "userAlias": user_alias
                }
                if password:
                    payload["password"] = password
                response = requests.put(f"{BASE_URL}/users", json=payload)
                if response.status_code == 200:
                    st.success("User updated successfully!")
                else:
                    st.error("Error updating user: " + response.text)