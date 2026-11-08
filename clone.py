import subprocess
import sys
from pathlib import Path

# --- CONFIGURATION ---
SOURCE_DRIVE = r"G:\\"  # Source SSD (Primary)
TARGET_DRIVE = r"E:\\"  # Target SSD (Backup)
# ----------------------


def safe_sync_drives(src: str, dst: str):
    source_path = Path(src)
    target_path = Path(dst)

    if not source_path.exists():
        print(f"Error: Source path '{src}' does not exist.")
        sys.exit(1)

    if not target_path.exists():
        print(f"Error: Target path '{dst}' does not exist.")
        sys.exit(1)

    print(f"Starting non-destructive sync: {src} ===> {dst}")
    print("Files on the target SSD will NOT be deleted.\n")

    # Robocopy flags:
    # /E     : Copy subdirectories, including empty ones.
    # /XO    : Exclude older files (skips files already up-to-date on destination).
    # /MT:16 : 16 parallel threads for fast SSD read/write speeds.
    # /R:2 /W:2 : Retry failed transfers twice, waiting 2 seconds between attempts.
    # /NP    : Suppress progress percentage per file to keep terminal logs clean.
    cmd = [
        "robocopy",
        str(source_path),
        str(target_path),
        "/E",
        "/XO",
        "/MT:16",
        "/R:2",
        "/W:2",
    ]

    result = subprocess.run(cmd, shell=True, check=True)

    # Robocopy exit codes < 8 indicate successful operations
    if result.returncode < 8:
        print("\nSync completed successfully! All new/modified files copied.")
    else:
        print(
            f"\nSync finished with warnings/errors (Exit code: {result.returncode})."
        )


if __name__ == "__main__":
    safe_sync_drives(SOURCE_DRIVE, TARGET_DRIVE)