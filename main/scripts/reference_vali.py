import os
import re
from pathlib import Path

# ==========================================
# 1. PATH DEFINITIONS
# ==========================================
SSD = "F"
AREA = "01_Rajrajeshwar"
AREABASE = "Base_20261107"
LOC = "Loc_01_20261106"

# Known Coordinates for Base 1 Validation (Pillar GPS 5692)
KNOWN_E = 247305.0956
KNOWN_N = 2568141.6390
KNOWN_MSL = 3.3640

# Processed Output Directory
DIR_PPP_OUT = Path(fr"{SSD}:\Meghna_UAV_Campaign_2026\{AREA}\{LOC}\04_Processed_PPP")

# Reference Point (Base 1)
DIR_BASE_1 = Path(fr"{SSD}:\Meghna_UAV_Campaign_2026\{AREA}\{AREABASE}")
SUM_BASE_1 = DIR_BASE_1 / f"{AREABASE}_Combined.sum"
METRICS_OUT = DIR_PPP_OUT / f"{AREABASE}_accuracy_metrics.txt"

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

# ==========================================
# 3. MAIN EXECUTION
# ==========================================
def main():
    DIR_PPP_OUT.mkdir(parents=True, exist_ok=True)
    
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

if __name__ == "__main__":
    main()