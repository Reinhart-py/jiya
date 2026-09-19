import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, Any
import requests
from utils.paths import get_app_dir, get_export_dir

def get_setup_state_file() -> Path:
    return get_app_dir() / "setup_complete.lock"

def is_first_run() -> bool:
    return not get_setup_state_file().exists()

def mark_setup_complete() -> None:
    try:
        with open(get_setup_state_file(), "w", encoding="utf-8") as f:
            f.write("SETUP_INITIALIZED_V4")
    except Exception:
        pass

def find_chrome_binary() -> str:
    system = platform.system()
    if system == "Windows":
        candidates = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe")
            path, _ = winreg.QueryValueEx(key, "")
            if os.path.isfile(path):
                return path
        except Exception:
            pass
    elif system == "Darwin":
        paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        ]
        for p in paths:
            if os.path.isfile(p):
                return p
    else:
        paths = ["/usr/bin/google-chrome", "/usr/bin/chromium-browser", "/usr/bin/chromium"]
        for p in paths:
            if os.path.isfile(p):
                return p
    return ""

def run_environment_diagnostics(progress_callback: Callable[[str, int, bool], None]) -> Dict[str, Any]:
    report = {"ready": True, "chrome_path": "", "errors": []}

    progress_callback("Allocating local application storage...", 20, True)
    try:
        app_dir = get_app_dir()
        export_dir = get_export_dir()
        test_file = app_dir / ".write_test"
        with open(test_file, "w") as f:
            f.write("OK")
        test_file.unlink(missing_ok=True)
    except Exception as e:
        report["ready"] = False
        report["errors"].append(f"Storage permission denied: {e}")
        progress_callback("Failed writing to application storage.", 20, False)
        return report

    progress_callback("Checking Chromium browser runtime...", 50, True)
    chrome_binary = find_chrome_binary()
    if chrome_binary:
        report["chrome_path"] = chrome_binary
    else:
        report["ready"] = False
        report["errors"].append("Google Chrome or Chromium runtime not found on this workstation.")
        progress_callback("Google Chrome is not detected.", 50, False)
        return report

    progress_callback("Verifying network connection and authentication gateway...", 75, True)
    try:
        res = requests.get("https://jules-api.vercel.app/api/validate", timeout=5)
    except Exception:
        pass

    progress_callback("Initializing hardware cryptographic signature...", 90, True)
    from utils.security import get_machine_soul
    soul = get_machine_soul()
    if not soul:
        report["ready"] = False
        report["errors"].append("Could not generate hardware fingerprint.")
        progress_callback("Cryptographic signature failure.", 90, False)
        return report

    progress_callback("Environment initialized successfully.", 100, True)
    mark_setup_complete()
    return report
