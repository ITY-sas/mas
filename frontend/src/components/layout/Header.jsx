import React from 'react';
import { useApp } from '../../context/AppContext';
import {
  Play,
  RotateCw,
  Activity,
  Layers,
  ChevronRight,
  Radio,
  CheckCircle2,
} from 'lucide-react';

export function Header() {
  const {
    activeTab,
    selectedClient,
    isExecuting,
    liveStreamStatus,
    runDemo,
    checkSystemHealth,
    loadTasks,
    loadIdeas,
    loadPublications,
  } = useApp();

  const tabLabels = {
    dashboard: 'Dashboard General',
    studio: 'Generador de Lotes',
    library: 'Biblioteca de Ideas',
    publications: 'Publicaciones Postiz',
    traceability: 'Pipeline & Trazabilidad',
    results: 'Resultados & Dossiers',
    history: 'Historial de Tareas',
    system: 'Arquitectura & Servicios',
  };

  const handleRefreshAll = async () => {
    await Promise.all([
      checkSystemHealth(),
      loadTasks(),
      loadIdeas(),
      loadPublications(),
    ]);
  };

  return (
    <header className="sticky top-0 z-20 bg-[#090d16]/90 backdrop-blur-md border-b border-slate-800/80 px-6 py-3 flex items-center justify-between">
      {/* Breadcrumb Navigation */}
      <div className="flex items-center gap-2 text-xs">
        <span className="text-slate-400 font-medium">Studio</span>
        <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
        <span className="text-slate-200 font-semibold">{tabLabels[activeTab] || 'Backoffice'}</span>
        {selectedClient && (
          <>
            <span className="text-slate-700">•</span>
            <span className="text-indigo-400 bg-indigo-950/60 px-2 py-0.5 rounded text-[11px] font-medium border border-indigo-900/50">
              {selectedClient.nombre}
            </span>
          </>
        )}
      </div>

      {/* Right Actions & Live Status */}
      <div className="flex items-center gap-3">
        {/* Live SSE Status Pill */}
        {isExecuting && (
          <div className="flex items-center gap-2 bg-cyan-950/80 border border-cyan-800/80 text-cyan-300 text-xs px-3 py-1.5 rounded-full shadow-sm">
            <Radio className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
            <span className="font-mono font-medium text-[11px] truncate max-w-xs">
              {liveStreamStatus || 'Ejecutando agente...'}
            </span>
          </div>
        )}

        {/* Refresh button */}
        <button
          onClick={handleRefreshAll}
          title="Refrescar estado y datos"
          className="p-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-700/80 transition"
        >
          <RotateCw className="w-3.5 h-3.5" />
        </button>

        {/* Demo Rápida button */}
        <button
          onClick={runDemo}
          disabled={isExecuting}
          className="px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white font-semibold text-xs transition shadow-sm shadow-cyan-600/20 flex items-center gap-1.5 disabled:opacity-50"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          <span>Demo 1-Clic</span>
        </button>
      </div>
    </header>
  );
}
