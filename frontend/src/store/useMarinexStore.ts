import { create } from 'zustand';
import { VesselCandidate, OilSlick, DriftSimulation, AISPoint } from '../types';

export interface MapLayersState {
  observedSlicks: boolean;
  driftHindcast: boolean;
  inferredOrigin: boolean;
  aisTracks: boolean;
  candidateVessels: boolean;
  sarFootprint: boolean;
  originHeatmap: boolean;
}

export interface MarinexState {
  // Navigation & Shell
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;

  // Active Incident
  activeIncidentId: string;
  incidentStatus: 'CRITICAL' | 'INVESTIGATING' | 'MONITORING' | 'RESOLVED';
  setIncidentStatus: (status: 'CRITICAL' | 'INVESTIGATING' | 'MONITORING' | 'RESOLVED') => void;

  // Candidate Selection & Evidence Drawer
  selectedCandidateMmsi: number | null;
  activeDrawerCandidate: VesselCandidate | null;
  isEvidenceDrawerOpen: boolean;
  openEvidenceDrawer: (candidate: VesselCandidate) => void;
  closeEvidenceDrawer: () => void;

  // Map Controls
  mapLayers: MapLayersState;
  toggleMapLayer: (layer: keyof MapLayersState) => void;
  setMapLayer: (layer: keyof MapLayersState, enabled: boolean) => void;

  // Timeline Scrubber
  timelineHours: number; // 0.0 (T_obs) to 6.0 (T_release)
  isTimelinePlaying: boolean;
  setTimelineHours: (hours: number) => void;
  toggleTimelinePlay: () => void;

  // Notification / Pipeline toast
  pipelineNotice: string | null;
  setPipelineNotice: (notice: string | null) => void;
}

export const useMarinexStore = create<MarinexState>((set) => ({
  sidebarCollapsed: false,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),

  activeIncidentId: 'INC-2026-ARABIAN-SEA-001',
  incidentStatus: 'CRITICAL',
  setIncidentStatus: (status) => set({ incidentStatus: status }),

  selectedCandidateMmsi: 538009876, // Default Pacific Crown
  activeDrawerCandidate: null,
  isEvidenceDrawerOpen: false,
  openEvidenceDrawer: (candidate) =>
    set({
      selectedCandidateMmsi: candidate.vessel?.mmsi,
      activeDrawerCandidate: candidate,
      isEvidenceDrawerOpen: true,
    }),
  closeEvidenceDrawer: () => set({ isEvidenceDrawerOpen: false }),

  mapLayers: {
    observedSlicks: true,
    driftHindcast: true,
    inferredOrigin: true,
    aisTracks: true,
    candidateVessels: true,
    sarFootprint: true,
    originHeatmap: true,
  },
  toggleMapLayer: (layer) =>
    set((s) => ({
      mapLayers: { ...s.mapLayers, [layer]: !s.mapLayers[layer] },
    })),
  setMapLayer: (layer, enabled) =>
    set((s) => ({
      mapLayers: { ...s.mapLayers, [layer]: enabled },
    })),

  timelineHours: 6.0,
  isTimelinePlaying: false,
  setTimelineHours: (hours) => set({ timelineHours: hours }),
  toggleTimelinePlay: () => set((s) => ({ isTimelinePlaying: !s.isTimelinePlaying })),

  pipelineNotice: null,
  setPipelineNotice: (notice) => set({ pipelineNotice: notice }),
}));
