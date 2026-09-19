import json
import os
from typing import Any, Dict, List, Optional
from utils.paths import get_app_dir

def get_history_file() -> str:
    return str(get_app_dir() / "history.json")

def get_checkpoint_file() -> str:
    return str(get_app_dir() / "checkpoint.json")

MAX_HISTORY = 20

def load_all_history() -> List[Dict[str, Any]]:
    path = get_history_file()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []
    return []

def push_history_checkpoint(entry: Dict[str, Any]) -> None:
    history = load_all_history()
    engine = entry.get("engine")
    target = entry.get("target")
    history = [h for h in history if not (h.get("engine") == engine and h.get("target") == target)]
    history.insert(0, entry)
    history = history[:MAX_HISTORY]
    try:
        with open(get_history_file(), "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception:
        pass

def update_latest_progress(engine: str, target: str, last_page_or_idx: int, total_saved: int) -> None:
    history = load_all_history()
    for h in history:
        if h.get("engine") == engine and h.get("target") == target:
            h["last_step"] = last_page_or_idx
            h["total_saved"] = total_saved
            break
    try:
        with open(get_history_file(), "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception:
        pass

    set_active_checkpoint({
        "engine": engine,
        "target": target,
        "last_step": last_page_or_idx,
        "total_saved": total_saved
    })

def set_active_checkpoint(state: Dict[str, Any]) -> None:
    try:
        with open(get_checkpoint_file(), "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass

def get_active_checkpoint() -> Optional[Dict[str, Any]]:
    path = get_checkpoint_file()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and data.get("target"):
                    return data
        except Exception:
            return None
    return None

def clear_active_checkpoint() -> None:
    path = get_checkpoint_file()
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass

def save_state(city: str, query: str, country: str, page: int, total_saved: int, output_path: str, target_count: int) -> None:
    payload = {
        "engine": "2gis",
        "target": f"{city}:{query}",
        "city_name": city,
        "query_string": query,
        "country": country,
        "output_path": output_path,
        "last_step": page,
        "total_saved": total_saved,
        "target_count": target_count,
    }
    push_history_checkpoint(payload)
    set_active_checkpoint(payload)

def clear_state() -> None:
    clear_active_checkpoint()
