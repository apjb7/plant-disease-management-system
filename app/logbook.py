import json
from datetime import datetime
from pathlib import Path

from app.config import BASE_DIR

LOGBOOK_PATH = BASE_DIR / "data" / "logbook.json"
LOGBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)


def _load_entries():
    if not LOGBOOK_PATH.exists():
        return []

    try:
        with open(LOGBOOK_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_entries(entries):
    with open(LOGBOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def save_logbook_entry(result: dict):
    entries = _load_entries()

    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "image_path": str(result.get("image_path", "")),
        "uploaded_image_path": str(result.get("uploaded_image_path", "")),
        "predicted_class": result.get("predicted_class", ""),
        "confidence": result.get("confidence", 0),
        "severity_label": result.get("severity_label") or result.get("severity", ""),
        "severity_percent": result.get("severity_percent", 0),
        "top3": result.get("top3", []),

        "summary": result.get("summary", ""),
        "what_to_do_now": result.get("what_to_do_now", []),
        "monitoring": result.get("monitoring", []),
        "caution": result.get("caution", []),
        "follow_up": result.get("follow_up", ""),
        "references_used": result.get("references_used", []),

        "gradcam_overlay_path": result.get("gradcam_overlay_path", ""),
        "affected_overlay_path": result.get("affected_overlay_path", "")
    }

    entries.append(entry)
    _save_entries(entries)


def read_logbook_entries():
    return _load_entries()