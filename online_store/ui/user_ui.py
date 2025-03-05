import os
import streamlit as st
import requests
import pandas as pd
from online_store.otel.otel import configure_telemetry, trace_span

SERVICE_VERSION = "1.0.0"
instruments = configure_telemetry(None, "User UI", SERVICE_VERSION)

# Get instruments
tracer = instruments["tracer"]

# Use environment variable with a fallback default (adjust port as needed)
BASE_URL = os.environ.get('USER_SERVICE_URL', 'http://127.0.0.1:5000')
@trace_span("run_user_ui", tracer)
def run_user_ui():
    
    st.header("User Service")
    action = st.selectbox("Select Action", ["Select...", "User List", "Add New User", "Update User", "Remove User", ], index=0)
    
    if action == "Select...":
        st.info("Please select an action from the dropdown.")
        return
    
    if action == "Add New User":
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
                response = requests.post(f"{BASE_URL}/users", json=payload,timeout=10)
                if response.status_code == 201:
                    st.success("User added successfully!")
                else:
                    st.error("Error adding user: " + response.text)

    elif action == "User List":
        #if st.button("Refresh User List"):
            response = requests.get(f"{BASE_URL}/users", timeout=10)
            if response.status_code == 200:
                users = response.json()
                if users:
                    df = pd.DataFrame(users, columns=['id', 'firstName', 'lastName', 'userAlias'])
                    st.markdown(df.to_html(index=False), unsafe_allow_html=True)
                else:
                    st.info("No users found.")
            else:
                st.error("Error fetching users: " + response.text)

    elif action == "Remove User":
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

    elif action == "Update User":
        with st.form("update_user_form"):
            user_id = st.text_input("User ID")
            first_name = st.text_input("New First Name")
            last_name = st.text_input("New Last Name")
            user_alias = st.text_input("New User Alias")
            password = st.text_input("New Password (optional)", type="password")
            submitted = st.form_submit_button("Update User")
            if submitted:
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