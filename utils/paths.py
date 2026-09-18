import os
import sys
from pathlib import Path

def get_app_dir() -> Path:
    if sys.platform == "win32":
        app_data = os.getenv("APPDATA")
        target = Path(app_data) / "Kiri" if app_data else Path.home() / ".kiri"
    else:
        target = Path.home() / ".kiri"
    target.mkdir(parents=True, exist_ok=True)
    return target

def get_export_dir() -> Path:
    downloads = Path.home() / "Downloads"
    if downloads.exists():
        target = downloads / "Kiri_Exports"
    else:
        target = get_app_dir() / "Exports"
    target.mkdir(parents=True, exist_ok=True)
    return target
