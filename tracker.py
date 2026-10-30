import json
import os

DATA_FILE = "user_progress.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"current_unit": 1, "drill_index": 0, "waiting_answer": False}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"current_unit": 1, "drill_index": 0, "waiting_answer": False}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_progress():
    return load_data()

def update_progress(unit=None, drill_idx=None, waiting=None):
    data = load_data()
    if unit is not None:
        data["current_unit"] = unit
    if drill_idx is not None:
        data["drill_index"] = drill_idx
    if waiting is not None:
        data["waiting_answer"] = waiting
    save_data(data)
