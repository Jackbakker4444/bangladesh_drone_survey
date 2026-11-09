from pathlib import Path

def merge_rinex_files(file1_path, file2_path, output_path):
    """
    Merges two consecutive RINEX observation files into one.
    file1_path MUST be the chronologically earlier file.
    """
    print(f"Reading File 1: {file1_path.name}")
    print(f"Reading File 2: {file2_path.name}")
    
    with open(output_path, 'w') as outfile:
        # 1. Write the entirety of the first session (Header + Data)
        with open(file1_path, 'r') as f1:
            outfile.write(f1.read())
            
        # Ensure we start on a new line before appending file 2
        outfile.write('\n')

        # 2. Write ONLY the Data section of the second session (Skip Header)
        with open(file2_path, 'r') as f2:
            in_header = True
            for line in f2:
                if in_header:
                    if "END OF HEADER" in line:
                        in_header = False
                    continue  # Skip all header lines
                outfile.write(line)
                
    print(f"Success! Merged file saved to: {output_path}")

if __name__ == "__main__":
    # Define your paths (Make sure to put the earlier time file as file_1)
    base_dir = Path(r"F:\Meghna_UAV_Campaign_2026\01_Rajrajeshwar\Loc_02_20261109\02_Raw_GNSS_Survey\Base_Static")
    
    file_1 = base_dir / "3375201313F3.26O"  # Replace with actual first file name
    file_2 = base_dir / "3375201313G.26O"    # Replace with actual second file name
    
    output_combined = base_dir / "20261109_Combined.26O"
    
    merge_rinex_files(file_1, file_2, output_combined)