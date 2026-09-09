import math
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import numpy as np
from app.utils.geo import (
    create_convex_hull_geojson,
    haversine_km,
)
from app.schemas.drift import DriftSimulationRequest, DriftSimulationResponse
from app.core.logging import logger


class DriftSimulationService(ABC):
    """
    Abstract interface for Marine Oil Drift and Hindcasting Simulation.
    Enables swapping between the Lagrangian baseline and OpenDrift / OpenOil engines.
    """

    @abstractmethod
    def simulate(
        self,
        slick_id: str,
        centroid: List[float],
        start_time: datetime,
        req: DriftSimulationRequest,
        wind_u: float,
        wind_v: float,
        current_u: float,
        current_v: float,
    ) -> DriftSimulationResponse:
        pass


class MockDriftService(DriftSimulationService):
    """
    Lagrangian Particle Drift Simulation Service (Baseline / Hindcasting Engine).

    Features:
    - Backward-in-time trajectory integration (hindcast) to infer spill release location and time.
    - Combined advection using ocean current vectors + leeway wind drift factor (~3.2%).
    - Stochastic horizontal turbulent eddy diffusion modeling uncertainty growth over time.
    - Produces a probable origin centroid, uncertainty polygon (convex hull), and particle dispersion cloud.

    DISCLAIMER:
    This baseline model is intended for demonstration, testing, and initial triage.
    It does not incorporate full 3D hydrodynamic wave-induced Stokes drift or evaporation weathering
    which will be handled by the future OpenDrift/OpenOil adapter.
    """

    def __init__(self, default_wind_factor: float = 0.032, default_diffusion: float = 10.0):
        self.default_wind_factor = default_wind_factor
        self.default_diffusion = default_diffusion

    def simulate(
        self,
        slick_id: str,
        centroid: List[float],  # [lon, lat]
        start_time: datetime,
        req: DriftSimulationRequest,
        wind_u: float,
        wind_v: float,
        current_u: float,
        current_v: float,
    ) -> DriftSimulationResponse:
        sim_id = f"drift_sim_{slick_id[:16]}_{uuid.uuid4().hex[:6]}"
        duration_seconds = int(req.duration_hours * 3600)
        dt = req.time_step_seconds
        num_steps = max(1, duration_seconds // dt)
        num_particles = req.num_particles

        wind_factor = req.wind_drift_factor or self.default_wind_factor
        diffusion = req.diffusion_coefficient if req.diffusion_coefficient is not None else self.default_diffusion

        # Use overrides if provided
        w_u = req.custom_wind_u if req.custom_wind_u is not None else wind_u
        w_v = req.custom_wind_v if req.custom_wind_v is not None else wind_v
        c_u = req.custom_current_u if req.custom_current_u is not None else current_u
        c_v = req.custom_current_v if req.custom_current_v is not None else current_v

        # Net drift velocity vector (m/s)
        # v_total = v_current + alpha * v_wind
        u_drift = c_u + wind_factor * w_u
        v_drift = c_v + wind_factor * w_v

        is_hindcast = req.direction.upper() == "HINDCAST"
        # If hindcast, propagate backwards in time
        direction_sign = -1.0 if is_hindcast else 1.0

        # Initial particle positions centered around slick centroid [lon, lat]
        init_lon, init_lat = centroid[0], centroid[1]
        mean_lat_rad = math.radians(init_lat)
        m_per_deg_lat = 111132.0
        m_per_deg_lon = 111320.0 * math.cos(mean_lat_rad)

        # Initialize particles with a small initial slick radius perturbation
        rng = np.random.default_rng(42)
        p_x = rng.normal(0, 150.0, size=num_particles)
        p_y = rng.normal(0, 150.0, size=num_particles)

        # Diffusion step size in meters: sigma = sqrt(2 * D * dt)
        diffusion_sigma = math.sqrt(2.0 * max(0.1, diffusion) * dt)

        # Track mean centerline trajectory
        trajectory_coords: List[List[float]] = [[round(init_lon, 5), round(init_lat, 5)]]

        # Integrate through time
        for step in range(num_steps):
            # Advection
            p_x += direction_sign * u_drift * dt
            p_y += direction_sign * v_drift * dt

            # Turbulent diffusion perturbation
            p_x += rng.normal(0, diffusion_sigma, size=num_particles)
            p_y += rng.normal(0, diffusion_sigma, size=num_particles)

            # Record trajectory waypoint
            mean_x_m = float(np.mean(p_x))
            mean_y_m = float(np.mean(p_y))
            waypoint_lon = init_lon + mean_x_m / m_per_deg_lon
            waypoint_lat = init_lat + mean_y_m / m_per_deg_lat
            trajectory_coords.append([round(waypoint_lon, 5), round(waypoint_lat, 5)])

        # Final end time
        if is_hindcast:
            end_time = start_time - timedelta(seconds=duration_seconds)
            origin_time = end_time
            origin_lon = float(np.mean(p_x)) / m_per_deg_lon + init_lon
            origin_lat = float(np.mean(p_y)) / m_per_deg_lat + init_lat
        else:
            end_time = start_time + timedelta(seconds=duration_seconds)
            origin_time = start_time
            origin_lon = init_lon
            origin_lat = init_lat

        # Final particle coordinates in WGS84
        p_lons = init_lon + p_x / m_per_deg_lon
        p_lats = init_lat + p_y / m_per_deg_lat
        final_points = [[float(lo), float(la)] for lo, la in zip(p_lons, p_lats)]

        # Origin uncertainty polygon: convex hull around final dispersed particles
        origin_poly_geojson = create_convex_hull_geojson(final_points)

        # Particle subsample for front-end rendering (up to 80 particles to keep payload light)
        particle_samples = []
        step_stride = max(1, num_particles // 80)
        for i in range(0, num_particles, step_stride):
            particle_samples.append({
                "particle_id": i,
                "coordinates": [round(float(p_lons[i]), 5), round(float(p_lats[i]), 5)],
                "timestamp": end_time.isoformat(),
                "status": "active",
            })

        trajectory_geojson = {
            "type": "LineString",
            "coordinates": trajectory_coords,
        }

        # Hindcast drift distance
        total_drift_km = haversine_km(init_lat, init_lon, origin_lat, origin_lon)

        uncertainty_meta = {
            "diffusion_radius_km": round(float(np.std(p_x) / 1000.0) * 1.96, 2),
            "confidence_interval": "95%",
            "total_drift_distance_km": round(total_drift_km, 2),
            "drift_speed_knots": round(math.sqrt(u_drift**2 + v_drift**2) * 1.94384, 2),
        }

        return DriftSimulationResponse(
            id=sim_id,
            slick_id=slick_id,
            direction=req.direction.upper(),
            start_time=start_time,
            end_time=end_time,
            model_name="LAGRANGIAN_MONTE_CARLO_DRIFT_v1",
            parameters={
                "duration_hours": req.duration_hours,
                "time_step_seconds": dt,
                "num_particles": num_particles,
                "wind_drift_factor": wind_factor,
                "diffusion_coefficient": diffusion,
                "net_u_mps": round(u_drift, 3),
                "net_v_mps": round(v_drift, 3),
                "is_baseline": True,
            },
            origin_geometry=origin_poly_geojson,
            trajectory_geometry=trajectory_geojson,
            particles=particle_samples,
            uncertainty=uncertainty_meta,
            probable_origin_time=origin_time,
            probable_origin_centroid=[round(origin_lon, 5), round(origin_lat, 5)],
            status="COMPLETED",
            created_at=datetime.now(timezone.utc),
        )
