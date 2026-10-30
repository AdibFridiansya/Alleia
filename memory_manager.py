import json
import os

MEMORY_FILE = "bot_memory.json"

def _load_all():
    if not os.path.exists(MEMORY_FILE):
        return {}
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_all(data):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_session(user_id: int):
    data = _load_all()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            "mode": "IDLE", # IDLE, KAIWA, PARTIKEL, DRILL
            "partikel_idx": 0,
            "drill_target": "",
            "kaiwa_history": []
        }
        _save_all(data)
    return data[uid]

def save_user_session(user_id: int, session: dict):
    data = _load_all()
    data[str(user_id)] = session
    _save_all(data)

def append_kaiwa_history(user_id: int, role: str, text: str):
    sess = get_user_session(user_id)
    history = sess.get("kaiwa_history", [])
    history.append({"role": role, "text": text})
    if len(history) > 10:
        history = history[-10:]
    sess["kaiwa_history"] = history
    save_user_session(user_id, sess)
