import os
import re
import pandas as pd
from pyproj import Transformer
from pathlib import Path

# ==========================================
# 1. PATH DEFINITIONS
# ==========================================
#######################################################################
SSD = "F"
AREA = "01_Rajrajeshwar"
AREABASE = "Base_20261107"
AREAN = "Area1"
LOC = "Loc_01_20261106"
LOCN = "Loc1_20261106"
SUMFILE_LOC = "3375201310F5.sum"

# Known Coordinates for Base 1 Validation (Pillar GPS 5692)
KNOWN_E = 247305.0956
KNOWN_N = 2568141.6390
KNOWN_MSL = 3.3640
#####################################################################

# Processed Output Directory (ALL outputs will go here)
DIR_PPP_OUT = Path(fr"{SSD}:\Meghna_UAV_Campaign_2026\{AREA}\{LOC}\04_Processed_PPP")

# Reference Point (Base 1) - Read Only
DIR_BASE_1 = Path(fr"{SSD}:\Meghna_UAV_Campaign_2026\{AREA}\{AREABASE}")
SUM_BASE_1 = DIR_BASE_1 / f"{AREABASE}_Combined.sum"

# Local Field Base (Base Static) - Read Only
DIR_BASE_LOCAL = Path(fr"{SSD}:\Meghna_UAV_Campaign_2026\{AREA}\{LOC}\02_Raw_GNSS_Survey\Base_Static")
SUM_BASE_LOCAL = DIR_BASE_LOCAL / f"{SUMFILE_LOC}"

# Rover GCPs - Read Only
CSV_ROVER_IN = Path(fr"{SSD}:\Meghna_UAV_Campaign_2026\{AREA}\{LOC}\02_Raw_GNSS_Survey\Rover_GCPs\{AREAN}_{LOCN}.csv")

# Output Files (Routed to 04_Processed_PPP)
CSV_ROVER_OUT = DIR_PPP_OUT / f"{LOC}_coor.csv"
METRICS_OUT = DIR_PPP_OUT / f"{AREABASE}_accuracy_metrics.txt"

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def parse_csrs_ppp_summary(filepath):
    """Extracts Easting, Northing, and Ellipsoid Height from CSRS-PPP .pos/.sum file"""
    data = {}
    with open(filepath, 'r') as file:
        content = file.read()
        
        # Matches the PRJ line for UTM Easting (Group 1) and Northing (Group 2)
        utm_match = re.search(r"PRJ\s+UTM\s+\d+\s+([-\d\.]+)\s+([-\d\.]+)", content)
        # Matches the POS HGT line for Ellipsoidal Height (Group 1)
        hgt_match = re.search(r"POS\s+HGT\s+\w+\s+[\d:]+\s+[-\d\.]+\s+([-\d\.]+)", content)
        # Matches Orthometric Height if available
        ortho_match = re.search(r"OHT\s+\w+\s+\w+\s+([-\d\.]+)", content)
        
        if utm_match: 
            data['E'] = float(utm_match.group(1))
            data['N'] = float(utm_match.group(2))
        if hgt_match: 
            data['H_ellips'] = float(hgt_match.group(1))
        if ortho_match: 
            data['H_ortho'] = float(ortho_match.group(1))
            
    return data

def clean_latlon(val):
    """Removes N/E letters from coordinates and converts to float"""
    if isinstance(val, str):
        val = val.replace('N', '').replace('E', '').strip()
    return float(val)

