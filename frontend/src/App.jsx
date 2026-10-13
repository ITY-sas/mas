import React from 'react';
import { useApp } from './context/AppContext';
import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { ToastContainer } from './components/layout/ToastContainer';
import { DashboardView } from './components/dashboard/DashboardView';
import { StudioView } from './components/studio/StudioView';
import { LibraryView } from './components/library/LibraryView';
import { PublicationsView } from './components/publications/PublicationsView';
import { TraceabilityView } from './components/traceability/TraceabilityView';
import { ResultsView } from './components/results/ResultsView';
import { HistoryView } from './components/history/HistoryView';
import { SystemView } from './components/system/SystemView';

export function App() {
  const { activeTab } = useApp();

  const renderActiveView = () => {
    switch (activeTab) {
      case 'dashboard':
        return <DashboardView />;
      case 'studio':
        return <StudioView />;
      case 'library':
        return <LibraryView />;
      case 'publications':
        return <PublicationsView />;
      case 'traceability':
        return <TraceabilityView />;
      case 'results':
        return <ResultsView />;
      case 'history':
        return <HistoryView />;
      case 'system':
        return <SystemView />;
      default:
        return <DashboardView />;
    }
  };

  return (
    <div className="flex min-h-screen bg-[#090d16] text-slate-100 font-sans selection:bg-indigo-500 selection:text-white">
      {/* Left Navigation Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header />

        <main className="flex-1 p-6 max-w-7xl w-full mx-auto">
          {renderActiveView()}
        </main>
      </div>

      {/* Floating Notifications */}
      <ToastContainer />
    </div>
  );
}
