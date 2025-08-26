import streamlit as st
import pandas as pd
from utils.charting import (
    render_line_chart,
    render_table,
    render_big_number,
    render_gauge,
    configure_chart_dialog
)

st.title("📊 Dashboard Preview")

# Retrieve the dataframe from session state
df = st.session_state.get('data', pd.DataFrame())

# Check if data is available
if df.empty:
    st.warning("Please upload a JSON file on the '🏠 Home' page first.", icon="👈")
    st.stop()

# --- Global Filters ---
st.header("Global Filters")
col1, col2, col3 = st.columns([2, 1, 1])

# Asset Type Filter
asset_types = df['asset_type'].unique().tolist()
global_selected_asset_type = col1.selectbox("Filter by Asset Type", ["All"] + asset_types)

# Date Range Filter
min_date = df['timestamp'].dt.date.min()
max_date = df['timestamp'].dt.date.max()

from_date = col2.date_input("From date", min_date, min_value=min_date, max_value=max_date)
to_date = col3.date_input("To date", max_date, min_value=min_date, max_value=max_date)

# Convert dates to timezone-aware datetimes for correct filtering
df_timezone = df['timestamp'].dt.tz
from_datetime = pd.Timestamp(from_date, tz=df_timezone)
# Include the entire 'to_date' by setting the time to the end of the day
to_datetime = pd.Timestamp(to_date, tz=df_timezone) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

st.markdown("---")

# --- Chart Configuration and Display ---
if st.button("➕ Add Chart", type="primary"):
    st.session_state.show_modal = True

if st.session_state.get('show_modal', False):
    # Pass the full, unfiltered dataframe to the dialog
    configure_chart_dialog(df)

charts = st.session_state.get('charts', [])

if not charts:
    st.info("Your dashboard is empty. Click '➕ Add Chart' to get started.")
else:
    # Use a two-column layout for the charts
    cols = st.columns(2)

    # Track which column to place the next chart in
    chart_index_to_render = 0

    # Iterate over a copy of the charts list to allow safe removal
    for i, config in enumerate(charts[:]):
        # Check if the chart should be displayed based on the global asset filter
        show_chart = (global_selected_asset_type == "All" or
                      global_selected_asset_type == config.get('asset_type'))

        if show_chart:
            # Filter data for the specific chart
            chart_df = df[
                (df['asset_type'] == config['asset_type']) &
                (df['timestamp'] >= from_datetime) &
                (df['timestamp'] <= to_datetime)
            ].copy()

            col_index = chart_index_to_render % 2
            with cols[col_index]:
                with st.container(border=True):
                    chart_key = f"chart_{i}"

                    # Render the correct chart type
                    if config['type'] == "Line Chart":
                        render_line_chart(chart_df, config, chart_key)
                    elif config['type'] == "Tabular Data":
                        render_table(chart_df, config, chart_key)
                    elif config['type'] == "Big Number":
                        render_big_number(chart_df, config, chart_key)
                    elif config['type'] == "Gauge":
                        render_gauge(chart_df, config, chart_key)

                    # Add a remove button for each chart
                    if st.button(f"Remove", key=f"remove_{i}", help="Remove this chart"):
                        st.session_state.charts.pop(i)
                        st.rerun()

            chart_index_to_render += 1

    if chart_index_to_render == 0 and global_selected_asset_type != "All":
        st.info(f"No charts configured for asset type '{global_selected_asset_type}'. Select 'All' to see every chart.")
