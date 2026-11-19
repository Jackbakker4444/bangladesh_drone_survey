import os
import shutil
import sys
import threading
import time
from pathlib import Path

# === CONFIGURATIE ===
SOURCE_DIR = Path(r"D:\Veldwerk_Meghna")          # Pas aan naar je externe SSD-map
DEST_DIR = Path(r"Y:\research-jouwgroep\data")   # Pas aan naar je WUR Yoda-map
PAUSE_FLAG_FILE = Path(__file__).resolve().parent / "pause.flag"
PART_SUFFIX = ".part"
CHUNK_SIZE = 4 * 1024 * 1024                    # 4 MB blokken (snelle pauze-reactie)
POLL_INTERVAL = 0.5                             # Seconden tussen pauze-checks


class PauseController:
    def __init__(self, flag_file: Path):
        self.flag_file = flag_file
        self._manual_pause = False
        self._lock = threading.Lock()

    def toggle_manual_pause(self) -> bool:
        with self._lock:
            self._manual_pause = not self._manual_pause
            return self._manual_pause

    def is_paused(self) -> bool:
        with self._lock:
            return self._manual_pause or self.flag_file.exists()

    def wait_if_paused(self) -> None:
        if not self.is_paused():
            return

        print("\n⏸  UPLOAD GEPAUZEERD. Verwijder 'pause.flag' of druk op Enter (na 'p') om te hervatten...")
        while self.is_paused():
            time.sleep(POLL_INTERVAL)
        print("▶  UPLOAD HERVAT.\n")


def keyboard_listener(controller: PauseController) -> None:
    """Luistert in de achtergrond naar 'p' + Enter om handmatig te pauzeren/hervatten."""
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            if line.strip().lower() == "p":
                paused = controller.toggle_manual_pause()
                status = "AANGEZET" if paused else "UITGEZET"
                print(f"[Toetsenbord] Handmatige pauze {status}.")
        except Exception:
            break


def copy_file_pausable(src: Path, dst: Path, controller: PauseController) -> str:
    """Kopiert één bestand in blokken met ondersteuning voor pauzeren en veilig hervatten."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    temp_dst = dst.with_name(dst.name + PART_SUFFIX)

    src_size = src.stat().st_size

    # Als het eindbestand al bestaat en exact even groot is, overslaan
    if dst.exists() and dst.stat().st_size == src_size:
        return "skipped"

    # Eventueel achtergebleven .part-bestand van een eerdere onderbreking opruimen
    if temp_dst.exists():
        try:
            temp_dst.unlink()
        except OSError:
            pass

    copied = 0
    try:
        with open(src, "rb") as f_src, open(temp_dst, "wb") as f_dst:
            while True:
                controller.wait_if_paused()

                chunk = f_src.read(CHUNK_SIZE)
                if not chunk:
                    break

                f_dst.write(chunk)
                copied += len(chunk)

        # Pas hernoemen naar definitieve naam als het hele bestand is geschreven
        shutil.move(str(temp_dst), str(dst))
        return "copied"

    except Exception as exc:
        # Probeer onvolledig .part-bestand op te ruimen zodat het bij herstart schoon opnieuw begint
        if temp_dst.exists():
            try:
                temp_dst.unlink()
            except OSError:
                pass
        raise exc


def collect_files(source_dir: Path) -> list[Path]:
    """Verzamelt alle bestanden recursief (negeert eventuele .part-bestanden)."""
    files: list[Path] = []
    for root, _, filenames in os.walk(source_dir):
        for name in filenames:
            if name.endswith(PART_SUFFIX):
                continue
            files.append(Path(root) / name)
    return sorted(files)


def main() -> None:
    if not SOURCE_DIR.exists():
        print(f"Fout: bronmap bestaat niet: {SOURCE_DIR}")
        sys.exit(1)

    if not DEST_DIR.exists():
        print(f"Fout: doelmap (Yoda) is niet bereikbaar of niet gemount: {DEST_DIR}")
        sys.exit(1)

    controller = PauseController(PAUSE_FLAG_FILE)

    listener = threading.Thread(target=keyboard_listener, args=(controller,), daemon=True)
    listener.start()

    files = collect_files(SOURCE_DIR)
    total_files = len(files)
    total_bytes = sum(f.stat().st_size for f in files)

    print(f"Gevonden bestanden: {total_files} ({total_bytes / (1024**3):.2f} GB)")
    print(f"Bron:  {SOURCE_DIR}")
    print(f"Doel:  {DEST_DIR}")
    print(f"Pauzeren: typ 'p' + Enter, of maak het bestand '{PAUSE_FLAG_FILE.name}' aan.\n")

    uploaded_bytes = 0
    start_time = time.time()

    for idx, src_file in enumerate(files, start=1):
        controller.wait_if_paused()

        rel_path = src_file.relative_to(SOURCE_DIR)
        dst_file = DEST_DIR / rel_path
        file_size = src_file.stat().st_size

        try:
            status = copy_file_pausable(src_file, dst_file, controller)
            uploaded_bytes += file_size

            elapsed = max(time.time() - start_time, 0.001)
            speed_mbs = (uploaded_bytes / (1024**2)) / elapsed
            pct = (uploaded_bytes / total_bytes * 100) if total_bytes > 0 else 100.0

            label = "OVERGESLAGEN" if status == "skipped" else "KLAAR"
            print(f"[{idx}/{total_files}] {pct:5.1f}% | {label}: {rel_path} ({speed_mbs:.1f} MB/s)")

        except KeyboardInterrupt:
            print("\nScript onderbroken door gebruiker (Ctrl+C). Voltooide bestanden blijven behouden.")
            sys.exit(0)
        except Exception as e:
            print(f"\n[WAARSCHUWING] Fout bij kopiëren van {rel_path}: {e}")
            print("Het script gaat verder met het volgende bestand...")

    print("\nUploadproces voltooid.")


if __name__ == "__main__":
    main()