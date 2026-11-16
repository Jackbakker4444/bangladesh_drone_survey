import os
import re
import pandas as pd
import matplotlib.pyplot as plt
from pyproj import Transformer
from pathlib import Path

# Optional basemap import fallback
try:
    import contextily as cx
    HAS_CONTEXTILY = True
except ImportError:
    HAS_CONTEXTILY = False

# ==========================================
# 1. PATH DEFINITIONS
# ==========================================
SSD = "F"
AREA = "02_Haimchar"
AREAN = "Area2"
LOC = "Loc_04_20261116"
LOCN = "Loc4_20261116"

# Processed Output Directory
DIR_PPP_OUT = Path(fr"{SSD}:\Meghna_UAV_Campaign_2026\{AREA}\{LOC}\04_Processed_PPP")

# Local Field Base Directory (Base Static)
DIR_BASE_LOCAL = Path(fr"{SSD}:\Meghna_UAV_Campaign_2026\{AREA}\{LOC}\02_Raw_GNSS_Survey\Base_Static")

# Rover GCP Inputs & Outputs
CSV_ROVER_IN = Path(fr"{SSD}:\Meghna_UAV_Campaign_2026\{AREA}\{LOC}\02_Raw_GNSS_Survey\Rover_GCPs\{AREAN}_{LOCN}.csv")

# Output Files (Regular CSV, Metadata CSV, and Map PNG)
CSV_ROVER_OUT = DIR_PPP_OUT / f"{LOC}_coor.csv"
CSV_ROVER_META_OUT = DIR_PPP_OUT / f"{LOC}_meta_coor.csv"
MAP_OUT = DIR_PPP_OUT / f"{LOC}_gcp_map.png"

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

def generate_gcp_map(df, output_path, crs="EPSG:4326"):
    """Generates a visual inspection map with satellite imagery background and point labels in WGS 84"""
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Plot shifted GCP positions in WGS 84 (Lon, Lat)
    ax.scatter(
        df['Lon'], df['Lat'], 
        color='#FF2D00', edgecolor='white', linewidth=1.2, 
        s=70, zorder=5, label='Shifted GCPs'
    )
    
    # Add PointID labels with bounding boxes for contrast
    for _, row in df.iterrows():
        ax.annotate(
            text=str(row['PointID']),
            xy=(row['Lon'], row['Lat']),
            xytext=(7, 7), 
            textcoords='offset points',
            color='yellow' if HAS_CONTEXTILY else 'black', 
            fontsize=8, 
            fontweight='bold',
            bbox=dict(
                boxstyle='round,pad=0.25', 
                fc='black' if HAS_CONTEXTILY else 'yellow', 
                alpha=0.7, 
                ec='none'
            ),
            zorder=6
        )
    
    # Set dynamic bounds with padding around the GCP cluster (in degrees)
    x_min, x_max = df['Lon'].min(), df['Lon'].max()
    y_min, y_max = df['Lat'].min(), df['Lat'].max()
    x_buffer = max((x_max - x_min) * 0.15, 0.0005)
    y_buffer = max((y_max - y_min) * 0.15, 0.0005)
    
    ax.set_xlim(x_min - x_buffer, x_max + x_buffer)
    ax.set_ylim(y_min - y_buffer, y_max + y_buffer)
    
    # Fetch Satellite Basemap (tries Esri World Imagery, falls back to OpenStreetMap or vector layout)
    if HAS_CONTEXTILY:
        basemap_loaded = False
        # Provider order list for basemap retrieval
        providers = [
            cx.providers.Esri.WorldImagery,
            cx.providers.OpenStreetMap.Mapnik,
            cx.providers.CartoDB.Positron
        ]
        
        for provider in providers:
            try:
                cx.add_basemap(ax, crs=crs, source=provider)
                basemap_loaded = True
                break
            except Exception:
                continue
                
        if not basemap_loaded:
            print("Notice: Web basemap servers un-reachable. Outputting vector map grid.")
            ax.set_facecolor('#e8ecef')
    else:
        print("Notice: 'contextily' library not installed. Outputting vector map grid.")
        ax.set_facecolor('#e8ecef')
    
    ax.set_title(f"Shifted GCP Locations - WGS 84 ({LOC})", fontsize=12, fontweight='bold', pad=12)
    ax.set_xlabel("Longitude (°E)", fontsize=10)
    ax.set_ylabel("Latitude (°N)", fontsize=10)
    ax.grid(True, linestyle='--', alpha=0.4, zorder=4)
    ax.ticklabel_format(useOffset=False, style='plain')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"GCP inspection map saved to: {output_path}")

