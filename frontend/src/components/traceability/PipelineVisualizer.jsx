import React, { useState } from 'react';
import {
  Workflow,
  Lightbulb,
  RotateCw,
  Share2,
  Database,
  CheckCircle2,
  CircleDot,
  XCircle,
  MinusCircle,
  Clock,
  ArrowRight,
  Info,
  ChevronDown,
  Layers,
} from 'lucide-react';

export function PipelineVisualizer({ stages = [], onSelectStage, selectedStageIndex }) {
  const defaultStages = [
    {
      id: 'stage-ingress',
      title: '1. Ingesta & Supervisor',
      service: 'orchestrator :8002',
      framework: 'LangGraph Supervisor',
      desc: 'LangGraph Supervisor, checkpointer en Redis (RedisSaver) y despacho de eventos a RabbitMQ.',
      icon: Workflow,
      tools: ['TaskStore.create', 'interrupt()', 'RedisSaver.put'],
    },
    {
      id: 'stage-ideacion',
      title: '2. Agente de Ideación',
      service: 'agente-ideacion :8000',
      framework: 'Microservicio LangGraph (4 nodos)',
      desc: 'Descubrimiento dinámico de tools, pgvector para tendencias y competencia, Google News RSS y LLM Gateway.',
      icon: Lightbulb,
      tools: ['client.profile', 'trends.search', 'competitors.search', 'rag.similar', 'news.news', 'llm-gateway'],
    },
    {
      id: 'stage-resume',
      title: '3. Reanudación Orquestador',
      service: 'orchestrator :8002',
      framework: 'Command(resume=...) desde Redis',
      desc: 'Reanudación tras finalizar la ideación; guarda el dossier y aguarda solicitud manual de publicación.',
      icon: RotateCw,
      tools: ['RedisSaver.resume', 'dispatch_publicacion'],
    },
    {
      id: 'stage-publicacion',
      title: '4. Agente de Publicación',
      service: 'agente-publicacion :8001',
      framework: 'Microservicio LangGraph (4 nodos)',
      desc: 'Genera copys personalizados por canal. En preparación no llama a Postiz; en entrega confirmada despacha variantes.',
      icon: Share2,
      tools: ['client.profile', 'trends.search', 'trending.trending', 'llm-gateway', 'postiz'],
    },
    {
      id: 'stage-persist',
      title: '5. Memoria & Persistencia',
      service: 'PostgreSQL + Redis',
      framework: 'pgvector + chat_history + RabbitMQ',
      desc: 'Guarda embeddings en pgvector, turnos en chat_history durable y publica task.completed en RabbitMQ.',
      icon: Database,
      tools: ['rag.save_idea', 'rag.save_publicacion', 'chat_history'],
    },
  ];

  return (
    <div className="space-y-4">
      {/* Visual Pipeline Nodes Flow */}
      <div className="w-full overflow-x-auto pb-2">
        <div className="flex items-center gap-3 min-w-[920px]">
          {defaultStages.map((stage, idx) => {
            const Icon = stage.icon;
            const liveStage = stages[idx];
            const status = liveStage?.status || 'pending';
            const isSelected = selectedStageIndex === idx;

            // Clases según estado
            let statusBadge = (
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-400 border border-slate-700">
                Pendiente
              </span>
            );
            let borderClass = 'border-slate-800 hover:border-slate-700 bg-slate-900/60';
            let iconColor = 'text-slate-400 bg-slate-800';

            if (status === 'completed') {
              statusBadge = (
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-950 text-emerald-300 border border-emerald-800 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3 text-emerald-400" /> Listo
                </span>
              );
              borderClass = 'border-emerald-800/80 bg-emerald-950/20';
              iconColor = 'text-emerald-400 bg-emerald-900/40';
            } else if (status === 'running') {
              statusBadge = (
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-950 text-cyan-300 border border-cyan-800 flex items-center gap-1 animate-pulse">
                  <CircleDot className="w-3 h-3 text-cyan-400" /> En curso
                </span>
              );
              borderClass = 'border-cyan-500 shadow-md shadow-cyan-500/20 bg-cyan-950/30';
              iconColor = 'text-cyan-300 bg-cyan-900/40';
            } else if (status === 'failed') {
              statusBadge = (
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-rose-950 text-rose-300 border border-rose-800 flex items-center gap-1">
                  <XCircle className="w-3 h-3 text-rose-400" /> Falló
                </span>
              );
              borderClass = 'border-rose-800 bg-rose-950/20';
              iconColor = 'text-rose-400 bg-rose-900/40';
            } else if (status === 'skipped') {
              statusBadge = (
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-900 text-slate-500 border border-slate-800">
                  Omitido
                </span>
              );
              borderClass = 'border-slate-800/60 opacity-50 border-dashed bg-slate-950/40';
            }

            return (
              <React.Fragment key={stage.id}>
                {/* Node Box */}
                <button
                  type="button"
                  onClick={() => onSelectStage(idx)}
                  className={`flex-1 p-3.5 rounded-xl border text-left transition relative select-none bo-card-interactive ${borderClass} ${
                    isSelected ? 'ring-2 ring-indigo-500 ring-offset-2 ring-offset-slate-950' : ''
                  }`}
                >
                  <div className="flex items-center justify-between gap-1 mb-2">
                    <div className="flex items-center gap-2">
                      <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${iconColor}`}>
                        <Icon className="w-4 h-4" />
                      </div>
                      <span className="text-xs font-bold text-white truncate">{stage.title}</span>
                    </div>
                  </div>

                  <div className="text-[10px] font-mono text-slate-400 mb-2 truncate">
                    {stage.service}
                  </div>

                  <div className="flex items-center justify-between text-[10px]">
                    {statusBadge}
                    <span className="text-slate-400 hover:text-slate-200">Inspeccionar &rarr;</span>
                  </div>
                </button>

                {/* Connector Arrow */}
                {idx < defaultStages.length - 1 && (
                  <div className="shrink-0 flex items-center justify-center text-slate-600">
                    <ArrowRight className="w-4 h-4" />
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
}
