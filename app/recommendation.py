import json
from pathlib import Path
from app.config import RECOMMENDATIONS_PATH

class RecommendationEngine:
    def __init__(self):
        self.data = self._load_recommendations()

    def _load_recommendations(self):
        path = Path(RECOMMENDATIONS_PATH)
        if not path.exists():
            raise FileNotFoundError(f"recommendations.json not found at: {path}")

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_recommendation(self, disease, severity=None):
        disease_data = self.data.get(disease)

        if disease_data is None:
            return {
                "summary": "No recommendation found.",
                "treatment": [],
                "prevention": [],
                "monitoring": [],
                "caution": [],
                "references": []
            }

        # Healthy entry
        if isinstance(disease_data, dict) and disease_data.get("status") == "healthy":
            return disease_data

        # Disease entry with severity
        if severity is not None:
            result = disease_data.get(severity)
            if result is not None:
                return result

        return {
            "summary": "No recommendation found.",
            "treatment": [],
            "prevention": [],
            "monitoring": [],
            "caution": [],
            "references": []
        }