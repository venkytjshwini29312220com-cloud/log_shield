import React, { useState } from 'react';
import { Header } from './components/Header';
import { NavTab, Sidebar } from './components/Sidebar';
import { useSOCData } from './hooks/useSOCData';
import { useWebSocket } from './hooks/useWebSocket';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { IncidentsPage } from './pages/IncidentsPage';
import { InvestigationPage } from './pages/InvestigationPage';
import { LiveEventsPage } from './pages/LiveEventsPage';
import { LogExplorerPage } from './pages/LogExplorerPage';
import { OverviewPage } from './pages/OverviewPage';
import { SystemStatusPage } from './pages/SystemStatusPage';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<NavTab>('overview');
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);

  const { status: wsStatus } = useWebSocket();
  const { statistics, incidents, liveEvents, systemStatus, loading, refresh } = useSOCData();

  const handleSelectIncident = (incidentId: string) => {
    setSelectedIncidentId(incidentId);
    setCurrentTab('investigation');
  };

  const activeIncidentsCount = incidents.filter(
    (i) => i.status === 'NEW' || i.status === 'INVESTIGATING' || i.status === 'CONTAINED'
  ).length;

  const getPageTitle = (tab: NavTab) => {
    switch (tab) {
      case 'overview':
        return { title: 'Security Operations Center', subtitle: 'Autonomous Intrusion Detection & Kill-Chain Correlation' };
      case 'events':
        return { title: 'Live Telemetry Stream', subtitle: 'Real-time WebSocket event ingestion pipeline from Laptop 1' };
      case 'incidents':
        return { title: 'Incident Portfolio', subtitle: 'Multi-stage intrusion incidents correlated by temporal and entity join keys' };
      case 'investigation':
        return { title: 'Deep Incident Investigation', subtitle: 'Unified timeline reconstruction, risk breakdown, and analyst response' };
      case 'analytics':
        return { title: 'Threat Analytics & Risk Model', subtitle: 'Severity distribution and explainable scoring weight calibration' };
      case 'explorer':
        return { title: 'Log Explorer & Parser Sandbox', subtitle: 'Historical SQLite query search and instant format normalization' };
      case 'status':
        return { title: 'System Architecture & Health', subtitle: 'Three-laptop physical LAN deployment and component states' };
    }
  };

  const { title, subtitle } = getPageTitle(currentTab);

  return (
    <div className="app-container">
      <Sidebar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        activeIncidentsCount={activeIncidentsCount}
        wsStatus={wsStatus}
        selectedIncidentId={selectedIncidentId}
      />

      <main className="main-content">
        <Header
          title={title}
          subtitle={subtitle}
          onRefresh={refresh}
          loading={loading}
        />

        {currentTab === 'overview' && (
          <OverviewPage
            statistics={statistics}
            incidents={incidents}
            liveEvents={liveEvents}
            systemStatus={systemStatus}
            onSelectIncident={handleSelectIncident}
            onNavigateTab={setCurrentTab}
          />
        )}

        {currentTab === 'events' && (
          <LiveEventsPage events={liveEvents} />
        )}

        {currentTab === 'incidents' && (
          <IncidentsPage
            incidents={incidents}
            onSelectIncident={handleSelectIncident}
            onRefresh={refresh}
          />
        )}

        {currentTab === 'investigation' && (
          <InvestigationPage
            incidentId={selectedIncidentId || (incidents[0]?.incident_id ?? null)}
            onBack={() => setCurrentTab('incidents')}
            onRefresh={refresh}
          />
        )}

        {currentTab === 'analytics' && (
          <AnalyticsPage incidents={incidents} />
        )}

        {currentTab === 'explorer' && (
          <LogExplorerPage />
        )}

        {currentTab === 'status' && (
          <SystemStatusPage
            systemStatus={systemStatus}
            wsStatus={wsStatus}
          />
        )}
      </main>
    </div>
  );
};
