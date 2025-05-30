# this is central ui for the online store
import os
import sys
import streamlit as st
from dotenv import load_dotenv

# Get the directory of the current file: online_store/ui/
current_dir = os.path.dirname(__file__)
# Go two levels up to reach the project root (observability360)
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    
from online_store.otel.otel import configure_telemetry
from db_init import initialize_db
from order_ui import run_order_ui
from cart_ui import run_cart_ui
from product_ui import run_product_ui
from user_ui import run_user_ui

SERVICE_VERSION = "1.0.0"
instruments = configure_telemetry(None, "Online Store UI", SERVICE_VERSION)

# Get instruments
tracer = instruments["tracer"]
logger = instruments["logger"]

load_dotenv()

database_path = os.path.join(project_root, "online_store/db/online_store.db")
sql_init_file = os.path.join(project_root, "online_store/ui/populate_products.sql")

logger.info(f"DB Path: {database_path}")
logger.info(f"SQL Init File: {sql_init_file}")

# (Optional) Initialize DB
# initialize_db(database_path, sql_init_file)

st.set_page_config(page_title="Online Store UI", layout="wide")

# ---------------------------------------------------------------------
# Title and Subheader
# ---------------------------------------------------------------------
st.title("Observability Demo.")
st.markdown("##### This observability demo showcases how to leverage the full power of "
    "OpenTelemetry to collect logs, metrics, and traces across multiple services. "
    "The system integrates with Azure Data Explorer (Kusto), Jaeger, and Grafana, providing "
    "end-to-end visibility into user, product, cart, and order microservices in the online store."
)
st.subheader("",divider="blue")

# ---------------------------------------------------------------------
# Center and Enlarge the Eye SVG with the Kusto Icon in the Pupil
# ---------------------------------------------------------------------
svg_logo_centered = """
<div style="display: flex; justify-content: center; align-items: center; margin: 20px 0;">
<svg width="500" height="250" viewBox="0 0 300 150" xmlns="http://www.w3.org/2000/svg">
  <!-- Eye shape -->
  <path d="M20,75 C80,10 220,10 280,75 C220,140 80,140 20,75 Z" 
        fill="#0000ff" stroke="#005A9E" stroke-width="2"/>
  <!-- Enlarged white circle (pupil) -->
  <circle cx="150" cy="75" r="40" fill="#006400 />
  <!-- Extended pulse line spanning from left to right of the eye -->
  <polyline points="20,75 50,65 80,85 110,60 140,75 170,83 200,65 230,80 260,70 280,75" 
            stroke="#ffdd00" stroke-width="2" fill="none"/>
  <polyline points="25,80 45,75 90,75 100,55 135,65 175,85 205,55 235,70 265,75 280,75"
            stroke="#00ff00" stroke-width="2" fill="none"/>       
  <polyline points="30,85 50,80 95,85 120,65 145,85 185,95 215,75 240,85 270,75 280,75"
            stroke="#ff0000" stroke-width="2" fill="none"/>       
  <!-- Kusto Icon in the white circle -->
  <g transform="translate(140,65)"> <!-- CHANGED: Adjusted translate values to keep icon centered -->
    <!-- Kusto Icon background: a blue circle -->
    <circle cx="12" cy="12" r="15" fill="#009900"/>
    <!-- White "K" centered in the icon -->
    <text x="12" y="15" text-anchor="middle" alignment-baseline="middle" 
          font-family="Arial" font-size="16" font-weight="bold" fill="#ffff00">
      K
    </text>
  </g>
</svg>
</div>
"""

st.markdown(svg_logo_centered, unsafe_allow_html=True)

# ---------------------------------------------------------------------
# Sidebar Navigation
# ---------------------------------------------------------------------
service = st.sidebar.radio(
    "Select Service",
    ["Home", "User Service", "Product Service", "Cart Service", "Order Service"]
)

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