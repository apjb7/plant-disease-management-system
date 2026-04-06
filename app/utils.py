from pathlib import Path
import cv2
import numpy as np

def ensure_directories(paths):
    for path in paths:
        Path(path).mkdir(parents=True, exist_ok=True)

def load_image_rgb(image_path):
    img_bgr = cv2.imread(str(image_path))
    if img_bgr is None:
        raise ValueError(f"Could not read image: {image_path}")
    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

def prepare_model_input(image_rgb, img_size):
    resized = cv2.resize(image_rgb, img_size)
    img_array = resized.astype(np.float32)
    img_array = np.expand_dims(img_array, axis=0)
    return resized, img_array

def save_rgb_image(image_rgb, save_path):
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(save_path), image_bgr)