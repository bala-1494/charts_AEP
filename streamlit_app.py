import streamlit as st
import pandas as pd
import json
from streamlit_echarts import st_echarts
import datetime

# --- Page Configuration ---
st.set_page_config(
    page_title="Dynamic Dashboard Generator",
    page_icon="📊",
    layout="wide"
)

# --- Helper Functions ---

def load_and_process_data(uploaded_file):
    """
    Loads data from the uploaded JSON file, flattens it, and processes it into a DataFrame.
    """
    if uploaded_file is None:
        return pd.DataFrame()

    try:
        data = json.load(uploaded_file)
        records = []
        for entry in data:
            flat_record = {
                'pld': entry.get('pld'),
                'asset_type': entry.get('asset_type'),
                'timestamp': entry.get('timestamp')
            }
            if 'parameters' in entry and isinstance(entry['parameters'], dict):
                flat_record.update(entry['parameters'])
            records.append(flat_record)

        df = pd.DataFrame(records)
        if 'timestamp' not in df.columns:
            st.error("The uploaded JSON must contain a 'timestamp' field in each record.")
            return pd.DataFrame()

        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce', utc=True)
        df.dropna(subset=['timestamp'], inplace=True)
        return df
    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")
        return pd.DataFrame()

# --- Chart Rendering Functions ---

def render_line_chart(df, config, key):
    """Renders a line chart using ECharts."""
    st.subheader(f"Line Chart: {config['parameter']} ({config['asset_type']})")
    if config['display_mode'] == 'Individual':
        series_data = []
        for pld_id, group in df.groupby('pld'):
            group = group.sort_values('timestamp')
            chart_data = [[row['timestamp'].isoformat(), row[config['parameter']]] for _, row in group.iterrows()]
            series_data.append({
                "name": pld_id, "type": 'line', "data": chart_data, "showSymbol": False,
            })
        legend_data = df['pld'].unique().tolist()
    else:
        agg_func = config['aggregation']
        grouped_df = df.groupby(pd.Grouper(key='timestamp', freq='D'))[config['parameter']].agg(agg_func).reset_index()
        grouped_df['timestamp'] = grouped_df['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        series_data = [{
            "name": f"{config['parameter']} ({agg_func})", "type": 'line', "data": grouped_df.values.tolist(), "showSymbol": False,
        }]
        legend_data = [f"{config['parameter']} ({agg_func})"]

    options = {
        "tooltip": {"trigger": 'axis'}, "legend": {"data": legend_data, "bottom": 10},
        "xAxis": {"type": 'time'}, "yAxis": {"type": 'value'}, "series": series_data,
        "dataZoom": [{"type": 'inside'}, {"type": 'slider'}]
    }
    st_echarts(options=options, height="400px", key=f"line_{key}")

def render_table(df, config, key):
    """Renders a data table."""
    st.subheader(f"Tabular Data ({config['asset_type']})")
    display_cols = ['timestamp', 'pld'] + [col for col in config['parameters'] if col in df.columns]
    st.dataframe(df[display_cols], use_container_width=True)

def render_big_number(df, config, key):
    """Renders a big number metric."""
    st.subheader(f"Big Number: {config['parameter']} ({config['asset_type']})")
    if not df.empty and config['parameter'] in df.columns:
        latest_df = df.sort_values('timestamp').groupby('pld').last().reset_index()
        value = latest_df[config['parameter']].sum() if config['aggregation'] == 'sum' else latest_df[config['parameter']].mean()
        st.metric(label=f"Total {config['parameter']} ({config['aggregation']})", value=f"{value:,.2f}")
    else:
        st.metric(label=f"Total {config['parameter']} ({config['aggregation']})", value="N/A")

def render_gauge(df, config, key):
    """Renders a gauge chart for a specific asset."""
    st.subheader(f"Gauge: {config['parameter']} ({config['asset_type']})")
    pld_list = df['pld'].unique().tolist()
    if not pld_list:
        st.warning("No assets of the selected type found in the date range.")
        return

    selected_pld = st.selectbox("Select Asset ID (pld) to view:", pld_list, key=f"gauge_pld_{key}")
    if selected_pld:
        asset_df = df[df['pld'] == selected_pld].sort_values('timestamp')
        if not asset_df.empty and config['parameter'] in asset_df.columns:
            latest_value = asset_df.iloc[-1][config['parameter']]
            options = {
                "series": [{"type": 'gauge', "detail": {"formatter": '{value}'},
                            "data": [{"value": latest_value, "name": config['parameter']}],
                            "min": config.get('min_val', 0), "max": config.get('max_val', 100),
                            "axisLine": {"lineStyle": {"width": 20, "color": [[0.3, '#67e0e3'], [0.7, '#37a2da'], [1, '#fd666d']]}}
                           }]
            }
            st_echarts(options=options, height="300px", key=f"gauge_{key}")
        else:
            st.info(f"No data available for asset {selected_pld} in the selected time range.")

