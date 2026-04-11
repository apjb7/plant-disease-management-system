import cv2
import numpy as np
from app.config import HEATMAP_THRESHOLD, MILD_THRESHOLD, MODERATE_THRESHOLD
def segment_leaf_mask(image_rgb):
    """
    Broader leaf segmentation:
    includes green + yellow + brown plant tissue.
    This works better for diseased leaves than green-only masking.
    """
    image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_RGB2HSV)

    # Green healthy tissue
    lower_green = np.array([20, 25, 20])
    upper_green = np.array([95, 255, 255])
    mask_green = cv2.inRange(hsv, lower_green, upper_green)

    # Yellow/chlorotic tissue
    lower_yellow = np.array([10, 20, 20])
    upper_yellow = np.array([35, 255, 255])
    mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)

    # Brown necrotic tissue
    lower_brown = np.array([5, 20, 10])
    upper_brown = np.array([25, 255, 180])
    mask_brown = cv2.inRange(hsv, lower_brown, upper_brown)

    # Combine all plant tissue masks
    mask = cv2.bitwise_or(mask_green, mask_yellow)
    mask = cv2.bitwise_or(mask, mask_brown)

    # Clean up
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # Keep the largest connected component only
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if num_labels > 1:
        largest_label = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
        mask = np.where(labels == largest_label, 255, 0).astype(np.uint8)

    return mask

def create_disease_mask_from_heatmap(heatmap, image_shape, threshold=0.25):
    """
    Lower threshold than before because 0.4 is often too strict.
    """
    heatmap_resized = cv2.resize(heatmap, (image_shape[1], image_shape[0]))
    disease_mask = (heatmap_resized >= threshold).astype(np.uint8) * 255

    # Optional cleanup
    kernel = np.ones((5, 5), np.uint8)
    disease_mask = cv2.morphologyEx(disease_mask, cv2.MORPH_OPEN, kernel)
    disease_mask = cv2.morphologyEx(disease_mask, cv2.MORPH_CLOSE, kernel)

    return disease_mask


def compute_severity(leaf_mask, disease_mask):
    if leaf_mask is None or disease_mask is None:
        return np.zeros((300, 300), dtype=np.uint8), 0, 0, 0.0

    leaf_binary = (leaf_mask > 0).astype(np.uint8)
    disease_binary = (disease_mask > 0).astype(np.uint8)

    affected_mask = (leaf_binary * disease_binary).astype(np.uint8)

    leaf_pixels = int(np.sum(leaf_binary))
    affected_pixels = int(np.sum(affected_mask))

    if leaf_pixels == 0:
        severity_percent = 0.0
    else:
        severity_percent = (affected_pixels / leaf_pixels) * 100.0

    return affected_mask, leaf_pixels, affected_pixels, severity_percent


def severity_label_from_percent(severity_percent):
    if severity_percent < MILD_THRESHOLD:
        return "Mild"
    elif severity_percent < MODERATE_THRESHOLD:
        return "Moderate"
    return "Severe"


def overlay_mask_on_image(image_rgb, mask, color=(255, 0, 0), alpha=0.35):
    image_rgb = image_rgb.copy()

    if mask is None:
        return image_rgb

    mask_bool = mask > 0

    color_layer = np.zeros_like(image_rgb, dtype=np.uint8)
    color_layer[:, :] = color

    blended = cv2.addWeighted(
        image_rgb.astype(np.uint8), 1 - alpha,
        color_layer, alpha,
        0
    )

    output = image_rgb.astype(np.uint8).copy()
    output[mask_bool] = blended[mask_bool]

    return output