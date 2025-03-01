# thi is central ui for the online store

from dotenv import load_dotenv
import streamlit as st
from user_ui import run_user_ui
from product_ui import run_product_ui
from cart_ui import run_cart_ui
from order_ui import run_order_ui

load_dotenv()

st.set_page_config(page_title="Online Store UI", layout="wide")
st.title("Online Store. Observability Demo.")

# Sidebar navigation: select a service section
service = st.sidebar.radio("Select Service", 
                           ["Home", "User Service", "Product Service", "Cart Service", "Order Service", ])

if service == "Home":
    st.header("Welcome to the Online Store!")
    st.write("Select a service from the sidebar.")
elif service == "User Service":
    run_user_ui()
elif service == "Product Service":
    run_product_ui()
elif service == "Cart Service":
    run_cart_ui()
elif service == "Order Service":
    run_order_ui()
    
