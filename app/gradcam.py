import tensorflow as tf
import numpy as np
import cv2

from app.config import BASE_MODEL_NAME, LAST_CONV_LAYER_NAME

def make_gradcam_heatmap(img_array, model, pred_index=None):
    aug_layer = model.get_layer("sequential_1")
    base_model = model.get_layer(BASE_MODEL_NAME)
    last_conv_layer = base_model.get_layer(LAST_CONV_LAYER_NAME)

    conv_model = tf.keras.Model(
        inputs=base_model.input,
        outputs=last_conv_layer.output
    )

    classifier_input = tf.keras.Input(shape=last_conv_layer.output.shape[1:])
    x = classifier_input

    take = False
    for layer in base_model.layers:
        if layer.name == LAST_CONV_LAYER_NAME:
            take = True
            continue
        if take:
            x = layer(x)

    passed_backbone = False
    for layer in model.layers:
        if layer.name == BASE_MODEL_NAME:
            passed_backbone = True
            continue
        if passed_backbone:
            x = layer(x)

    classifier_model = tf.keras.Model(classifier_input, x)

    with tf.GradientTape() as tape:
        augmented = aug_layer(img_array, training=False)
        preprocessed = tf.keras.applications.efficientnet.preprocess_input(augmented)

        conv_outputs = conv_model(preprocessed)
        tape.watch(conv_outputs)

        predictions = classifier_model(conv_outputs)

        if pred_index is None:
            pred_index = tf.argmax(predictions[0])

        class_channel = predictions[:, pred_index]

    grads = tape.gradient(class_channel, conv_outputs)
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

    conv_outputs = conv_outputs[0]
    heatmap = conv_outputs @ pooled_grads[..., tf.newaxis]
    heatmap = tf.squeeze(heatmap)

    heatmap = tf.maximum(heatmap, 0)
    max_val = tf.reduce_max(heatmap)
    if max_val > 0:
        heatmap /= max_val

    return heatmap.numpy()

def overlay_gradcam_on_image(image_rgb, heatmap, alpha=0.4):
    heatmap_resized = cv2.resize(heatmap, (image_rgb.shape[1], image_rgb.shape[0]))
    heatmap_uint8 = np.uint8(255 * heatmap_resized)
    heatmap_color = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)
    heatmap_color = cv2.cvtColor(heatmap_color, cv2.COLOR_BGR2RGB)
    overlay = cv2.addWeighted(image_rgb, 1 - alpha, heatmap_color, alpha, 0)
    return overlay