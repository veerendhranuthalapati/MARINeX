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

    CONCLUSION_CANDIDATE = "CANDIDATE_IDENTIFIED"
    CONCLUSION_INSUFFICIENT = "INSUFFICIENT_EVIDENCE"
    CONCLUSION_NO_CANDIDATE = "NO_RELIABLE_CANDIDATE"

    @staticmethod
    def derive_conclusion(candidates: List[VesselCandidateResponse]) -> tuple[str, str]:
        """Derive a single honest conclusion tier from the candidate list (Phase 28)."""
        if not candidates:
            return (
                ReportGeneratorService.CONCLUSION_NO_CANDIDATE,
                "No AIS vessel trajectories were found in the spatial and temporal search window, so no "
                "candidate correlation could be performed. No reliable candidate identified.",
            )
        top = candidates[0]
        if top.confidence == "EXCLUDED":
            return (
                ReportGeneratorService.CONCLUSION_NO_CANDIDATE,
                f"All {len(candidates)} scanned vessel(s) were spatially/temporally inconsistent "
                "with the inferred spill origin. No reliable candidate identified.",
            )
        if top.confidence in ("LOW", "MEDIUM"):
            return (
                ReportGeneratorService.CONCLUSION_INSUFFICIENT,
                f"Top candidate ('{top.vessel.vessel_name}', score {top.overall_score:.1f}/100) reaches only "
                "LOW/MEDIUM evidence consistency; insufficient for reliable attribution.",
            )
        return (
            ReportGeneratorService.CONCLUSION_CANDIDATE,
            f"Top candidate ('{top.vessel.vessel_name}', score {top.overall_score:.1f}/100) is consistent with "
            "the drift-hindcast origin region at HIGH evidence strength.",
        )

    @staticmethod
    def generate_report(
        slick: SlickResponse,
        environmental: Optional[EnvironmentalSnapshotResponse],
        drift_data: Dict[str, Any],
        candidates: List[VesselCandidateResponse],
        analyst_name: str = "Lead Maritime Intelligence Analyst",
        analyst_notes: Optional[str] = None,
        priority_level: str = "HIGH",
        data_quality: Optional[Dict[str, Any]] = None,
        conclusion: Optional[str] = None,
        conclusion_detail: Optional[str] = None,
    ) -> InvestigationReportResponse:
        report_id = f"REP-{slick.id[:8].upper()}-{datetime.now(timezone.utc).strftime('%Y%m%d')}"

        if conclusion is None or conclusion_detail is None:
            conclusion, conclusion_detail = ReportGeneratorService.derive_conclusion(candidates)

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
        top_name = candidates[0].vessel.vessel_name if candidates and candidates[0].confidence != "EXCLUDED" else "None identified"
        top_score = candidates[0].overall_score if candidates and candidates[0].confidence != "EXCLUDED" else 0.0
        if conclusion == ReportGeneratorService.CONCLUSION_NO_CANDIDATE:
            exec_summary = (
                f"On {slick.detected_at.strftime('%d %B %Y')}, a marine oil slick ({slick.area_km2:.2f} km²) "
                f"was detected in the offshore corridor. Backward Lagrangian trajectory simulation indicates the slick "
                f"originated approximately {origin_time_str}. AIS trajectory correlation identified NO reliable candidate "
                f"vessel consistent with the origin region within the search window. Without a corroborating vessel track, "
                f"origin attribution is NOT ARRIVED AT and escalation to vessel inspection is not currently justified."
            )
        elif conclusion == ReportGeneratorService.CONCLUSION_INSUFFICIENT:
            exec_summary = (
                f"On {slick.detected_at.strftime('%d %B %Y')}, a marine oil slick ({slick.area_km2:.2f} km²) "
                f"was detected in the offshore corridor. Backward Lagrangian trajectory simulation indicates the slick "
                f"originated approximately {origin_time_str}. AIS correlation produced '{top_name}' "
                f"(Evidence Score: {top_score:.1f}/100) as the leading candidate, but the evidence strength is "
                f"LOW/MEDIUM - INSUFFICIENT for reliable attribution. Additional optical/tracking verification is "
                f"recommended before any port-state action."
            )
        else:
            exec_summary = (
                f"On {slick.detected_at.strftime('%d %B %Y')}, a substantial marine oil slick ({slick.area_km2:.2f} km²) "
                f"was detected in the offshore shipping corridor. Backward Lagrangian trajectory simulation indicates the slick "
                f"originated approximately {origin_time_str}. AIS trajectory correlation across {len(candidates)} vessels identified "
                f"'{top_name}' as the primary candidate of interest (Evidence Score: {top_score:.1f}/100) based on spatial proximity, "
                f"temporal alignment, and cargo profile. Immediate port state verification is recommended."
            )

        # 5. Recommended Next Steps (honest for the evidence state)
        if conclusion == ReportGeneratorService.CONCLUSION_NO_CANDIDATE:
            recommended_actions = [
                "No vessel meets the spatial/temporal consistency threshold; do NOT escalate to port-state boarding on this basis.",
                "Task high-resolution optical satellite (Sentinel-2 / PlanetScope) for follow-up verification of weathering.",
                "Request AIS archives from adjacent coastal stations to detect possible dark-vessel (transponder-off) presence.",
                "Re-run the drift origin uncertainty analysis with a wider temporal window and additional met-ocean ensembles.",
            ]
        elif conclusion == ReportGeneratorService.CONCLUSION_INSUFFICIENT:
            recommended_actions = [
                "Do NOT issue a formal PSC boarding notice yet - evidence consistency is LOW/MEDIUM.",
                "Task high-resolution optical or airborne surveillance to independently confirm slick weathering and source proximity.",
                "Correlate leading candidate with port-of-departure inspection and Oil Record Book documentation as a DESK QUERY ONLY.",
                "Expand the AIS search window (time and radius) and re-evaluate with updated met-ocean fields.",
            ]
        else:
            recommended_actions = [
                "Issue Port State Control (PSC) inspection notice for primary candidate at next port of call.",
                "Request official Oil Record Book (Part I / Part II) and bilge separator alarm logs.",
                "Secure vessel voyage data recorder (VDR) and navigational ECDIS logs for the incident window.",
                "Task high-resolution optical satellite (Sentinel-2 / PlanetScope) for follow-up verification of weathering.",
            ]

        # Add attribution conclusion + data quality into predictions for transparency
        model_predictions.append(f"Attribution conclusion: {conclusion}.")
        if data_quality:
            dq = data_quality
            model_predictions.append(
                f"Overall input data quality grade: {dq.get('overall', 'UNKNOWN')} "
                f"(strict worst-case across {', '.join(s['source'] for s in dq.get('sources', []))})."
            )

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
            conclusion=conclusion,
            conclusion_detail=conclusion_detail,
            data_quality=data_quality or {},
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
            f"**Priority Level:** **{report.priority_level}**  ",
            f"**Attribution Conclusion:** `{report.conclusion}`  ",
            f"**Data Quality Grade:** `{report.data_quality.get('overall', 'UNKNOWN')}`  \n",
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

        lines.extend(["", "## 4. Attribution Conclusion"])
        lines.append(f"**{report.conclusion}** — {report.conclusion_detail}")

        lines.extend(["", "## 5. Input Data Quality"])
        if report.data_quality:
            lines.append(
                f"Overall grade: **{report.data_quality.get('overall', 'UNKNOWN')}** "
                f"({report.data_quality.get('note', '')})"
            )
            lines.append("")
            lines.append("| Source | Grade | Detail |")
            lines.append("|---|---|---|")
            for s in report.data_quality.get("sources", []):
                lines.append(f"| {s['source']} | `{s['grade']}` | {s['detail']} |")
        else:
            lines.append("No per-source data quality assessment was attached to this report.")

        lines.extend(["", "## 6. Methodological Assumptions & Limitations"])
        for limit in report.assumptions_and_limitations:
            lines.append(f"- {limit}")

        lines.extend(["", "## 7. Recommended Actions"])
        for act in report.recommended_actions:
            lines.append(f"1. {act}")

        lines.extend(["", "---", f"> **Legal Disclaimer:** {report.legal_disclaimer}"])
        return "\n".join(lines)
