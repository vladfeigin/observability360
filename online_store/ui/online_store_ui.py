#import the library loading env variables from .env

from dotenv import load_dotenv
import streamlit as st
from user_ui import run_user_ui
from product_ui import run_product_ui

load_dotenv()

st.set_page_config(page_title="Online Store UI", layout="wide")
st.title("Online Store Dashboard")

# Sidebar navigation: select a service section
service = st.sidebar.radio("Select Service", 
                           ["Home", "User Service", "Product Service", "Order Service", "Cart Service"])

if service == "Home":
    st.header("Welcome")
    st.write("Select a service from the sidebar to manage it.")
elif service == "User Service":
    run_user_ui()
elif service == "Product Service":
    run_product_ui()
    
