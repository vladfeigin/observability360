# thi is central ui for the online store
import os
import sys

# Get the directory of the current file: online_store/ui/
current_dir = os.path.dirname(__file__)
# Go two levels up to reach the project root (observability360)
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
import streamlit as st
from user_ui import run_user_ui
from product_ui import run_product_ui
from cart_ui import run_cart_ui
from order_ui import run_order_ui

load_dotenv()

st.set_page_config(page_title="Online Store UI", layout="wide")
st.title("Observability Demo.")

svg_logo = """
<svg width="300" height="150" viewBox="0 0 300 150" xmlns="http://www.w3.org/2000/svg">
  <!-- Eye shape -->
  <path d="M20,75 C80,10 220,10 280,75 C220,140 80,140 20,75 Z" 
        fill="#007ACC" stroke="#005A9E" stroke-width="2"/>
  <!-- Enlarged white circle (pupil) -->
  <circle cx="150" cy="75" r="30" fill="#ffffff" />
  <!-- Extended pulse line spanning from left to right of the eye -->
  <polyline points="20,75 50,65 80,85 110,60 140,75 170,90 200,65 230,80 260,70 280,75" 
            stroke="#ffdd00" stroke-width="3" fill="none"/>
  <!-- Letter K centered in the white circle -->
  <text x="150" y="75" text-anchor="middle" alignment-baseline="middle" 
        font-family="Arial" font-size="24" font-weight="bold" fill="#000000">
    K
  </text>
</svg>
"""

st.markdown(svg_logo, unsafe_allow_html=True)

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
    
