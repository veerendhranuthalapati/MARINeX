from typing import List, Tuple, Dict, Any, Optional
import numpy as np
from PIL import Image
from scipy.ndimage import label, binary_opening, binary_closing, generate_binary_structure


def load_image_to_grayscale_array(image_source: Any) -> np.ndarray:
    """Load an image file path or bytes to a 2D float32 numpy array."""
    if isinstance(image_source, str):
        img = Image.open(image_source).convert("L")
    elif isinstance(image_source, bytes):
        import io
        img = Image.open(io.BytesIO(image_source)).convert("L")
    elif isinstance(image_source, np.ndarray):
        if image_source.ndim == 3:
            return np.mean(image_source, axis=2).astype(np.float32)
        return image_source.astype(np.float32)
    elif isinstance(image_source, Image.Image):
        img = image_source.convert("L")
    else:
        raise ValueError(f"Unsupported image source type: {type(image_source)}")

    return np.array(img, dtype=np.float32)


def otsu_threshold(gray: np.ndarray) -> float:
    """
    Compute Otsu's optimal threshold value for grayscale image.
    Minimizes intra-class variance between dark regions and background.
    """
    pixels = gray.ravel()
    hist, bin_edges = np.histogram(pixels, bins=256, range=(0, 256))
    hist = hist.astype(np.float32)
    total_pixels = len(pixels)

    if total_pixels == 0:
        return 128.0

    current_max = 0.0
    threshold = 0.0
    sum_total = np.dot(np.arange(256), hist)
    sum_background = 0.0
    weight_background = 0.0

    for i in range(256):
        weight_background += hist[i]
        if weight_background == 0:
            continue
        weight_foreground = total_pixels - weight_background
        if weight_foreground == 0:
            break

        sum_background += i * hist[i]
        mean_background = sum_background / weight_background
        mean_foreground = (sum_total - sum_background) / weight_foreground

        # Between-class variance
        between_var = weight_background * weight_foreground * (mean_background - mean_foreground) ** 2
        if between_var > current_max:
            current_max = between_var
            threshold = bin_edges[i]

    return float(threshold)


def mask_to_polygon_coordinates(
    binary_mask: np.ndarray,
    bbox: List[float],
    min_pixels: int = 50
) -> List[List[List[float]]]:
    """
    Extract polygons from a binary mask (where True = slick) and map pixel coordinates
    to geographic [lon, lat] coordinates according to bbox [min_lon, min_lat, max_lon, max_lat].
    """
    struct = generate_binary_structure(2, 2)
    labeled, num_features = label(binary_mask, structure=struct)
    if num_features == 0:
        return []

    height, width = binary_mask.shape
    min_lon, min_lat, max_lon, max_lat = bbox

    polygons = []
    # Identify components larger than min_pixels
    for feature_id in range(1, num_features + 1):
        component = (labeled == feature_id)
        pixel_count = np.sum(component)
        if pixel_count < min_pixels:
            continue

        # Extract boundary points
        y_indices, x_indices = np.where(component)
        if len(x_indices) < 3:
            continue

        # Convert to geographical coords
        # Longitude: x / (width - 1) * (max_lon - min_lon) + min_lon
        # Latitude: (1.0 - y / (height - 1)) * (max_lat - min_lat) + min_lat  (image y grows downward)
        lons = min_lon + (x_indices / max(1, width - 1)) * (max_lon - min_lon)
        lats = max_lat - (y_indices / max(1, height - 1)) * (max_lat - min_lat)

        # Compute convex hull or approximate simplified perimeter
        from app.utils.geo import create_convex_hull_geojson
        pts = [[float(lo), float(la)] for lo, la in zip(lons, lats)]
        # Sample points if too large
        if len(pts) > 400:
            step = len(pts) // 300
            pts = pts[::step]

        hull_geom = create_convex_hull_geojson(pts)
        if hull_geom and "coordinates" in hull_geom:
            polygons.append(hull_geom["coordinates"][0])

    return polygons
