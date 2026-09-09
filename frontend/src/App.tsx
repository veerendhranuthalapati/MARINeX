import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from './layouts/AppLayout';
import { DashboardPage } from './pages/DashboardPage';
import { ScenesPage } from './pages/ScenesPage';
import { DetectionPage } from './pages/DetectionPage';
import { InvestigationPage } from './pages/InvestigationPage';
import { DriftPage } from './pages/DriftPage';
import { AISAnalysisPage } from './pages/AISAnalysisPage';
import { CandidatesPage } from './pages/CandidatesPage';
import { ReportsPage } from './pages/ReportsPage';
import { SettingsPage } from './pages/SettingsPage';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="scenes" element={<ScenesPage />} />
          <Route path="detection" element={<DetectionPage />} />
          <Route path="investigation" element={<InvestigationPage />} />
          <Route path="drift" element={<DriftPage />} />
          <Route path="ais" element={<AISAnalysisPage />} />
          <Route path="candidates" element={<CandidatesPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
