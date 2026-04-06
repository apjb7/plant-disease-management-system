from app.config import IMG_SIZE, UPLOADS_DIR, GRADCAM_DIR, AFFECTED_DIR
from app.utils import ensure_directories, load_image_rgb, prepare_model_input, save_rgb_image
from app.predictor import DiseasePredictor
from app.recommendation import RecommendationEngine
from app.logbook import save_logbook_entry
from app.gradcam import make_gradcam_heatmap, overlay_gradcam_on_image
from app.severity import (
    segment_leaf_mask,
    create_disease_mask_from_heatmap,
    compute_severity,
    severity_label_from_percent,
    overlay_mask_on_image
)

# Change this to your test image
IMAGE_PATH = "/Users/adrianpothanah/Plant_Disease_Management_System/Plant-Disease-Management-System/unseen_test_dataset_final/Mango_Healthy/Mango_Healthy_0002.jpg"

def main():
    ensure_directories([UPLOADS_DIR, GRADCAM_DIR, AFFECTED_DIR])

    predictor = DiseasePredictor()
    recommender = RecommendationEngine()

    image_rgb = load_image_rgb(IMAGE_PATH)
    resized_img, img_array = prepare_model_input(image_rgb, IMG_SIZE)

    prediction = predictor.predict(img_array)
    predicted_class = prediction["predicted_class"]

    gradcam_overlay_path = None
    affected_overlay_path = None
    severity_label = None
    severity_percent = None
    leaf_pixels = None
    affected_pixels = None

    if predicted_class.endswith("_Healthy"):
        recommendation = recommender.get_recommendation(predicted_class)
    else:
        heatmap = make_gradcam_heatmap(
            img_array=img_array,
            model=predictor.model,
            pred_index=prediction["pred_index"]
        )

        leaf_mask = segment_leaf_mask(resized_img)
        disease_mask = create_disease_mask_from_heatmap(heatmap, resized_img.shape)
        affected_mask, leaf_pixels, affected_pixels, severity_percent = compute_severity(
            leaf_mask, disease_mask
        )
        severity_label = severity_label_from_percent(severity_percent)

        recommendation = recommender.get_recommendation(predicted_class, severity_label)

        gradcam_overlay = overlay_gradcam_on_image(resized_img, heatmap)
        affected_overlay = overlay_mask_on_image(resized_img, affected_mask * 255)

        gradcam_overlay_path = GRADCAM_DIR / "gradcam_overlay.png"
        affected_overlay_path = AFFECTED_DIR / "affected_overlay.png"

        save_rgb_image(gradcam_overlay, gradcam_overlay_path)
        save_rgb_image(affected_overlay, affected_overlay_path)

    result = {
        "image_path": IMAGE_PATH,
        "predicted_class": predicted_class,
        "confidence": prediction["confidence"],
        "top3": prediction["top3"],
        "severity_label": severity_label,
        "severity_percent": severity_percent,
        "leaf_pixels": leaf_pixels,
        "affected_pixels": affected_pixels,
        "gradcam_overlay_path": str(gradcam_overlay_path) if gradcam_overlay_path else None,
        "affected_overlay_path": str(affected_overlay_path) if affected_overlay_path else None,
        "recommendation": recommendation
    }

    save_logbook_entry(result)

    print("\nPrediction result")
    print("-----------------")
    print("Predicted class:", predicted_class)
    print("Confidence:", f"{prediction['confidence']:.4f}")
    print("Top 3:", prediction["top3"])
    print("Severity label:", severity_label)
    print("Severity percent:", severity_percent)
    print("Leaf pixels:", leaf_pixels)
    print("Affected pixels:", affected_pixels)
    print("Recommendation summary:", recommendation.get("summary"))

    print("\nTreatment:")
    for item in recommendation.get("treatment", []):
        print("-", item)

    if gradcam_overlay_path:
        print("\nGrad-CAM saved to:", gradcam_overlay_path)
    if affected_overlay_path:
        print("Affected overlay saved to:", affected_overlay_path)

if __name__ == "__main__":
    main()