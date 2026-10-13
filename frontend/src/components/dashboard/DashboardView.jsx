import React from 'react';
import { useApp } from '../../context/AppContext';
import {
  Sparkles,
  BookOpen,
  Send,
  GitBranch,
  Database,
  Activity,
  Layers,
  ArrowRight,
  Clock,
  CheckCircle2,
  AlertCircle,
  Play,
  Share2,
} from 'lucide-react';

export function DashboardView() {
  const {
    selectedClient,
    overview,
    ragStats,
    health,
    tasks,
    ideas,
    publications,
    brandChannels,
    setActiveTab,
    runDemo,
    loadTaskDetails,
    setCurrentTaskId,
    latestIdeaBatch,
    isExecuting,
  } = useApp();

  const services = health?.services || {};
  const isAllHealthy =
    typeof services.orchestrator === 'object' &&
    services.redis === 'ok' &&
    services.postgres === 'ok' &&
    typeof services.llm_gateway === 'object';

  const recentTasks = tasks.slice(0, 6);

  return (
    <div className="space-y-6">
      {/* Welcome & Brand Banner */}
      <div className="p-6 rounded-2xl bo-surface border border-slate-800 relative overflow-hidden bg-gradient-to-r from-slate-900 via-indigo-950/20 to-slate-900">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-bold uppercase tracking-wider text-indigo-400">Backoffice Ejecutivo</span>
              <span className="text-slate-600">•</span>
              <span className="text-xs text-slate-400">LangGraph Multi-Agent Architecture</span>
            </div>
            <h1 className="text-xl font-bold text-white tracking-tight">
              Centro de Mando: <span className="text-indigo-400">{selectedClient?.nombre || 'Marca'}</span>
            </h1>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
              {selectedClient?.perfil_marca ||
                'Sistema multi-agente para ideación masiva de campañas, persistencia semántica en pgvector y publicación manual con trazabilidad.'}
            </p>
          </div>

          <div className="flex items-center gap-2.5 shrink-0">
            <button
              onClick={() => setActiveTab('studio')}
              className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition shadow-md shadow-indigo-600/30 flex items-center gap-2"
            >
              <Sparkles className="w-4 h-4" />
              <span>Generar Lote</span>
            </button>
            <button
              onClick={runDemo}
              disabled={isExecuting}
              className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold text-xs transition flex items-center gap-2 disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5 text-cyan-400" />
              <span>Demo Rápida</span>
            </button>
          </div>
        </div>
      </div>

      {/* Top 4 KPI Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* KPI 1: Tareas */}
        <div className="p-4 rounded-xl bo-surface border border-slate-800 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span className="font-medium">Tareas en TaskStore</span>
            <Clock className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white font-mono">{overview.tasks.total}</span>
            <span className="text-[11px] text-emerald-400 font-mono">
              {overview.tasks.completed} completadas
            </span>
          </div>
          <div className="mt-2 text-[11px] text-slate-400 flex items-center justify-between border-t border-slate-800/80 pt-2">
            <span>En ejecución: {overview.tasks.running}</span>
            <span className="text-rose-400">Fallidas: {overview.tasks.failed}</span>
          </div>
        </div>

        {/* KPI 2: Memoria RAG */}
        <div className="p-4 rounded-xl bo-surface border border-slate-800 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span className="font-medium">Memoria Vectorial (pgvector)</span>
            <Database className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-cyan-400 font-mono">
              {(ragStats.ideas || overview.rag.ideas || 0) + (ragStats.publicaciones || overview.rag.publicaciones || 0)}
            </span>
            <span className="text-[11px] text-slate-400">vectores</span>
          </div>
          <div className="mt-2 text-[11px] text-slate-400 flex items-center justify-between border-t border-slate-800/80 pt-2">
            <span>{ragStats.ideas || overview.rag.ideas || 0} ideas</span>
            <span>{ragStats.publicaciones || overview.rag.publicaciones || 0} publicaciones</span>
          </div>
        </div>

        {/* KPI 3: Canales Postiz */}
        <div className="p-4 rounded-xl bo-surface border border-slate-800 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span className="font-medium">Canales Postiz</span>
            <Share2 className="w-4 h-4 text-amber-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-amber-400 font-mono">{brandChannels.length}</span>
            <span className="text-[11px] text-slate-400">activos en {selectedClient?.nombre}</span>
          </div>
          <div className="mt-2 text-[11px] text-slate-400 flex items-center justify-between border-t border-slate-800/80 pt-2">
            <span>{publications.length} entregas totales</span>
            <button
              onClick={() => setActiveTab('publications')}
              className="text-amber-400 hover:underline flex items-center gap-1"
            >
              Ver <ArrowRight className="w-2.5 h-2.5" />
            </button>
          </div>
        </div>

        {/* KPI 4: Infraestructura */}
        <div className="p-4 rounded-xl bo-surface border border-slate-800 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span className="font-medium">Estado de Servicios</span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-sm font-bold text-white flex items-center gap-1.5">
              <span className={`w-2.5 h-2.5 rounded-full ${isAllHealthy ? 'bg-emerald-400 shadow-sm shadow-emerald-400' : 'bg-amber-400'}`} />
              {isAllHealthy ? 'Operativo 100%' : 'Atención Requerida'}
            </span>
          </div>
          <div className="mt-2 text-[11px] text-slate-400 flex items-center justify-between border-t border-slate-800/80 pt-2">
            <span>Supervisor + RabbitMQ</span>
            <button
              onClick={() => setActiveTab('system')}
              className="text-indigo-400 hover:underline flex items-center gap-1"
            >
              Detalles <ArrowRight className="w-2.5 h-2.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Grid: Active Batch / Quick Shortcuts + Recent Tasks */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (8 cols): Lote Activo + Actividad Reciente */}
        <div className="lg:col-span-8 space-y-6">
          {/* Lote Activo Banner (si existe) */}
          {latestIdeaBatch && (
            <div className="p-5 rounded-xl border border-cyan-800/60 bg-cyan-950/20 bo-surface">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                  <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-300">
                    Último Lote Procesado ({latestIdeaBatch.status})
                  </h3>
                </div>
                <button
                  onClick={() => setActiveTab('traceability')}
                  className="text-xs text-cyan-400 hover:underline flex items-center gap-1 font-medium"
                >
                  Abrir Traza <ArrowRight className="w-3 h-3" />
                </button>
              </div>
              <p className="text-xs text-slate-300">
                Lote con {latestIdeaBatch.total || 0} idea(s): {latestIdeaBatch.completed || 0} completadas, {latestIdeaBatch.failed || 0} fallidas.
              </p>
              <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-2">
                {(latestIdeaBatch.ideas || []).slice(0, 3).map((idea, idx) => (
                  <div key={idx} className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 text-xs">
                    <span className="text-[10px] text-amber-400 font-semibold uppercase block">Idea {idx + 1}</span>
                    <p className="text-slate-200 truncate mt-0.5">{idea.title || 'Generando...'}</p>
                    <span className={`text-[10px] mt-1 inline-block ${idea.status === 'completed' ? 'text-emerald-400' : 'text-slate-400'}`}>
                      {idea.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tabla de Tareas Recientes */}
          <div className="p-5 rounded-xl bo-surface border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Clock className="w-4 h-4 text-indigo-400" /> Tareas Recientes en Redis
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">Historial de ejecuciones multi-agente con trazabilidad auditable.</p>
              </div>
              <button
                onClick={() => setActiveTab('history')}
                className="text-xs text-indigo-400 hover:underline font-semibold flex items-center gap-1"
              >
                Ver todas <ArrowRight className="w-3 h-3" />
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 uppercase text-[10px] font-semibold tracking-wider">
                    <th className="pb-2.5">ID Tarea</th>
                    <th className="pb-2.5">Brief / Propósito</th>
                    <th className="pb-2.5">Estado</th>
                    <th className="pb-2.5">Duración</th>
                    <th className="pb-2.5 text-right">Acción</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-sans">
                  {recentTasks.map((t) => (
                    <tr key={t.task_id} className="hover:bg-slate-900/50 transition">
                      <td className="py-2.5 font-mono text-[11px] text-indigo-400">
                        {t.task_id.slice(0, 8)}...
                      </td>
                      <td className="py-2.5 text-slate-300 max-w-xs truncate">
                        {t.brief_content || 'Brief estándar por perfil de marca'}
                      </td>
                      <td className="py-2.5">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                            t.status === 'completed'
                              ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                              : t.status === 'running'
                              ? 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                              : 'bg-rose-950 text-rose-300 border border-rose-800'
                          }`}
                        >
                          {t.status}
                        </span>
                      </td>
                      <td className="py-2.5 font-mono text-slate-400 text-[11px]">
                        {t.duration_seconds ? `${t.duration_seconds}s` : '-'}
                      </td>
                      <td className="py-2.5 text-right">
                        <button
                          onClick={() => {
                            setCurrentTaskId(t.task_id);
                            loadTaskDetails(t.task_id);
                            setActiveTab('traceability');
                          }}
                          className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] border border-slate-700 font-medium"
                        >
                          Auditar Traza
                        </button>
                      </td>
                    </tr>
                  ))}
                  {recentTasks.length === 0 && (
                    <tr>
                      <td colSpan={5} className="py-6 text-center text-slate-500 text-xs">
                        No hay tareas registradas en Redis aún.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right Column (4 cols): Ficha de Marca + Accesos Directos */}
        <div className="lg:col-span-4 space-y-6">
          {/* Ficha de Marca Activa */}
          <div className="p-5 rounded-xl bo-surface border border-slate-800 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <span className="text-xs font-bold text-white flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-amber-400" /> Perfil Corporativo
              </span>
              <span className="text-[10px] font-mono text-indigo-400 bg-indigo-950 px-1.5 py-0.5 rounded">
                {selectedClient?.pais || 'Colombia'}
              </span>
            </div>

            <div className="text-xs space-y-2.5 text-slate-300">
              <div>
                <span className="text-slate-400 text-[10px] uppercase font-semibold block">Producto / Servicio:</span>
                <p className="mt-0.5 text-slate-200 line-clamp-2">{selectedClient?.producto_servicio || 'N/A'}</p>
              </div>
              <div>
                <span className="text-slate-400 text-[10px] uppercase font-semibold block">Restricciones de Tono:</span>
                <p className="mt-0.5 text-slate-300 line-clamp-2">{selectedClient?.restricciones_tono || 'N/A'}</p>
              </div>
              <div>
                <span className="text-slate-400 text-[10px] uppercase font-semibold block">Audiencia Objetivo:</span>
                <p className="mt-0.5 text-slate-300 line-clamp-1">{selectedClient?.audiencia_objetivo || 'N/A'}</p>
              </div>
              <div>
                <span className="text-slate-400 text-[10px] uppercase font-semibold block">Zona Horaria:</span>
                <p className="mt-0.5 font-mono text-slate-400 text-[11px]">{selectedClient?.zona_horaria || 'America/Bogota'}</p>
              </div>
            </div>
          </div>

          {/* Accesos Rápidos */}
          <div className="p-5 rounded-xl bo-surface border border-slate-800 space-y-3">
            <span className="text-xs font-bold text-white block pb-2 border-b border-slate-800">
              Flujos Operativos
            </span>

            <div className="space-y-2">
              <button
                onClick={() => setActiveTab('studio')}
                className="w-full p-2.5 rounded-lg bg-slate-900 hover:bg-slate-800/80 border border-slate-800 text-left transition flex items-center justify-between group"
              >
                <div>
                  <span className="text-xs font-semibold text-slate-200 block group-hover:text-indigo-400">
                    Generar Nuevo Lote
                  </span>
                  <span className="text-[11px] text-slate-400">Briefs masivos y dossiers</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-indigo-400" />
              </button>

              <button
                onClick={() => setActiveTab('library')}
                className="w-full p-2.5 rounded-lg bg-slate-900 hover:bg-slate-800/80 border border-slate-800 text-left transition flex items-center justify-between group"
              >
                <div>
                  <span className="text-xs font-semibold text-slate-200 block group-hover:text-indigo-400">
                    Biblioteca de Ideas ({ideas.length})
                  </span>
                  <span className="text-[11px] text-slate-400">Revisión de dossiers y preproducción</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-indigo-400" />
              </button>

              <button
                onClick={() => setActiveTab('publications')}
                className="w-full p-2.5 rounded-lg bg-slate-900 hover:bg-slate-800/80 border border-slate-800 text-left transition flex items-center justify-between group"
              >
                <div>
                  <span className="text-xs font-semibold text-slate-200 block group-hover:text-indigo-400">
                    Aprobaciones de Publicación ({publications.length})
                  </span>
                  <span className="text-[11px] text-slate-400">Copys por canal y entregas a Postiz</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-indigo-400" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
