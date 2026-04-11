from pathlib import Path
import cv2
import numpy as np

def ensure_directories(paths):
    # Create each folder if it does not already exist
    for path in paths:
        Path(path).mkdir(parents=True, exist_ok=True)

def load_image_rgb(image_path):
    # Read the image with OpenCV
    img_bgr = cv2.imread(str(image_path))
    
    # Stop if the image could not be loaded
    if img_bgr is None:
        raise ValueError(f"Could not read image: {image_path}")
    
    # Convert from BGR to RGB before returning
    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

def prepare_model_input(image_rgb, img_size):
    # Resize the image to match the model input size
    resized = cv2.resize(image_rgb, img_size)
    
    # Convert to float for model processing
    img_array = resized.astype(np.float32)
    
    # Add batch dimension so the model can accept it
    img_array = np.expand_dims(img_array, axis=0)
    
    return resized, img_array

def save_rgb_image(image_rgb, save_path):
    # Make sure the destination folder exists
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert back to BGR because OpenCV saves in BGR format
    image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(save_path), image_bgr)

def safe_filename(name: str) -> str:
    # Keep only simple filename characters and replace the rest
    keep = []
    for ch in name:
        if ch.isalnum() or ch in ("_", "-", "."):
            keep.append(ch)
        else:
            keep.append("_")
    return "".join(keep)