def configure_chart_dialog(df):
    """Displays the chart configuration dialog and returns the config."""
    with st.dialog("Configure New Chart"):
        asset_types = df['asset_type'].unique().tolist()
        chart_config = {}

        modal_asset_type = st.selectbox("Select Asset Type for this Chart", asset_types)
        chart_config['asset_type'] = modal_asset_type

        modal_df = df[df['asset_type'] == modal_asset_type]
        numeric_cols = modal_df.select_dtypes(include=['number']).columns.tolist()
        all_cols = modal_df.columns.tolist()

        chart_type = st.selectbox("Select Chart Type", ["Line Chart", "Tabular Data", "Big Number", "Gauge"])
        chart_config['type'] = chart_type

        if chart_type == "Line Chart":
            chart_config['parameter'] = st.selectbox("Select Parameter", numeric_cols)
            chart_config['display_mode'] = st.radio("Display Mode", ["Individual", "Grouped"])
            if chart_config['display_mode'] == 'Grouped':
                chart_config['aggregation'] = st.radio("Aggregation", ["sum", "mean"], horizontal=True)
        elif chart_type == "Tabular Data":
            chart_config['parameters'] = st.multiselect("Select Parameters to Display", all_cols)
        elif chart_type == "Big Number":
            chart_config['parameter'] = st.selectbox("Select Parameter", numeric_cols)
            chart_config['aggregation'] = st.radio("Aggregation", ["sum", "mean"], horizontal=True)
        elif chart_type == "Gauge":
            chart_config['parameter'] = st.selectbox("Select Parameter", numeric_cols)
            c1, c2 = st.columns(2)
            chart_config['min_val'] = c1.number_input("Minimum Value", value=0)
            chart_config['max_val'] = c2.number_input("Maximum Value", value=100)

        if st.button("Add to Dashboard"):
            st.session_state.charts.append(chart_config)
            st.session_state.show_modal = False
            st.rerun()

# --- Main Application ---
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame()
if 'charts' not in st.session_state:
    st.session_state.charts = []
if 'show_modal' not in st.session_state:
    st.session_state.show_modal = False

st.sidebar.title("Navigation")
menu_choice = st.sidebar.radio("Go to", ["Upload JSON", "Dashboard Preview"])

if menu_choice == "Upload JSON":
    st.title("📄 Upload Asset Data")
    st.markdown("Upload a JSON file containing asset data to begin generating your dashboard.")
    uploaded_file = st.file_uploader("Choose a JSON file", type="json")
    if uploaded_file is not None:
        with st.spinner('Processing data...'):
            st.session_state.data = load_and_process_data(uploaded_file)
            if not st.session_state.data.empty:
                st.success("Data loaded successfully!")
                st.dataframe(st.session_state.data.head())
                st.write(f"Found **{len(st.session_state.data)}** records.")
                st.session_state.charts = []

elif menu_choice == "Dashboard Preview":
    st.title("📊 Dashboard Preview")
    df = st.session_state.data
    if df.empty:
        st.warning("Please upload a JSON file first using the 'Upload JSON' page.", icon="👈")
    else:
        st.header("Global Filters")
        col1, col2, col3 = st.columns([2, 1, 1])
        asset_types = df['asset_type'].unique().tolist()
        global_selected_asset_type = col1.selectbox("Select Asset Type to View", ["All"] + asset_types)

        min_date = df['timestamp'].dt.date.min()
        max_date = df['timestamp'].dt.date.max()
        from_date = col2.date_input("From date", min_date, min_value=min_date, max_value=max_date)
        to_date = col3.date_input("To date", max_date, min_value=min_date, max_value=max_date)

        df_timezone = df['timestamp'].dt.tz
        from_datetime = pd.Timestamp(from_date, tz=df_timezone)
        to_datetime = pd.Timestamp(to_date, tz=df_timezone) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

        st.markdown("---")

        if st.button("➕ Add Chart", type="primary"):
            st.session_state.show_modal = True

        if st.session_state.show_modal:
            configure_chart_dialog(df)

        if not st.session_state.charts:
            st.info("Your dashboard is empty. Click 'Add Chart' to get started.")
        else:
            cols = st.columns(2)
            chart_index_to_render = 0
            for i, config in enumerate(st.session_state.charts):
                show_chart = (global_selected_asset_type == "All" or global_selected_asset_type == config['asset_type'])
                if show_chart:
                    chart_df = df[(df['asset_type'] == config['asset_type']) & (df['timestamp'] >= from_datetime) & (df['timestamp'] <= to_datetime)].copy()
                    col_index = chart_index_to_render % 2
                    with cols[col_index]:
                        with st.container(border=True):
                            chart_key = f"chart_{i}"
                            if config['type'] == "Line Chart": render_line_chart(chart_df, config, chart_key)
                            elif config['type'] == "Tabular Data": render_table(chart_df, config, chart_key)
                            elif config['type'] == "Big Number": render_big_number(chart_df, config, chart_key)
                            elif config['type'] == "Gauge": render_gauge(chart_df, config, chart_key)
                            if st.button(f"Remove Chart {i+1}", key=f"remove_{i}"):
                                st.session_state.charts.pop(i)
                                st.rerun()
                    chart_index_to_render += 1
