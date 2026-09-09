import pytest
from app.utils.geo import (
    haversine_km,
    calculate_polygon_geodesic_area_km2,
    calculate_polygon_perimeter_km,
    point_in_bbox,
    point_to_polygon_distance_km,
    trajectory_intersects_polygon,
    create_convex_hull_geojson,
)
from app.services.detection.characterizer import SlickCharacterizer


def test_haversine_distance():
    # Mumbai to Goa is approximately 435-440 km
    dist = haversine_km(18.922, 72.834, 15.299, 74.124)
    assert 420.0 < dist < 460.0

    # Same point distance is 0
    assert haversine_km(19.34, 71.41, 19.34, 71.41) == 0.0


def test_polygon_area_and_perimeter(sample_slick_polygon):
    area = calculate_polygon_geodesic_area_km2(sample_slick_polygon)
    assert area > 0.0
    # The sample polygon is an elongated slick with area roughly 5-25 km²
    assert 1.0 < area < 30.0

    perimeter = calculate_polygon_perimeter_km(sample_slick_polygon)
    assert perimeter > 5.0


def test_point_in_bbox():
    bbox = [71.0, 19.0, 72.0, 20.0]
    assert point_in_bbox(71.5, 19.5, bbox) is True
    assert point_in_bbox(70.5, 19.5, bbox) is False
    assert point_in_bbox(71.5, 20.5, bbox) is False


def test_point_to_polygon_distance(sample_slick_polygon):
    # Point inside or right on centroid
    dist_near = point_to_polygon_distance_km(19.345, 71.418, sample_slick_polygon)
    assert dist_near == 0.0 or dist_near < 1.0

    # Point far away
    dist_far = point_to_polygon_distance_km(19.900, 72.000, sample_slick_polygon)
    assert dist_far > 50.0


def test_trajectory_intersects_polygon(sample_slick_polygon):
    # Line that cuts across the slick
    line_crossing = [(71.370, 19.310), (71.470, 19.380)]
    assert trajectory_intersects_polygon(line_crossing, sample_slick_polygon) is True

    # Line that is far to the east
    line_away = [(71.600, 19.200), (71.600, 19.500)]
    assert trajectory_intersects_polygon(line_away, sample_slick_polygon) is False


def test_convex_hull():
    pts = [
        [71.30, 19.30],
        [71.35, 19.32],
        [71.33, 19.38],
        [71.28, 19.35],
    ]
    hull = create_convex_hull_geojson(pts)
    assert hull["type"] == "Polygon"
    assert len(hull["coordinates"][0]) >= 4  # Closed polygon ring


def test_slick_characterizer(sample_slick_polygon):
    char = SlickCharacterizer.characterize_polygon(sample_slick_polygon, confidence=0.91)
    assert char.area_km2 > 0.0
    assert char.perimeter_km > 0.0
    assert len(char.centroid) == 2
    assert 71.0 < char.centroid[0] < 72.0
    assert 19.0 < char.centroid[1] < 20.0
    assert char.length_km > char.width_km
    assert 0.0 <= char.compactness <= 1.0
    assert char.confidence == 0.91

    feature = SlickCharacterizer.to_geojson_feature("slick_001", "scene_001", sample_slick_polygon, char)
    assert feature["type"] == "Feature"
    assert feature["id"] == "slick_001"
    assert feature["geometry"]["type"] == "Polygon"
    assert feature["properties"]["area_km2"] == char.area_km2
