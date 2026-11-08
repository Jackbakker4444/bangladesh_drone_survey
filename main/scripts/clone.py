import subprocess
import sys
from pathlib import Path

# --- CONFIGURATION ---
DRIVE_A = r"G:\\"  # e.g., The SSD with Drone Images
DRIVE_B = r"F:\\"  # e.g., The SSD with RTK Measurements

# 🛡️ SAFETY FIRST: 
# Set to True to simulate the merge and see what WILL be copied.
# Set to False to actually execute the file transfers.
DRY_RUN = False
# ----------------------

def run_merge_pass(source: Path, target: Path, dry_run: bool):
    """Executes a single, non-destructive robocopy pass."""
    
    print(f"\n{'='*50}")
    print(f"Starting Pass: {source} ===> {target}")
    if dry_run:
        print("MODE: DRY RUN (No files will be changed)")
    print(f"{'='*50}\n")

    # Core Robocopy flags:
    # /E     : Copy subdirectories, including empty ones.
    # /XO    : Exclude older files (prevents overwriting newer data).
    # /MT:16 : 16 parallel threads for SSD speed.
    # /R:2 /W:2 : Retry failed files twice, wait 2 seconds.
    cmd = [
        "robocopy",
        str(source),
        str(target),
        "/E",
        "/XO",
        "/MT:16",
        "/R:2",
        "/W:2",
        "/XD", "$RECYCLE.BIN", "System Volume Information"
    ]

    if dry_run:
        # /L tells robocopy to ONLY list files, not copy or modify them.
        cmd.append("/L")

    # IMPORTANT: We DO NOT use check=True. Robocopy returns codes 1-7 for 
    # successful operations (e.g., 1 = files copied, 3 = extra files detected).
    result = subprocess.run(cmd, shell=True)

    # Exit codes 8 and above indicate critical failures (e.g., permissions, hardware errors).
    if result.returncode >= 8:
        print(f"\n❌ CRITICAL ERROR: Pass failed with exit code {result.returncode}.")
        sys.exit(1)
    else:
        print(f"\n✅ Pass completed successfully (Exit code: {result.returncode}).")


def safe_bidirectional_merge(drive_a: str, drive_b: str, dry_run: bool):
    path_a = Path(drive_a)
    path_b = Path(drive_b)

    # 1. Validation checks
    if not path_a.exists():
        print(f"Error: Drive path '{drive_a}' does not exist.")
        sys.exit(1)
    if not path_b.exists():
        print(f"Error: Drive path '{drive_b}' does not exist.")
        sys.exit(1)

    print("\n" + "#"*50)
    print(" INITIATING BIDIRECTIONAL SAFE MERGE")
    print(" Directories will complement each other. Nothing will be deleted.")
    print("#"*50)

    # 2. Execute Pass 1 (A -> B)
    # This pushes the Drone Images (and anything else unique to A) onto B.
    run_merge_pass(path_a, path_b, dry_run)

    # 3. Execute Pass 2 (B -> A)
    # This pushes the RTK Measurements (and anything else unique to B) onto A.
    run_merge_pass(path_b, path_a, dry_run)

    print("\n" + "#"*50)
    if dry_run:
        print(" DRY RUN COMPLETE. Review the logs above.")
        print(" If everything looks correct, change DRY_RUN = False and run again.")
    else:
        print(" BIDIRECTIONAL MERGE COMPLETE! Both drives are now identical.")
    print("#"*50 + "\n")


if __name__ == "__main__":
    safe_bidirectional_merge(DRIVE_A, DRIVE_B, DRY_RUN)