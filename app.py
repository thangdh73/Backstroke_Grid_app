import streamlit as st
import pandas as pd
import numpy as np
from scipy.interpolate import RegularGridInterpolator
import re
import os

def extract_stimp_feet(sheet_name):
    match = re.search(r"Stimp[_ ]?(\d+\.\d+)", sheet_name)
    if match:
        stimp_m = float(match.group(1))
        stimp_ft = stimp_m * 3.28084
        return stimp_ft
    return None

st.title("Backstroke Predictor (Uphill/Downhill & Stimp Selector)")

# --- Automatically load Excel from the repo (no upload) ---
EXCEL_PATH = "data/Extracted_Backstroke_Table.xlsx"
if not os.path.exists(EXCEL_PATH):
    st.error(f"Excel file not found at {EXCEL_PATH}. Please check your repo structure!")
    st.stop()

xl = pd.ExcelFile(EXCEL_PATH)
data_frames = {}
uphill_sheets = []
downhill_sheets = []
stimp_dict = {}

for sheet in xl.sheet_names:
    try:
        df = xl.parse(sheet, header=3)
        df = df.dropna(how='all')
        if 'Putt Length (m)' in df.columns:
            df = df.set_index('Putt Length (m)')
        if "uphill" in sheet.lower():
            uphill_sheets.append(sheet)
        elif "downhill" in sheet.lower():
            downhill_sheets.append(sheet)
        stimp_ft = extract_stimp_feet(sheet)
        if stimp_ft:
            stimp_dict[sheet] = round(stimp_ft,2)
        data_frames[sheet] = df
    except Exception as e:
        st.info(f"Sheet {sheet} skipped: {e}")

st.success(f"Loaded {len(data_frames)} sheets.")

direction = st.radio("Select Slope Direction", ["Uphill", "Downhill"], horizontal=True)
relevant_sheets = uphill_sheets if direction == "Uphill" else downhill_sheets

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

    # --- User inputs: putt length and slope % only ---
    putt_length = st.number_input("Putt Length (m)", min_value=0.5, max_value=20.0, value=3.0)
    slope_percent = st.number_input("Slope at ball position (%)", min_value=0.0, max_value=20.0, value=4.0)

    # --- Calculate elevation in cm ---
    elevation_cm = putt_length * slope_percent
    st.info(f"Calculated elevation: **{elevation_cm:.1f} cm** (for {putt_length:.2f}m at {slope_percent:.2f}%)")

    if st.button("Predict Backstroke Length"):
    df = data_frames[selected_sheet]
    try:
        row_vals = np.array(df.index, dtype=float)
        col_vals = np.array([float(str(c).replace('cm', '').replace(' ','')) for c in df.columns])
        grid = df.values.astype(float)
        interp = RegularGridInterpolator((row_vals, col_vals), grid)
        pred = interp([[putt_length, elevation_cm]])[0]
        pred_inch = pred / 2.54
        st.success(
            f"**Predicted Backstroke Length:** {pred:.2f} cm  \n"
            f"**( = {pred_inch:.2f} inches )**  \n"
            f"(Direction: {direction}, Stimp: {stimp_dict[selected_sheet]:.2f} ft, Elevation: {elevation_cm:.1f} cm)"
        )
    except Exception as e:
        st.error(f"Interpolation failed: {e}")
