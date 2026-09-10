"""
Evidence ledger service (Phase 21-22).

Every pipeline stage (detection, characterization, environment, drift, origin,
AIS, attribution, report) appends a structured EvidenceRecord to the incident
ledger so the analyst sees exactly what was observed/inferred/simulated, with
provenance, confidence, and status label.
"""

from typing import Any, Dict, Optional
from datetime import datetime, timezone
from app.core.status import StatusLabel, DataQuality, make_provenance
from app.schemas.evidence import EvidenceRecordCreate
from app.repositories.evidence_repo import EvidenceRepository
from app.core.logging import logger


class EvidenceService:
    """Creates stage-specific evidence records for an incident."""

    @staticmethod
    def _record(db, *, incident_id: str, stage: str, source: str, source_version: str,
                status_label: str, confidence: float, timestamp: datetime, title: str,
                summary: str, value: Dict[str, Any], provenance: Dict[str, Any],
                related_entity_type: Optional[str], related_entity_id: Optional[str]):
        if not incident_id:
            logger.warning("EvidenceService skipped record: no incident_id (%s, %s)", stage, title)
            return None
        try:
            data = EvidenceRecordCreate(
                incident_id=incident_id,
                evidence_type=stage,
                source=source,
                source_version=source_version,
                status_label=status_label,
                confidence=confidence,
                timestamp=timestamp,
                title=title,
                summary=summary,
                value=value,
                provenance=provenance,
                related_entity_type=related_entity_type,
                related_entity_id=related_entity_id,
            )
            return EvidenceRepository.create(db, data)
        except Exception as e:  # evidence recording must never break the pipeline
            logger.error(f"Evidence recording failed ({stage}): {e}")
            return None

    @classmethod
    def record_detection(cls, db, *, incident_id: str, scene_id: str, model_id: str,
                         model_version: str, confidence: float, oil_pixel_count: int,
                         artifact_path: str, status_label: str, slick_ids: list,
                         extra: Optional[Dict[str, Any]] = None,
                         timestamp: Optional[datetime] = None) -> Any:
        return cls._record(
            db,
            incident_id=incident_id,
            stage="DETECTION",
            source="Sentinel-1 C-SAR",
            source_version="v1",
            status_label=status_label,
            confidence=confidence,
            timestamp=timestamp or datetime.now(timezone.utc),
            title="Oil spill detection (ML segmentation)",
            summary=f"LLM detector produced {len(slick_ids)} slick polygons with confidence {confidence:.3f} "
                    f"({oil_pixel_count} oil pixels, threshold-calibrated).",
            value={"scene_id": scene_id, "model_id": model_id, "model_version": model_version,
                   "confidence": confidence, "oil_pixel_count": oil_pixel_count,
                   "artifact_path": artifact_path, "slick_ids": slick_ids,
                   **(extra or {})},
            provenance=make_provenance(
                source="Sentinel-1 C-SAR", source_version="v1",
                processing_stage="detection", model_id=model_id, model_version=model_version,
                config={"artifact": artifact_path}),
            related_entity_type="scene",
            related_entity_id=scene_id,
        )

    @classmethod
    def record_characterization(cls, db, *, incident_id: str, slick_id: str, area_km2: float,
                                confidence: float, char_value: Dict[str, Any],
                                timestamp: Optional[datetime] = None) -> Any:
        return cls._record(
            db,
            incident_id=incident_id, stage="SLICK", source="MARINeX-Characterizer",
            source_version="v1", status_label=StatusLabel.ML_SEGMENTED.value,
            confidence=confidence, timestamp=timestamp or datetime.now(timezone.utc),
            title="Slick characterization",
            summary=f"Slick {slick_id}: area {area_km2:.2f} km2 (geodesic), eccentricity/compactness computed.",
            value=char_value,
            provenance=make_provenance(source="Sentinel-1 C-SAR", source_version="v1",
                                       processing_stage="characterization",
                                       model_version="characterizer_v1"),
            related_entity_type="slick", related_entity_id=slick_id,
        )

    @classmethod
    def record_environment(cls, db, *, incident_id: str, slick_id: str, env, quality: DataQuality,
                           timestamp: Optional[datetime] = None) -> Any:
        env_value = {
            "wind_u_mps": env.wind.u_component_mps if hasattr(env, "wind") else None,
            "wind_v_mps": env.wind.v_component_mps if hasattr(env, "wind") else None,
            "current_u_mps": env.ocean_current.u_component_mps if hasattr(env, "ocean_current") else None,
            "current_v_mps": env.ocean_current.v_component_mps if hasattr(env, "ocean_current") else None,
            "provider": getattr(env, "provider", "MOCK"),
            "quality": quality.value if hasattr(quality, "value") else str(quality),
        }
        return cls._record(
            db,
            incident_id=incident_id, stage="ENVIRONMENT", source="ERA5/CMEMS",
            source_version="v1", status_label=StatusLabel.SIMULATED.value,
            confidence=0.7, timestamp=timestamp or datetime.now(timezone.utc),
            title="Environmental conditions (wind + current)",
            summary=f"Environment provider {env_value['provider']} with quality {env_value['quality']}.",
            value=env_value,
            provenance=make_provenance(source="ERA5/CMEMS", source_version="v1",
                                       processing_stage="environment", config={"provider": env_value["provider"]}),
            related_entity_type="slick", related_entity_id=slick_id,
        )

    @classmethod
    def record_drift(cls, db, *, incident_id: str, slick_id: str, sim, timestamp: Optional[datetime] = None) -> Any:
        origin = sim.probable_origin_centroid if hasattr(sim, "probable_origin_centroid") else None
        return cls._record(
            db,
            incident_id=incident_id, stage="DRIFT", source=sim.model_name,
            source_version="v1", status_label=StatusLabel.SIMULATED.value,
            confidence=0.7, timestamp=timestamp or datetime.now(timezone.utc),
            title=f"Drift {'hindcast' if sim.direction == 'HINDCAST' else 'forecast'} simulation",
            summary=f"Lagrangian drift simulation from slick centroid -> probable origin "
                    f"{origin} at {getattr(sim, 'probable_origin_time', None)}.",
            value={"direction": sim.direction, "origin_centroid": origin,
                   "origin_time": getattr(sim, "probable_origin_time", None),
                   "model": sim.model_name, "parameters": getattr(sim, "parameters", {}),
                   "uncertainty": getattr(sim, "uncertainty", {})},
            provenance=make_provenance(source=sim.model_name, source_version="v1",
                                       processing_stage="drift", config={"direction": sim.direction}),
            related_entity_type="slick", related_entity_id=slick_id,
        )

    @classmethod
    def record_ais(cls, db, *, incident_id: str, slick_id: str, vessel_count: int,
                   query_window: Dict[str, Any], timestamp: Optional[datetime] = None) -> Any:
        return cls._record(
            db,
            incident_id=incident_id, stage="AIS", source="MarineCadastre AIS",
            source_version="v1", status_label=StatusLabel.TRACKED.value,
            confidence=0.9, timestamp=timestamp or datetime.now(timezone.utc),
            title="AIS trajectory correlation window",
            summary=f"{vessel_count} vessel trajectory reports found in spatial-temporal window.",
            value={"vessel_count": vessel_count, **query_window},
            provenance=make_provenance(source="MarineCadastre AIS", source_version="v1",
                                       processing_stage="ais", config=query_window),
            related_entity_type="slick", related_entity_id=slick_id,
        )

    @classmethod
    def record_attribution(cls, db, *, incident_id: str, slick_id: str, results,
                           timestamp: Optional[datetime] = None) -> Any:
        top = results.candidates[0] if results.candidates else None
        return cls._record(
            db,
            incident_id=incident_id, stage="CANDIDATE", source="MARINeX-Attribution",
            source_version="v1", status_label=StatusLabel.CANDIDATE.value,
            confidence=top.overall_score / 100.0 if top else 0.0,
            timestamp=timestamp or datetime.now(timezone.utc),
            title="Vessel attribution ranking",
            summary=(f"Top candidate {top.vessel.vessel_name if top else 'NONE'} score "
                     f"{top.overall_score:.1f}/100 (CANDIDATE, not guilt).")
                    if top else "No candidate vessels found.",
            value={"ranking": [
                {"rank": c.rank, "vessel_name": c.vessel.vessel_name, "mmsi": c.vessel.mmsi,
                 "overall_score": c.overall_score, "factors": {
                     "proximity": c.factors.proximity_score, "temporal": c.factors.temporal_score,
                     "trajectory": c.factors.trajectory_score, "behavior": c.factors.behavior_score}}
                for c in results.candidates]},
            provenance=make_provenance(source="MARINeX-Attribution", source_version="v1",
                                       processing_stage="attribution",
                                       config={"weights": results.weights if hasattr(results, "weights") else {}}),
            related_entity_type="slick", related_entity_id=slick_id,
        )