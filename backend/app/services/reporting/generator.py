import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.schemas.slick import SlickResponse
from app.schemas.environment import EnvironmentalSnapshotResponse
from app.schemas.attribution import VesselCandidateResponse
from app.schemas.report import InvestigationReportResponse


class ReportGeneratorService:
    """
    Forensic Investigation Report Generation Service.
    Compiles multimodal evidence, sensor observations, drift hindcasts, and candidate vessel logs.
    Strictly separates observed facts, model predictions, assumptions, and limitations.
    """

    @staticmethod
    def generate_report(
        slick: SlickResponse,
        environmental: Optional[EnvironmentalSnapshotResponse],
        drift_data: Dict[str, Any],
        candidates: List[VesselCandidateResponse],
        analyst_name: str = "Lead Maritime Intelligence Analyst",
        analyst_notes: Optional[str] = None,
        priority_level: str = "HIGH",
    ) -> InvestigationReportResponse:
        report_id = f"REP-{slick.id[:8].upper()}-{datetime.now(timezone.utc).strftime('%Y%m%d')}"

        # 1. Observed Facts (Raw empirical data)
        observed_facts = [
            f"Satellite scene acquisition at {slick.detected_at.strftime('%Y-%m-%d %H:%M UTC')} confirmed surface anomaly.",
            f"Oil slick footprint measured at {slick.area_km2:.2f} km² with perimeter {slick.perimeter_km:.2f} km.",
            f"Geometric centroid located at latitude {slick.centroid[1]:.5f}° N, longitude {slick.centroid[0]:.5f}° E.",
            f"Detected using {slick.detection_method} with statistical confidence of {slick.confidence:.1%}.",
            f"AIS receivers logged {len(candidates)} active vessels in the designated maritime corridor during the investigation window.",
        ]

        # 2. Model Predictions (Hindcast and attribution outputs)
        origin_coords = drift_data.get("probable_origin_centroid", slick.centroid)
        origin_time_str = drift_data.get("probable_origin_time", slick.detected_at.isoformat())
        model_predictions = [
            f"Lagrangian drift hindcasting estimated spill release occurred at approximately {origin_time_str}.",
            f"Inferred origin centroid located at {origin_coords[1]:.5f}° N, {origin_coords[0]:.5f}° E.",
            f"Hindcast trajectory indicates net drift of {drift_data.get('uncertainty', {}).get('total_drift_distance_km', 0.0)} km under combined wind/current forcing.",
        ]

        if candidates:
            top_candidate = candidates[0]
            model_predictions.append(
                f"Candidate vessel #{top_candidate.rank} ({top_candidate.vessel.vessel_name}, MMSI {top_candidate.vessel.mmsi}) "
                f"exhibits highest multi-factor evidence score ({top_candidate.overall_score:.1f}/100)."
            )

        # 3. Assumptions and Methodological Limitations
        assumptions_and_limitations = [
            "Surface drift model assumes standard 3.2% leeway wind drift factor without real-time wave Stokes drift corrections.",
            "Atmospheric and current fields derived from reanalysis snapshots; local sub-mesoscale eddies may alter local trajectory.",
            "AIS reports rely on broadcast compliance; vessels with deactivated transponders (dark vessels) are uncatalogued.",
            "Detection confidence reflects radar backscatter suppression; natural surfactants (algal blooms) require optical cross-verification.",
            "Candidate scores represent relative investigation priority for port state inspection; they DO NOT constitute definitive legal liability.",
        ]

        # 4. Executive Summary
        top_name = candidates[0].vessel.vessel_name if candidates else "None identified"
        top_score = candidates[0].overall_score if candidates else 0.0
        exec_summary = (
            f"On {slick.detected_at.strftime('%d %B %Y')}, a substantial marine oil slick ({slick.area_km2:.2f} km²) "
            f"was detected in the offshore shipping corridor. Backward Lagrangian trajectory simulation indicates the slick "
            f"originated approximately {origin_time_str}. AIS trajectory correlation across {len(candidates)} vessels identified "
            f"'{top_name}' as the primary candidate of interest (Evidence Score: {top_score:.1f}/100) based on spatial proximity, "
            f"temporal alignment, and cargo profile. Immediate port state verification is recommended."
        )

        # 5. Recommended Next Steps
        recommended_actions = [
            "Issue Port State Control (PSC) inspection notice for primary candidate at next port of call.",
            "Request official Oil Record Book (Part I / Part II) and bilge separator alarm logs.",
            "Secure vessel voyage data recorder (VDR) and navigational ECDIS logs for the incident window.",
            "Task high-resolution optical satellite (Sentinel-2 / PlanetScope) for follow-up verification of weathering.",
        ]

        return InvestigationReportResponse(
            report_id=report_id,
            incident_id=slick.id,
            generated_at=datetime.now(timezone.utc),
            analyst=analyst_name,
            priority_level=priority_level,
            executive_summary=exec_summary,
            observed_facts=observed_facts,
            model_predictions=model_predictions,
            assumptions_and_limitations=assumptions_and_limitations,
            slick_details=slick,
            environmental_conditions=environmental,
            drift_analysis=drift_data,
            candidate_vessels=candidates,
            recommended_actions=recommended_actions,
            legal_disclaimer=(
                "CONFIDENTIAL MARITIME INTELLIGENCE ASSESSMENT: This report contains automated forensic analysis "
                "generated by the MARINeX SIH26143 system. Attribution rankings reflect mathematical and physical "
                "consistency with available satellite and AIS data. Formal legal determination of culpability requires "
                "physical chemical fingerprinting and on-board port state investigation."
            ),
        )

    @staticmethod
    def to_markdown(report: InvestigationReportResponse) -> str:
        """Render report as formatted Markdown."""
        lines = [
            f"# MARINeX Forensic Investigation Report: {report.report_id}",
            f"**Incident ID:** `{report.incident_id}`  ",
            f"**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
            f"**Investigating Analyst:** {report.analyst}  ",
            f"**Priority Level:** **{report.priority_level}**  \n",
            "---",
            "## Executive Summary",
            report.executive_summary,
            "",
            "## 1. Observed Empirical Facts",
        ]
        for fact in report.observed_facts:
            lines.append(f"- {fact}")

        lines.extend(["", "## 2. Model Predictions & Hindcast Analysis"])
        for pred in report.model_predictions:
            lines.append(f"- {pred}")

        lines.extend(["", "## 3. Candidate Vessels Matrix", "| Rank | Vessel Name | MMSI | Vessel Type | Flag | Evidence Score | Priority |", "|---|---|---|---|---|---|---|"])
        for c in report.candidate_vessels:
            lines.append(
                f"| {c.rank} | **{c.vessel.vessel_name}** | `{c.vessel.mmsi}` | {c.vessel.vessel_type} | {c.vessel.flag} | **{c.overall_score:.1f}** | `{c.confidence}` |"
            )

        lines.extend(["", "## 4. Methodological Assumptions & Limitations"])
        for limit in report.assumptions_and_limitations:
            lines.append(f"- {limit}")

        lines.extend(["", "## 5. Recommended Actions"])
        for act in report.recommended_actions:
            lines.append(f"1. {act}")

        lines.extend(["", "---", f"> **Legal Disclaimer:** {report.legal_disclaimer}"])
        return "\n".join(lines)
