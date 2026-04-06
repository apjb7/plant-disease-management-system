import cv2
import numpy as np
from app.config import HEATMAP_THRESHOLD, MILD_THRESHOLD, MODERATE_THRESHOLD

def segment_leaf_mask(image_rgb):
    image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)

    lower_green = np.array([20, 30, 20])
    upper_green = np.array([100, 255, 255])

    mask = cv2.inRange(hsv, lower_green, upper_green)

    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    return mask

def create_disease_mask_from_heatmap(heatmap, image_shape, threshold=HEATMAP_THRESHOLD):
    heatmap_resized = cv2.resize(heatmap, (image_shape[1], image_shape[0]))
    disease_mask = (heatmap_resized >= threshold).astype(np.uint8) * 255
    return disease_mask

def compute_severity(leaf_mask, disease_mask):
    leaf_binary = (leaf_mask > 0).astype(np.uint8)
    disease_binary = (disease_mask > 0).astype(np.uint8)

    affected_mask = leaf_binary * disease_binary

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
    overlay = image_rgb.copy()
    mask_bool = mask > 0

    color_layer = np.zeros_like(image_rgb)
    color_layer[:, :] = color

    overlay[mask_bool] = cv2.addWeighted(
        image_rgb[mask_bool], 1 - alpha,
        color_layer[mask_bool], alpha,
        0
    )
    return overlay