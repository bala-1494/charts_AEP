import pandas as pd
import json
import streamlit as st

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