# ==========================================
# 3. MAIN EXECUTION
# ==========================================
def main():
    DIR_PPP_OUT.mkdir(parents=True, exist_ok=True)
    
    # Transformers for precision projection shifting
    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32646", always_xy=True)
    to_wgs84 = Transformer.from_crs("EPSG:32646", "EPSG:4326", always_xy=True)

    print("--- Processing Local Field Base & Shifting GCPs ---")
    
    # 1. Automatically locate the .sum file in DIR_BASE_LOCAL
    sum_files = list(DIR_BASE_LOCAL.glob("*.sum"))
    if not sum_files:
        # Check for uppercase extension if needed
        sum_files = list(DIR_BASE_LOCAL.glob("*.[sS][uU][mM]"))
        
    if not sum_files:
        print(f"Error: No .sum file found in {DIR_BASE_LOCAL}")
        return
        
    SUM_BASE_LOCAL = sum_files[0]
    print(f"Auto-detected PPP summary file: {SUM_BASE_LOCAL.name}")

    if CSV_ROVER_IN.exists():
        ppp_local = parse_csrs_ppp_summary(SUM_BASE_LOCAL)
        
        # Read raw CSV
        df = pd.read_csv(CSV_ROVER_IN, header=None, names=['PointID', 'Lat', 'Lon', 'Elevation'])
        df['Lat'] = df['Lat'].apply(clean_latlon)
        df['Lon'] = df['Lon'].apply(clean_latlon)
        
        # Project Lat/Lon to UTM 46N to compute 3D distance shifts in meters
        df['Easting'], df['Northing'] = to_utm.transform(df['Lon'].values, df['Lat'].values)
        
        # Extract temporary field coordinate of the Base (Assumed to be first row)
        base_row = df.iloc[0]
        field_E = base_row['Easting']
        field_N = base_row['Northing']
        field_H = base_row['Elevation']
        
        # Calculate 3D Translation Vector in meters
        shift_E = ppp_local['E'] - field_E
        shift_N = ppp_local['N'] - field_N
        shift_H = ppp_local['H_ellips'] - field_H
        
        print(f"Calculated Shift Vector -> E: {shift_E:+.4f}m, N: {shift_N:+.4f}m, H: {shift_H:+.4f}m")
        
        # Apply shift vector to planar UTM coordinates
        df['Easting_Shifted'] = df['Easting'] + shift_E
        df['Northing_Shifted'] = df['Northing'] + shift_N
        df['Elevation_Shifted'] = (df['Elevation'] + shift_H).round(4)
        
        # 2. Convert shifted coordinates back to WGS 84 (Lon, Lat)
        df['Lon_Shifted'], df['Lat_Shifted'] = to_wgs84.transform(
            df['Easting_Shifted'].values, df['Northing_Shifted'].values
        )
        df['Lat_Shifted'] = df['Lat_Shifted'].round(7)
        df['Lon_Shifted'] = df['Lon_Shifted'].round(7)
        
        # 3. Separate regular numeric GCPs from metadata points
        # Filter based on whether PointID starts with a digit
        df['PointID_str'] = df['PointID'].astype(str).str.strip()
        is_numeric = df['PointID_str'].str.contains(r'^\d', regex=True)
        
        df_regular = df[is_numeric][['PointID', 'Lat_Shifted', 'Lon_Shifted', 'Elevation_Shifted']].copy()
        df_regular.columns = ['PointID', 'Lat', 'Lon', 'Elevation']
        
        df_meta = df[~is_numeric][['PointID', 'Lat_Shifted', 'Lon_Shifted', 'Elevation_Shifted']].copy()
        df_meta.columns = ['PointID', 'Lat', 'Lon', 'Elevation']
        
        # Save output CSVs
        df_regular.to_csv(CSV_ROVER_OUT, index=False)
        print(f"Successfully saved regular GCPs (WGS 84) to: {CSV_ROVER_OUT}")
        
        df_meta.to_csv(CSV_ROVER_META_OUT, index=False)
        print(f"Successfully saved metadata points (WGS 84) to: {CSV_ROVER_META_OUT}")
        
        # 4. Generate map in WGS 84 with updated basemap provider loop
        full_output_df = df[['PointID', 'Lat_Shifted', 'Lon_Shifted', 'Elevation_Shifted']].copy()
        full_output_df.columns = ['PointID', 'Lat', 'Lon', 'Elevation']
        generate_gcp_map(full_output_df, MAP_OUT, crs="EPSG:4326")
    else:
        print(f"Missing input file: {CSV_ROVER_IN}")

if __name__ == "__main__":
    main()