import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { PipelineVisualizer } from './PipelineVisualizer';
import {
  GitBranch,
  Clock,
  CheckCircle2,
  AlertCircle,
  Copy,
  Terminal,
  MessagesSquare,
  Wrench,
  Database,
  Layers,
  ArrowRight,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

export function TraceabilityView() {
  const {
    currentTaskId,
    currentTask,
    currentTrace,
    latestIdeaBatch,
    activeBatchTraceTaskId,
    setActiveBatchTraceTaskId,
    loadTaskDetails,
    copyText,
  } = useApp();

  const [selectedStageIndex, setSelectedStageIndex] = useState(0);
  const [showRawJson, setShowRawJson] = useState(false);

  const stages = currentTrace?.pipeline_stages || [];
  const selectedStage = stages[selectedStageIndex];
  const chatHistory = currentTrace?.chat_history || [];

  const handleSelectBatchIdea = (taskId) => {
    setActiveBatchTraceTaskId(taskId);
    loadTaskDetails(taskId);
  };

  return (
    <div className="space-y-6">
      {/* Panel de Progreso del Lote (si aplica) */}
      {latestIdeaBatch && (
        <div className="p-5 rounded-2xl bo-surface border border-slate-800 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3 pb-2 border-b border-slate-800">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Layers className="w-4 h-4 text-cyan-400" /> Progreso del Lote de Campaña
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Cada idea en el lote tiene un ciclo independiente con su propio hilo de ejecución en Redis y RabbitMQ.
              </p>
            </div>
            <span className="text-xs font-mono px-3 py-1 rounded-full bg-cyan-950/80 text-cyan-300 border border-cyan-800">
              {latestIdeaBatch.completed || 0}/{latestIdeaBatch.total || 0} completadas • {latestIdeaBatch.failed || 0} fallidas • {latestIdeaBatch.status}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 pt-1">
            {(latestIdeaBatch.ideas || []).map((idea, idx) => {
              const isActive = idea.task_id === currentTaskId;
              const statusClass =
                idea.status === 'completed'
                  ? 'text-emerald-400 border-emerald-900/60 bg-emerald-950/20'
                  : idea.status === 'failed'
                  ? 'text-rose-400 border-rose-900/60 bg-rose-950/20'
                  : idea.status === 'running'
                  ? 'text-cyan-400 border-cyan-800 bg-cyan-950/40 animate-pulse'
                  : 'text-slate-400 border-slate-800 bg-slate-900/40';

              return (
                <div
                  key={idx}
                  className={`p-3 rounded-xl border text-xs transition ${
                    isActive ? 'ring-2 ring-indigo-500 bg-indigo-950/20' : ''
                  } ${statusClass}`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-bold text-slate-200">Idea {idx + 1}</span>
                    <span className="font-mono text-[10px] uppercase font-semibold">{idea.status}</span>
                  </div>
                  <p className="text-slate-300 truncate text-[11px]">
                    {idea.title || (idea.status === 'running' ? 'Generando dossier...' : 'En cola...')}
                  </p>
                  {idea.error && (
                    <p className="text-rose-300 text-[10px] mt-1 line-clamp-1">{idea.error}</p>
                  )}
                  <div className="mt-2.5 flex items-center justify-between text-[10px] pt-1.5 border-t border-slate-800/80">
                    <span className="font-mono text-slate-400">
                      {idea.task_id ? idea.task_id.slice(0, 8) : 'sin tarea'}
                    </span>
                    {idea.task_id && (
                      <button
                        onClick={() => handleSelectBatchIdea(idea.task_id)}
                        className="text-cyan-400 hover:underline font-semibold flex items-center gap-1"
                      >
                        Ver traza &rarr;
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Encabezado de la Tarea Monitoreada */}
      <div className="p-4 rounded-xl bo-surface border border-slate-800 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-indigo-600/20 text-indigo-400 flex items-center justify-center">
            <GitBranch className="w-5 h-5" />
          </div>
          <div>
            <div className="text-[11px] text-slate-400 uppercase font-semibold">Tarea Monitoreada:</div>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="font-mono text-sm font-bold text-white">
                {currentTaskId || 'Ninguna seleccionada'}
              </span>
              {currentTaskId && (
                <button
                  onClick={() => copyText(currentTaskId)}
                  className="text-slate-400 hover:text-white p-1"
                  title="Copiar ID de tarea"
                >
                  <Copy className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs">
          <div>
            <span className="text-slate-400">Duración:</span>
            <span className="font-mono text-white font-semibold ml-1.5">
              {currentTrace?.total_duration_seconds ? `${currentTrace.total_duration_seconds}s` : '-'}
            </span>
          </div>

          <div>
            <span className="text-slate-400">Estado:</span>
            <span
              className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold ml-1.5 uppercase font-mono ${
                currentTrace?.status === 'completed'
                  ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                  : currentTrace?.status === 'running'
                  ? 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                  : currentTrace?.status === 'failed'
                  ? 'bg-rose-950 text-rose-300 border border-rose-800'
                  : 'bg-slate-800 text-slate-400'
              }`}
            >
              {currentTrace?.status || 'STANDBY'}
            </span>
          </div>
        </div>
      </div>

      {/* Pipeline Interactivo */}
      <div className="p-6 rounded-2xl bo-surface border border-slate-800 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <GitBranch className="w-4 h-4 text-cyan-400" /> Grafo de Ejecución del Pipeline (Nodos LangGraph)
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Haz clic en cualquier nodo para inspeccionar sus contratos de datos, estado y microservicios involucrados.
            </p>
          </div>
        </div>

        <PipelineVisualizer
          stages={stages}
          onSelectStage={setSelectedStageIndex}
          selectedStageIndex={selectedStageIndex}
        />

        {/* Detalle del Nodo Seleccionado */}
        {selectedStage && (
          <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 text-xs space-y-3 mt-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <span className="font-bold text-white text-sm">{selectedStage.name}</span>
                <span className="font-mono text-[11px] text-cyan-300 bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-900/60">
                  {selectedStage.component}
                </span>
              </div>
              <span className="font-mono text-[10px] text-slate-400 uppercase font-semibold">
                Estado: {selectedStage.status}
              </span>
            </div>

            <p className="text-slate-300">{selectedStage.framework}</p>

            {selectedStage.tools_used && selectedStage.tools_used.length > 0 && (
              <div>
                <span className="text-[10px] font-bold uppercase text-slate-400 block mb-1">
                  Herramientas Invocadas:
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {selectedStage.tools_used.map((tool, tIdx) => (
                    <span
                      key={tIdx}
                      className="px-2 py-0.5 rounded bg-slate-800 text-cyan-300 font-mono text-[11px] border border-cyan-900/50 flex items-center gap-1"
                    >
                      <Wrench className="w-2.5 h-2.5 text-cyan-400" /> {tool}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {selectedStage.details && (
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 font-mono text-[11px] text-slate-300 space-y-1">
                {Object.entries(selectedStage.details).map(([k, v]) => (
                  <div key={k} className="flex gap-2">
                    <span className="text-indigo-400 shrink-0">{k}:</span>
                    <span className="text-slate-300 break-all">
                      {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Grid: Timeline de Eventos & Chat History Durable */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (7 cols): Timeline de Herramientas y Etapas */}
        <div className="lg:col-span-7 space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Clock className="w-4 h-4 text-indigo-400" /> Eventos & Tools-as-a-Service Invocadas
          </h3>

          <div className="p-5 rounded-2xl bo-surface border border-slate-800 space-y-6">
            {stages.length === 0 ? (
              <p className="text-xs text-slate-500 text-center py-8">
                Ejecuta una tarea o selecciona una del historial para visualizar su cronología de herramientas.
              </p>
            ) : (
              stages.map((st, idx) => (
                <div key={idx} className="relative pl-6 space-y-2 border-l-2 border-slate-800 last:border-l-0">
                  <div className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-slate-900 border-2 border-indigo-500 flex items-center justify-center text-[9px] font-bold text-white">
                    {idx + 1}
                  </div>

                  <div className="flex items-center justify-between gap-2">
                    <span className="font-bold text-slate-200 text-xs">{st.name}</span>
                    <span className="font-mono text-[10px] text-slate-400">{st.component}</span>
                  </div>

                  <p className="text-[11px] text-slate-400">{st.framework}</p>

                  {/* Tools invocadas */}
                  {st.tools_used && st.tools_used.length > 0 && (
                    <div className="flex flex-wrap gap-1 pt-1">
                      {st.tools_used.map((t, tIdx) => (
                        <span
                          key={tIdx}
                          className="px-1.5 py-0.5 rounded bg-slate-900 text-cyan-300 font-mono text-[10px] border border-cyan-900/50"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Contexto recuperado */}
                  {st.context_retrieved && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 text-[11px]">
                      {st.context_retrieved.trends_context && (
                        <div className="p-2 rounded bg-slate-900/70 border border-slate-800">
                          <span className="text-indigo-400 font-semibold block text-[10px]">
                            Tendencias (pgvector):
                          </span>
                          <p className="text-slate-300 line-clamp-2 mt-0.5">
                            {st.context_retrieved.trends_context}
                          </p>
                        </div>
                      )}
                      {st.context_retrieved.competitors_context && (
                        <div className="p-2 rounded bg-slate-900/70 border border-slate-800">
                          <span className="text-amber-400 font-semibold block text-[10px]">
                            Competencia:
                          </span>
                          <p className="text-slate-300 line-clamp-2 mt-0.5">
                            {st.context_retrieved.competitors_context}
                          </p>
                        </div>
                      )}
                      {st.context_retrieved.news_rss && (
                        <div className="p-2 rounded bg-slate-900/70 border border-slate-800">
                          <span className="text-sky-400 font-semibold block text-[10px]">
                            Google News RSS:
                          </span>
                          <p className="text-slate-300 line-clamp-2 mt-0.5">
                            {st.context_retrieved.news_rss}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Column (5 cols): Historial Durable de Chat PostgreSQL + JSON */}
        <div className="lg:col-span-5 space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <MessagesSquare className="w-4 h-4 text-emerald-400" /> Historial Durable (`chat_history` en PostgreSQL)
          </h3>

          <div className="p-4 rounded-2xl bo-surface border border-slate-800 max-h-[460px] overflow-y-auto space-y-3">
            {chatHistory.length === 0 ? (
              <p className="text-xs text-slate-500 text-center py-8">
                Los turnos de interacción se sincronizan automáticamente en PostgreSQL al finalizar cada fase.
              </p>
            ) : (
              chatHistory.map((msg, mIdx) => (
                <div
                  key={msg.id || mIdx}
                  className={`p-3 rounded-xl border text-xs space-y-1 ${
                    msg.role === 'user'
                      ? 'bg-indigo-950/30 border-indigo-900/60'
                      : 'bg-slate-900/80 border-slate-800'
                  }`}
                >
                  <div className="flex items-center justify-between text-[10px]">
                    <span className="font-bold uppercase tracking-wider text-indigo-400 font-mono">
                      {msg.role}
                    </span>
                    <span className="text-slate-500 font-mono">
                      {msg.created_at ? new Date(msg.created_at).toLocaleTimeString() : ''}
                    </span>
                  </div>
                  <p className="text-slate-200 whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                </div>
              ))
            )}
          </div>

          {/* Raw JSON Inspector */}
          {currentTask && (
            <div className="p-4 rounded-xl bo-surface border border-slate-800">
              <button
                onClick={() => setShowRawJson(!showRawJson)}
                className="w-full flex items-center justify-between text-xs font-semibold text-slate-300 hover:text-white"
              >
                <span className="flex items-center gap-1.5">
                  <Terminal className="w-3.5 h-3.5 text-cyan-400" /> Inspector JSON Crudo de la Tarea
                </span>
                {showRawJson ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>

              {showRawJson && (
                <div className="mt-3 space-y-2">
                  <div className="flex justify-end">
                    <button
                      onClick={() => copyText(JSON.stringify(currentTask, null, 2))}
                      className="text-[11px] text-cyan-400 hover:underline flex items-center gap-1"
                    >
                      <Copy className="w-3 h-3" /> Copiar JSON
                    </button>
                  </div>
                  <pre className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-[10px] font-mono text-slate-300 max-h-60 overflow-auto whitespace-pre-wrap">
                    {JSON.stringify(currentTask, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
