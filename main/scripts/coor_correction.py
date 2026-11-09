import os
import re
import pandas as pd
from pyproj import Transformer
from pathlib import Path

# ==========================================
# 1. PATH DEFINITIONS
# ==========================================
SSD = "F"
AREA = "01_Rajrajeshwar"
AREAN = "Area1"
LOC = "Loc_02_20261109"
LOCN = "Loc2_20261109"
SUMFILE_LOC = "20261109_Combined.sum"

# Processed Output Directory
DIR_PPP_OUT = Path(fr"{SSD}:\Meghna_UAV_Campaign_2026\{AREA}\{LOC}\04_Processed_PPP")

# Local Field Base (Base Static)
DIR_BASE_LOCAL = Path(fr"{SSD}:\Meghna_UAV_Campaign_2026\{AREA}\{LOC}\02_Raw_GNSS_Survey\Base_Static")
SUM_BASE_LOCAL = DIR_BASE_LOCAL / f"{SUMFILE_LOC}"

# Rover GCPs
CSV_ROVER_IN = Path(fr"{SSD}:\Meghna_UAV_Campaign_2026\{AREA}\{LOC}\02_Raw_GNSS_Survey\Rover_GCPs\{AREAN}_{LOCN}.csv")
CSV_ROVER_OUT = DIR_PPP_OUT / f"{LOC}_coor.csv"

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def parse_csrs_ppp_summary(filepath):
    """Extracts Easting, Northing, and Ellipsoid Height from CSRS-PPP .pos/.sum file"""
    data = {}
    with open(filepath, 'r') as file:
        content = file.read()
        utm_match = re.search(r"PRJ\s+UTM\s+\d+\s+([-\d\.]+)\s+([-\d\.]+)", content)
        hgt_match = re.search(r"POS\s+HGT\s+\w+\s+[\d:]+\s+[-\d\.]+\s+([-\d\.]+)", content)
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
    DIR_PPP_OUT.mkdir(parents=True, exist_ok=True)
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32646", always_xy=True)

    print("--- Processing Local Field Base & Shifting GCPs ---")
    if SUM_BASE_LOCAL.exists() and CSV_ROVER_IN.exists():
        ppp_local = parse_csrs_ppp_summary(SUM_BASE_LOCAL)
        
        df = pd.read_csv(CSV_ROVER_IN, header=None, names=['PointID', 'Lat', 'Lon', 'Elevation'])
        df['Lat'] = df['Lat'].apply(clean_latlon)
        df['Lon'] = df['Lon'].apply(clean_latlon)
        df['Easting'], df['Northing'] = transformer.transform(df['Lon'].values, df['Lat'].values)
        
        # Extract temporary field coordinate of the Base
        base_row = df.iloc[0]
        field_E = base_row['Easting']
        field_N = base_row['Northing']
        field_H = base_row['Elevation']
        
        # Calculate the 3D Translation Vector
        shift_E = ppp_local['E'] - field_E
        shift_N = ppp_local['N'] - field_N
        shift_H = ppp_local['H_ellips'] - field_H
        
        print(f"Calculated Shift -> E: {shift_E:+.4f}m, N: {shift_N:+.4f}m, H: {shift_H:+.4f}m")
        
        # Apply shift to Rover points
        gcp_df = df.iloc[1:].copy()
        gcp_df['Easting_Shifted'] = (gcp_df['Easting'] + shift_E).round(4)
        gcp_df['Northing_Shifted'] = (gcp_df['Northing'] + shift_N).round(4)
        gcp_df['Elevation_Shifted'] = (gcp_df['Elevation'] + shift_H).round(4)
        
        final_out = gcp_df[['PointID', 'Easting_Shifted', 'Northing_Shifted', 'Elevation_Shifted']]
        final_out.columns = ['PointID', 'Easting', 'Northing', 'Elevation']
        
        final_out.to_csv(CSV_ROVER_OUT, index=False)
        print(f"Successfully saved corrected GCPs to: {CSV_ROVER_OUT}")
    else:
        print(f"Missing files for GCP shift. Check paths for {SUM_BASE_LOCAL} or {CSV_ROVER_IN}.")

if __name__ == "__main__":
    main()