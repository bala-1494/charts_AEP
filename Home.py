import streamlit as st
import pandas as pd
from utils.data_processing import load_and_process_data

# --- Page Configuration ---
st.set_page_config(
    page_title="Dashboard Generator - Home",
    page_icon="🏠",
    layout="wide"
)

# --- Session State Initialization ---
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame()
if 'charts' not in st.session_state:
    st.session_state.charts = []
if 'show_modal' not in st.session_state:
    st.session_state.show_modal = False

# --- Main Page UI ---
st.title("📄 Upload Asset Data")
st.markdown(
    """
    Welcome to the Dynamic Dashboard Generator!

    **To get started:**
    1.  Upload a JSON file containing your asset data.
    2.  Once processed, navigate to the **Dashboard** page from the sidebar.
    3.  Build and customize your dashboard by adding charts.
    """
)

uploaded_file = st.file_uploader("Choose a JSON file", type="json")

if uploaded_file is not None:
    with st.spinner('Processing data...'):
        # When a new file is uploaded, process it and reset the dashboard
        st.session_state.data = load_and_process_data(uploaded_file)
        if not st.session_state.data.empty:
            st.session_state.charts = []  # Reset charts
            st.success("Data loaded successfully! Navigate to the 'Dashboard' page to view and create charts.")
            st.dataframe(st.session_state.data.head())
            st.write(f"Found **{len(st.session_state.data)}** records.")
