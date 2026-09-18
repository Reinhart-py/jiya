import hashlib
import json
import os
import platform
import subprocess
import uuid
import requests
from utils.paths import get_app_dir

API_URL = "https://jules-api.vercel.app/api/validate"

def get_key_path() -> str:
    return str(get_app_dir() / "license.key")

def get_machine_soul() -> str:
    components = []
    try:
        if platform.system() == "Windows":
            out = subprocess.check_output("wmic csproduct get uuid", shell=True).decode()
            lines = [line.strip() for line in out.splitlines() if line.strip()]
            if len(lines) > 1:
                components.append(lines[1])
            disk_out = subprocess.check_output("wmic diskdrive get serialnumber", shell=True).decode()
            disk_lines = [line.strip() for line in disk_out.splitlines() if line.strip()]
            if len(disk_lines) > 1:
                components.append(disk_lines[1])
        elif platform.system() == "Darwin":
            out = subprocess.check_output("ioreg -rd1 -c IOPlatformExpertDevice | grep IOPlatformUUID", shell=True).decode()
            components.append(out.split('"')[3])
        else:
            with open("/etc/machine-id", "r") as f:
                components.append(f.read().strip())
    except Exception:
        pass

    components.append(str(uuid.getnode()))
    components.append(os.getenv("USERNAME", os.getenv("USER", "generic_user")))
    components.append(platform.processor())

    raw_signature = "||".join(components) + "@KIRI_SECURE_FINGERPRINT_SALT_V4"
    return hashlib.sha256(raw_signature.encode()).hexdigest()

def verify_key_payload(key: str) -> dict:
    cleaned = key.strip()
    if not cleaned:
        return {"passed": False, "msg": "Key string cannot be empty."}

    hwid = get_machine_soul()
    payload = {
        "key": cleaned,
        "hwid": hwid,
        "os": platform.platform(),
        "arch": platform.machine()
    }

    try:
        response = requests.post(API_URL, json=payload, timeout=6)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return {
                    "passed": True,
                    "owner": str(data.get("owner", "Active User")),
                    "expires": str(data.get("expires", "Permanent")),
                }
            return {"passed": False, "msg": str(data.get("message", "License denied by server."))}
        return {"passed": False, "msg": f"Authentication rejected (Status {response.status_code})"}
    except requests.exceptions.Timeout:
        return {"passed": False, "msg": "Authentication server timeout. Check network."}
    except requests.exceptions.RequestException:
        return {"passed": False, "msg": "Gateway connection failure."}

def save_key(key: str) -> bool:
    try:
        with open(get_key_path(), "w", encoding="utf-8") as f:
            f.write(key.strip())
        return True
    except Exception:
        return False

def get_saved_key() -> str:
    path = get_key_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            return ""
    return ""

def revoke_saved_key() -> None:
    path = get_key_path()
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass
