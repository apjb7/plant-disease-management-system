from pathlib import Path

BASE_DIR = Path("/Users/adrianpothanah/Plant_Disease_Management_System/Plant-Disease-Management-System")

MODEL_PATH = BASE_DIR / "models_second" / "best_stage1_model_tuned.keras"
CLASS_NAMES_PATH = BASE_DIR / "models_second" / "class_names_tuned.txt"

RECOMMENDATIONS_PATH = BASE_DIR / "data" / "recommendations.json"
LOGBOOK_PATH = BASE_DIR / "data" / "logbook.json"

UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"
GRADCAM_DIR = OUTPUTS_DIR / "gradcam"
AFFECTED_DIR = OUTPUTS_DIR / "affected"

IMG_SIZE = (300, 300)

BASE_MODEL_NAME = "efficientnetb0"
LAST_CONV_LAYER_NAME = "top_conv"

HEATMAP_THRESHOLD = 0.25
MILD_THRESHOLD = 15.0
MODERATE_THRESHOLD = 35.0