# ==========================================
# 3. MAIN EXECUTION
# ==========================================
def main():
    # Ensure processed output directory exists without modifying raw folders
    DIR_PPP_OUT.mkdir(parents=True, exist_ok=True)
    
    # Transformer: WGS84 Lat/Lon (EPSG:4326) to UTM 46N (EPSG:32646)
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32646", always_xy=True)

    print("--- 1. Processing Reference Base (Accuracy Validation) ---")
    if SUM_BASE_1.exists():
        ppp_b1 = parse_csrs_ppp_summary(SUM_BASE_1)
        
        diff_E = ppp_b1['E'] - KNOWN_E
        diff_N = ppp_b1['N'] - KNOWN_N
        diff_MSL = ppp_b1.get('H_ortho', 0) - KNOWN_MSL
        
        metrics_text = (
            f"CSRS-PPP Validation Metrics for GPS 5692\n"
            f"----------------------------------------\n"
            f"Known Easting : {KNOWN_E:.4f} m\n"
            f"PPP Easting   : {ppp_b1['E']:.4f} m\n"
            f"Difference (E): {diff_E:+.4f} m\n\n"
            f"Known Northing: {KNOWN_N:.4f} m\n"
            f"PPP Northing  : {ppp_b1['N']:.4f} m\n"
            f"Difference (N): {diff_N:+.4f} m\n\n"
            f"Known MSL Hgt : {KNOWN_MSL:.4f} m\n"
            f"PPP MSL Hgt   : {ppp_b1.get('H_ortho', 'N/A')} m\n"
            f"Difference (H): {diff_MSL:+.4f} m\n"
        )
        with open(METRICS_OUT, "w") as f:
            f.write(metrics_text)
        print(f"Validation metrics saved to: {METRICS_OUT}")
    else:
        print(f"File not found: {SUM_BASE_1}. Skipping validation.")

    print("\n--- 2. Processing Local Field Base & Shifting GCPs ---")
    if SUM_BASE_LOCAL.exists() and CSV_ROVER_IN.exists():
        ppp_local = parse_csrs_ppp_summary(SUM_BASE_LOCAL)
        
        # Read the CSV file without headers (since it starts immediately with data)
        df = pd.read_csv(CSV_ROVER_IN, header=None, names=['PointID', 'Lat', 'Lon', 'Elevation'])
        
        # Clean the letters off the Lat/Lon
        df['Lat'] = df['Lat'].apply(clean_latlon)
        df['Lon'] = df['Lon'].apply(clean_latlon)
        
        # Project all rows to UTM 46N (always_xy expects Lon, Lat)
        df['Easting'], df['Northing'] = transformer.transform(df['Lon'].values, df['Lat'].values)
        
        # Extract the temporary field coordinate of the Base (Assumed to be the first row 'base_1')
        base_row = df.iloc[0]
        field_E = base_row['Easting']
        field_N = base_row['Northing']
        field_H = base_row['Elevation']
        
        # Calculate the 3D Translation Vector
        shift_E = ppp_local['E'] - field_E
        shift_N = ppp_local['N'] - field_N
        shift_H = ppp_local['H_ellips'] - field_H
        
        print(f"Calculated Shift -> E: {shift_E:+.4f}m, N: {shift_N:+.4f}m, H: {shift_H:+.4f}m")
        
        # Apply shift to the Rover points (skip the first row which is the base itself)
        gcp_df = df.iloc[1:].copy()
        gcp_df['Easting_Shifted'] = (gcp_df['Easting'] + shift_E).round(4)
        gcp_df['Northing_Shifted'] = (gcp_df['Northing'] + shift_N).round(4)
        gcp_df['Elevation_Shifted'] = (gcp_df['Elevation'] + shift_H).round(4)
        
        # Select final columns for Metashape export
        final_out = gcp_df[['PointID', 'Easting_Shifted', 'Northing_Shifted', 'Elevation_Shifted']]
        final_out.columns = ['PointID', 'Easting', 'Northing', 'Elevation']
        
        # Save to Processed_PPP folder
        final_out.to_csv(CSV_ROVER_OUT, index=False)
        print(f"Successfully saved corrected GCPs to: {CSV_ROVER_OUT}")
    else:
        print(f"Missing files for GCP shift. Check paths for {SUM_BASE_LOCAL} or {CSV_ROVER_IN}.")

if __name__ == "__main__":
    main()