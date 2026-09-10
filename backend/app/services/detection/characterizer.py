import math
from typing import List, Dict, Any, Optional
from shapely.geometry import Polygon, Point
from app.utils.geo import (
    calculate_polygon_geodesic_area_km2,
    calculate_polygon_perimeter_km,
    haversine_km,
)
from app.schemas.slick import SlickCharacterization


class SlickCharacterizer:
    """
    Computes geometric, spatial, and morphometric attributes of detected oil slicks.
    Generates standardized characterization profiles and GeoJSON representations.
    """

    @staticmethod
    def characterize_polygon(
        coords: List[List[float]],
        confidence: float = 0.85,
        attributes: Optional[Dict[str, Any]] = None
    ) -> SlickCharacterization:
        """
        Calculate area, perimeter, centroid, bounding box, length, width, orientation, and compactness
        from WGS84 polygon coordinate ring [[lon, lat], ...].
        """
        if not coords or len(coords) < 3:
            raise ValueError("A valid polygon requires at least 3 coordinates.")

        # Ensure ring is closed
        ring = coords if coords[0] == coords[-1] else coords + [coords[0]]
        poly = Polygon(ring)

        # 1. Geodesic Area and Perimeter
        area_km2 = calculate_polygon_geodesic_area_km2(ring)
        perimeter_km = calculate_polygon_perimeter_km(ring)

        # 2. Centroid
        centroid_lon = float(poly.centroid.x)
        centroid_lat = float(poly.centroid.y)

        # 3. Axis-aligned Bounding Box [min_lon, min_lat, max_lon, max_lat]
        min_lon, min_lat, max_lon, max_lat = poly.bounds

        # 4. Length, Width, Orientation via Minimum Rotated Rectangle
        mrr = poly.minimum_rotated_rectangle
        mrr_coords = list(mrr.exterior.coords)

        # Compute side lengths in km
        side1_km = haversine_km(mrr_coords[0][1], mrr_coords[0][0], mrr_coords[1][1], mrr_coords[1][0])
        side2_km = haversine_km(mrr_coords[1][1], mrr_coords[1][0], mrr_coords[2][1], mrr_coords[2][0])

        length_km = max(side1_km, side2_km)
        width_km = min(side1_km, side2_km)

        # Eccentricity from rotated-rectangle axes: sqrt(1 - (w/l)^2), 0 = circle
        eccentricity = math.sqrt(max(0.0, 1.0 - (width_km / length_km) ** 2)) if length_km > 0 else 0.0

        # Calculate principal axis orientation (0 to 180 degrees clockwise from North)
        if side1_km >= side2_km:
            dx = mrr_coords[1][0] - mrr_coords[0][0]
            dy = mrr_coords[1][1] - mrr_coords[0][1]
        else:
            dx = mrr_coords[2][0] - mrr_coords[1][0]
            dy = mrr_coords[2][1] - mrr_coords[1][1]

        angle_rad = math.atan2(dx, dy)
        orientation_deg = math.degrees(angle_rad) % 180.0

        # 5. Compactness (Isoperimetric Quotient / Circularity): 4 * pi * Area / Perimeter^2
        if perimeter_km > 0:
            compactness = min(1.0, (4.0 * math.pi * area_km2) / (perimeter_km ** 2))
        else:
            compactness = 0.0

        return SlickCharacterization(
            area_km2=round(area_km2, 3),
            perimeter_km=round(perimeter_km, 3),
            centroid=[round(centroid_lon, 5), round(centroid_lat, 5)],
            bounding_box=[round(min_lon, 4), round(min_lat, 4), round(max_lon, 4), round(max_lat, 4)],
            length_km=round(length_km, 3),
            width_km=round(width_km, 3),
            orientation_deg=round(orientation_deg, 1),
            compactness=round(compactness, 4),
            eccentricity=round(eccentricity, 4),
            confidence=round(confidence, 3),
            attributes=attributes or {},
        )

    @staticmethod
    def to_geojson_feature(
        slick_id: str,
        scene_id: str,
        coords: List[List[float]],
        characterization: SlickCharacterization,
        detection_method: str = "CLASSICAL_BASELINE_ADAPTIVE_THRESHOLD"
    ) -> Dict[str, Any]:
        """Format characterized slick into RFC 7946 GeoJSON Feature."""
        ring = coords if coords[0] == coords[-1] else coords + [coords[0]]
        return {
            "type": "Feature",
            "id": slick_id,
            "properties": {
                "slick_id": slick_id,
                "scene_id": scene_id,
                "detection_method": detection_method,
                "area_km2": characterization.area_km2,
                "perimeter_km": characterization.perimeter_km,
                "centroid": characterization.centroid,
                "length_km": characterization.length_km,
                "width_km": characterization.width_km,
                "orientation_deg": characterization.orientation_deg,
                "compactness": characterization.compactness,
                "confidence": characterization.confidence,
                "attributes": characterization.attributes,
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [ring],
            },
        }
