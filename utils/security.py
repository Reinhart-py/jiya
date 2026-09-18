import hashlib
import os
import platform
import subprocess
import uuid
from datetime import datetime, timezone
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

def format_expiry(expires_raw: str | None) -> str:
    if not expires_raw:
        return "Permanent / Lifetime"

    try:
        clean_iso = expires_raw.replace("Z", "+00:00")
        exp_dt = datetime.fromisoformat(clean_iso)
        now_dt = datetime.now(timezone.utc)

        delta = exp_dt - now_dt
        if delta.total_seconds() <= 0:
            return "Expired"

        local_str = exp_dt.astimezone().strftime("%d %b %Y, %H:%M")
        days = delta.days
        hours = int(delta.seconds // 3600)

        if days > 0:
            return f"{local_str} ({days}d {hours}h remaining)"
        else:
            minutes = int((delta.seconds % 3600) // 60)
            return f"{local_str} ({hours}h {minutes}m remaining)"
    except Exception:
        return str(expires_raw)[:19]

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
                formatted_exp = format_expiry(data.get("expiresAt"))
                return {
                    "passed": True,
                    "owner": str(data.get("owner", "Active User")),
                    "expires": formatted_exp,
                    "raw_expires": data.get("expiresAt")
                }
            return {"passed": False, "msg": str(data.get("message", "License denied by server."))}
        elif response.status_code in (403, 404):
            data = response.json()
            msg = data.get("message", "key_rejected")
            if msg == "key_expired":
                return {"passed": False, "msg": "License duration has expired."}
            elif msg == "hwid_mismatch":
                return {"passed": False, "msg": "Locked to another machine (HWID mismatch)."}
            elif msg == "key_inactive":
                return {"passed": False, "msg": "License is deactivated by administrator."}
            return {"passed": False, "msg": f"Access Denied: {msg}"}
        return {"passed": False, "msg": f"Authentication rejected (Status {response.status_code})"}
    except requests.exceptions.Timeout:
        return {"passed": False, "msg": "Auth server timeout. Check network."}
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
