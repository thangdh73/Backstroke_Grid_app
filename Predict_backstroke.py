import streamlit as st
import pandas as pd
import numpy as np
from scipy.interpolate import RegularGridInterpolator
import io
import re

def extract_stimp_feet(sheet_name):
    """Extract Stimp value in meters from sheet name, convert to feet"""
    match = re.search(r"Stimp[_ ]?(\d+\.\d+)", sheet_name)
    if match:
        stimp_m = float(match.group(1))
        stimp_ft = stimp_m * 3.28084
        return stimp_ft
    return None

st.title("Backstroke Predictor (Uphill/Downhill & Stimp Selector)")

uploaded_file = st.file_uploader("Upload Extracted_Backstroke_Table Excel", type=["xlsx"])
if uploaded_file:
    excel_bytes = uploaded_file.read()
    xl = pd.ExcelFile(io.BytesIO(excel_bytes))
    data_frames = {}
    uphill_sheets = []
    downhill_sheets = []
    stimp_dict = {}  # (sheet: stimp_ft)

    # Gather sheet information
    for sheet in xl.sheet_names:
        try:
            df = xl.parse(sheet, header=3)
            df = df.dropna(how='all')
            if 'Putt Length (m)' in df.columns:
                df = df.set_index('Putt Length (m)')
            # Classify as uphill/downhill
            if "uphill" in sheet.lower():
                uphill_sheets.append(sheet)
            elif "downhill" in sheet.lower():
                downhill_sheets.append(sheet)
            # Save stimp value (in ft) for display
            stimp_ft = extract_stimp_feet(sheet)
            if stimp_ft:
                stimp_dict[sheet] = round(stimp_ft,2)
            data_frames[sheet] = df
        except Exception as e:
            st.info(f"Sheet {sheet} skipped: {e}")

    st.success(f"Loaded {len(data_frames)} sheets.")

    # --- User selections ---
    direction = st.radio("Select Slope Direction", ["Uphill", "Downhill"], horizontal=True)
    relevant_sheets = uphill_sheets if direction == "Uphill" else downhill_sheets

    # Group by Stimp for display
    stimp_options = []
    for s in relevant_sheets:
        stimp = stimp_dict.get(s, None)
        if stimp:
            label = f"Stimp {stimp:.2f} ft ({s})"
            stimp_options.append((label, s))
    if not stimp_options:
        st.warning("No matching sheets found for selected direction.")
    else:
        stimp_label, selected_sheet = st.selectbox(
            "Select Green Speed (Stimp ft):",
            options=stimp_options,
            format_func=lambda x: x[0]
        )

        # Prediction inputs
        putt_length = st.number_input("Putt Length (m)", min_value=0.5, max_value=20.0, value=3.0)
        slope_elevation = st.number_input("Slope Elevation (cm)", min_value=0.0, max_value=50.0, value=5.0)

        if st.button("Predict Backstroke Length"):
            df = data_frames[selected_sheet]
            try:
                row_vals = np.array(df.index, dtype=float)
                col_vals = np.array([float(str(c).replace('cm', '').replace(' ','')) for c in df.columns])
                grid = df.values.astype(float)
                interp = RegularGridInterpolator((row_vals, col_vals), grid)
                pred = interp([[putt_length, slope_elevation]])[0]
                st.success(
                    f"Predicted Backstroke Length: {pred:.2f} cm "
                    f"(Direction: {direction}, Stimp: {stimp_dict[selected_sheet]:.2f} ft)"
                )
            except Exception as e:
                st.error(f"Interpolation failed: {e}")

else:
    st.info("Upload your Excel file above to begin.")
