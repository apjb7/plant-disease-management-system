import numpy as np
from tensorflow.keras.models import load_model
from app.config import MODEL_PATH, CLASS_NAMES_PATH

class DiseasePredictor:
    def __init__(self):
        # Load the trained classification model
        self.model = load_model(MODEL_PATH)

        # Load class names in the same order used during training
        with open(CLASS_NAMES_PATH, "r", encoding="utf-8") as f:
            self.class_names = [line.strip() for line in f.readlines()]

    def predict(self, img_array):
        # Run prediction on the prepared image
        preds = self.model.predict(img_array, verbose=0)[0]

        # Get the class with the highest probability
        pred_idx = int(np.argmax(preds))
        pred_class = self.class_names[pred_idx]
        confidence = float(preds[pred_idx])

        # Also get the top 3 predicted classes
        top3_idx = np.argsort(preds)[-3:][::-1]
        top3 = [
            {
                "class": self.class_names[i],
                "confidence": float(preds[i])
            }
            for i in top3_idx
        ]

        # Return the final prediction details
        return {
            "pred_index": pred_idx,
            "predicted_class": pred_class,
            "confidence": confidence,
            "top3": top3
        }