import streamlit as st
import pandas as pd
from streamlit_echarts import st_echarts

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
