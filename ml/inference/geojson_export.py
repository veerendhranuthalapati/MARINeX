"""
GeoJSON and Slick Vector Feature Extraction Module.
Converts raster segmentation masks into standard GeoJSON polygons with area and centroid properties.
"""

import cv2
import numpy as np
from typing import Dict, List, Any, Optional

def mask_to_geojson_features(
    binary_mask: np.ndarray,
    prob_map: Optional[np.ndarray] = None,
    geo_bounds: Optional[Dict[str, float]] = None,
    scene_id: str = "scene_unknown",
    pixel_size_meters: float = 10.0
) -> Dict[str, Any]:
    """
    Extracts polygon contours and packages them as standardized GeoJSON FeatureCollection.
    If geo_bounds (min_lat, min_lon, max_lat, max_lon) are provided, projects to geographic coordinates;
    otherwise preserves exact metric/pixel coordinates.
    """
    h, w = binary_mask.shape[:2]
    contours, _ = cv2.findContours(binary_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    features = []
    slick_id = 0

    has_geo = geo_bounds is not None and all(k in geo_bounds for k in ["min_lat", "min_lon", "max_lat", "max_lon"])

    for cnt in contours:
        area_px = float(cv2.contourArea(cnt))
        if area_px < 15:
            continue

        slick_id += 1
        pts = cnt.squeeze(1) # (N, 2) where col 0 is x, col 1 is y
        if len(pts) < 3:
            continue

        # Close polygon if not closed
        if not np.array_equal(pts[0], pts[-1]):
            pts = np.vstack([pts, pts[0]])

        # Centroid
        M = cv2.moments(cnt)
        if M["m00"] != 0:
            cx_px = float(M["m10"] / M["m00"])
            cy_px = float(M["m01"] / M["m00"])
        else:
            cx_px, cy_px = float(pts[:, 0].mean()), float(pts[:, 1].mean())

        # Confidence over slick area
        mask_roi = np.zeros((h, w), dtype=np.uint8)
        cv2.drawContours(mask_roi, [cnt], -1, 1, -1)
        if prob_map is not None:
            slick_conf = float(np.mean(prob_map[mask_roi == 1]))
        else:
            slick_conf = 0.90

        # Physical area calculation
        area_sqkm = (area_px * (pixel_size_meters ** 2)) / 1e6

        if has_geo:
            min_lat, max_lat = geo_bounds["min_lat"], geo_bounds["max_lat"]
            min_lon, max_lon = geo_bounds["min_lon"], geo_bounds["max_lon"]

            # Convert pixel coords to lat/lon
            geo_coords = []
            for x, y in pts:
                lon = min_lon + (x / w) * (max_lon - min_lon)
                lat = max_lat - (y / h) * (max_lat - min_lat)
                geo_coords.append([round(float(lon), 6), round(float(lat), 6)])

            centroid_lon = min_lon + (cx_px / w) * (max_lon - min_lon)
            centroid_lat = max_lat - (cy_px / h) * (max_lat - min_lat)

            feature = {
                "type": "Feature",
                "properties": {
                    "id": f"slick_{scene_id}_{slick_id:03d}",
                    "scene_id": scene_id,
                    "confidence": round(slick_conf, 4),
                    "area_pixels": int(area_px),
                    "area_sqkm": round(area_sqkm, 4),
                    "centroid_lat": round(float(centroid_lat), 6),
                    "centroid_lon": round(float(centroid_lon), 6),
                    "coordinate_type": "WGS-84"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [geo_coords]
                }
            }
        else:
            # Metric / Pixel coordinate feature
            pixel_coords = [[int(x), int(y)] for x, y in pts]
            feature = {
                "type": "Feature",
                "properties": {
                    "id": f"slick_{scene_id}_{slick_id:03d}",
                    "scene_id": scene_id,
                    "confidence": round(slick_conf, 4),
                    "area_pixels": int(area_px),
                    "area_sqkm": round(area_sqkm, 4),
                    "centroid_x": round(cx_px, 2),
                    "centroid_y": round(cy_px, 2),
                    "coordinate_type": "pixel_space"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [pixel_coords]
                }
            }

        features.append(feature)

    geojson_doc = {
        "type": "FeatureCollection",
        "scene_id": scene_id,
        "features": features
    }
    return geojson_doc
