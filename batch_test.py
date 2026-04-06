from pathlib import Path
from app.predictor import DiseasePredictor
from app.recommendation import RecommendationEngine
from app.logbook import save_logbook_entry
from app.pipeline import PlantDiseasePipeline

TEST_FOLDER = Path("/Users/adrianpothanah/Plant_Disease_Management_System/Plant-Disease-Management-System/mini_dataset")

def main():
    predictor = DiseasePredictor()
    recommender = RecommendationEngine()
    pipeline = PlantDiseasePipeline(
        predictor=predictor,
        recommender=recommender,
        save_logs=True
    )

    image_files = []
    for ext in ("*.jpg", "*.jpeg", "*.png"):
        image_files.extend(TEST_FOLDER.rglob(ext))

    print(f"Found {len(image_files)} images")

    for image_path in image_files[:10]:
        print("\n--------------------------------")
        print("Testing:", image_path.name)

        try:
            result = pipeline.run_analysis(image_path, save_log_fn=save_logbook_entry)
            print("Predicted:", result["predicted_class"])
            print("Confidence:", f"{result['confidence']:.4f}")
            print("Severity:", result["severity_label"], result["severity_percent"])
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    main()