import hashlib
import json
import os
import platform
import subprocess
import uuid
import requests

KEY_PATH = "license.key"
API_URL = "https://jules-api.vercel.app/api/validate"

def get_machine_soul() -> str:
    """Generates a unique hardware ID (HWID) similar to node-machine-id"""
    try:
        if platform.system() == "Windows":
            hwid = subprocess.check_output('wmic csproduct get uuid').decode().split('\n')[1].strip()
        elif platform.system() == "Darwin":
            hwid = subprocess.check_output("ioreg -rd1 -c IOPlatformExpertDevice | grep IOPlatformUUID", shell=True).decode().split('"')[3]
        else:
            hwid = subprocess.check_output('cat /etc/machine-id', shell=True).decode().strip()
    except Exception:
        hwid = str(uuid.getnode())
        
    return hashlib.md5((hwid + "ReinhartWasHere").encode()).hexdigest()

def verify_key_payload(key: str) -> dict:
    hwid = get_machine_soul()
    payload = {"key": key.strip(), "hwid": hwid}
    
    try:
        # 5-second timeout so the UI doesn't freeze forever if the server is down
        response = requests.post(API_URL, json=payload, timeout=5)
        data = response.json()
        
        if data.get("success"):
            return {
                "passed": True, 
                "owner": data.get("owner", "Unknown"), 
                "expires": data.get("expires", "Lifetime / Active")
            }
        else:
            return {"passed": False, "msg": data.get("message", "Key Rejected")}
    except Exception as e:
        return {"passed": False, "msg": "Cannot connect to auth server."}

def save_key(key: str) -> bool:
    try:
        with open(KEY_PATH, "w", encoding="utf-8") as f:
            f.write(key.strip())
        return True
    except Exception:
        return False

def get_saved_key() -> str:
    if os.path.exists(KEY_PATH):
        try:
            with open(KEY_PATH, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    return ""
