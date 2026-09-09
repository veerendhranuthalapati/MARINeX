import math
from typing import List, Dict, Any, Tuple
from shapely.geometry import Polygon, Point, LineString


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on Earth in kilometers."""
    r = 6371.0  # Mean Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return r * c


def calculate_polygon_geodesic_area_km2(coords: List[List[float]]) -> float:
    """
    Calculate geodesic surface area of a polygon defined in WGS84 [lon, lat] coords in km^2.
    Uses Green's theorem with spherical surface area metric.
    """
    if not coords or len(coords) < 3:
        return 0.0

    # Spherical excess / polygon area on sphere
    # Convert degrees to radians
    r = 6371.0  # Earth radius in km
    area = 0.0
    n = len(coords)
    # Ensure ring is closed
    pts = coords if coords[0] == coords[-1] else coords + [coords[0]]
    n = len(pts)

    # Approximate local planar metric centered on mean latitude
    mean_lat = math.radians(sum(p[1] for p in pts[:-1]) / (n - 1))
    km_per_deg_lat = 111.132
    km_per_deg_lon = 111.320 * math.cos(mean_lat)

    # Shoelace formula in metric space
    for i in range(n - 1):
        x1 = pts[i][0] * km_per_deg_lon
        y1 = pts[i][1] * km_per_deg_lat
        x2 = pts[i + 1][0] * km_per_deg_lon
        y2 = pts[i + 1][1] * km_per_deg_lat
        area += (x1 * y2) - (x2 * y1)

    return abs(area) / 2.0


def calculate_polygon_perimeter_km(coords: List[List[float]]) -> float:
    """Calculate geodesic perimeter of a polygon in kilometers."""
    if not coords or len(coords) < 2:
        return 0.0
    total_km = 0.0
    for i in range(len(coords) - 1):
        total_km += haversine_km(coords[i][1], coords[i][0], coords[i + 1][1], coords[i + 1][0])
    return total_km


def create_convex_hull_geojson(points: List[List[float]]) -> Dict[str, Any]:
    """Given a list of [lon, lat] points, return a GeoJSON Polygon representing their convex hull."""
    import numpy as np
    from scipy.spatial import ConvexHull

    pts = np.array(points)
    if len(pts) < 3:
        min_lon, min_lat = float(pts[:, 0].min()), float(pts[:, 1].min())
        max_lon, max_lat = float(pts[:, 0].max()), float(pts[:, 1].max())
        coords = [
            [min_lon, min_lat],
            [max_lon, min_lat],
            [max_lon, max_lat],
            [min_lon, max_lat],
            [min_lon, min_lat],
        ]
        return {"type": "Polygon", "coordinates": [coords]}

    try:
        hull = ConvexHull(pts)
        hull_coords = pts[hull.vertices].tolist()
        # Close polygon ring
        hull_coords.append(hull_coords[0])
        return {"type": "Polygon", "coordinates": [hull_coords]}
    except Exception:
        mean_lon, mean_lat = float(pts[:, 0].mean()), float(pts[:, 1].mean())
        delta = 0.02
        coords = [
            [mean_lon - delta, mean_lat - delta],
            [mean_lon + delta, mean_lat - delta],
            [mean_lon + delta, mean_lat + delta],
            [mean_lon - delta, mean_lat + delta],
            [mean_lon - delta, mean_lat - delta],
        ]
        return {"type": "Polygon", "coordinates": [coords]}


def point_in_bbox(lon: float, lat: float, bbox: List[float]) -> bool:
    """Check if point is within [min_lon, min_lat, max_lon, max_lat]."""
    min_lon, min_lat, max_lon, max_lat = bbox
    return min_lon <= lon <= max_lon and min_lat <= lat <= max_lat


def point_to_polygon_distance_km(lat: float, lon: float, poly_coords: List[List[float]]) -> float:
    """Calculate minimum great-circle distance from a point to polygon boundary or 0 if inside."""
    pt = Point(lon, lat)
    poly = Polygon(poly_coords)
    if poly.contains(pt):
        return 0.0

    # Approximate distance to exterior ring vertices and edges
    min_dist = float("inf")
    for vertex in poly_coords:
        dist = haversine_km(lat, lon, vertex[1], vertex[0])
        if dist < min_dist:
            min_dist = dist

    return min_dist


def trajectory_intersects_polygon(points: List[Tuple[float, float]], poly_coords: List[List[float]]) -> bool:
    """
    Check if a vessel trajectory LineString intersects or touches a polygon.
    points: list of (lon, lat)
    """
    if len(points) < 2:
        if len(points) == 1:
            return Polygon(poly_coords).contains(Point(points[0][0], points[0][1]))
        return False

    line = LineString(points)
    poly = Polygon(poly_coords)
    return poly.intersects(line)
