from pathlib import Path

from app.config import IMG_SIZE, GRADCAM_DIR, AFFECTED_DIR
from app.utils import (
    ensure_directories,
    load_image_rgb,
    prepare_model_input,
    save_rgb_image,
    safe_filename
)
from app.gradcam import make_gradcam_heatmap, overlay_gradcam_on_image
from app.severity import (
    segment_leaf_mask,
    create_disease_mask_from_heatmap,
    compute_severity,
    severity_label_from_percent,
    overlay_mask_on_image
)

class PlantDiseasePipeline:
    def __init__(self, predictor, recommender, save_logs=True):
        self.predictor = predictor
        self.recommender = recommender
        self.save_logs = save_logs

        ensure_directories([GRADCAM_DIR, AFFECTED_DIR])

    def run_analysis(self, image_path, save_log_fn=None):
        image_path = Path(image_path)
        image_rgb = load_image_rgb(image_path)
        resized_img, img_array = prepare_model_input(image_rgb, IMG_SIZE)

        prediction = self.predictor.predict(img_array)
        predicted_class = prediction["predicted_class"]

        gradcam_overlay_path = None
        affected_overlay_path = None
        severity_label = None
        severity_percent = None
        leaf_pixels = None
        affected_pixels = None

        if predicted_class.endswith("_Healthy"):
            recommendation = self.recommender.get_recommendation(predicted_class)
        else:
            heatmap = make_gradcam_heatmap(
                img_array=img_array,
                model=self.predictor.model,
                pred_index=prediction["pred_index"]
            )

            leaf_mask = segment_leaf_mask(resized_img)
            disease_mask = create_disease_mask_from_heatmap(heatmap, resized_img.shape)
            affected_mask, leaf_pixels, affected_pixels, severity_percent = compute_severity(
                leaf_mask, disease_mask
            )
            severity_label = severity_label_from_percent(severity_percent)

            recommendation = self.recommender.get_recommendation(predicted_class, severity_label)

            gradcam_overlay = overlay_gradcam_on_image(resized_img, heatmap)
            affected_overlay = overlay_mask_on_image(resized_img, affected_mask * 255)

            base_name = safe_filename(image_path.stem)

            gradcam_overlay_path = GRADCAM_DIR / f"{base_name}_gradcam.png"
            affected_overlay_path = AFFECTED_DIR / f"{base_name}_affected.png"

            save_rgb_image(gradcam_overlay, gradcam_overlay_path)
            save_rgb_image(affected_overlay, affected_overlay_path)

        result = {
            "image_path": str(image_path),
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

        if self.save_logs and save_log_fn is not None:
            save_log_fn(result)

        return result