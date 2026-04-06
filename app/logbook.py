import json
from pathlib import Path
from datetime import datetime
from app.config import LOGBOOK_PATH

def save_logbook_entry(entry):
    path = Path(LOGBOOK_PATH)

    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception:
                data = []
    else:
        data = []

    entry["timestamp"] = datetime.now().isoformat()
    data.append(entry)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def read_logbook_entries():
    path = Path(LOGBOOK_PATH)

    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []