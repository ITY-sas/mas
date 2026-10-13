import React from 'react';
import { useApp } from '../../context/AppContext';
import {
  Server,
  Activity,
  Boxes,
  Database,
  Cpu,
  RotateCw,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  ShieldCheck,
  Radio,
  FileCode,
  Wrench,
} from 'lucide-react';

export function SystemView() {
  const {
    health,
    overview,
    ragStats,
    toolsCatalog,
    checkSystemHealth,
  } = useApp();

  const services = health?.services || {};

  const serviceList = [
    {
      name: 'Orquestador LangGraph',
      port: ':8002',
      status: typeof services.orchestrator === 'object' ? 'healthy' : 'down',
      details: services.orchestrator,
      role: 'Supervisor stateless, checkpointer RedisSaver y enrutador de tareas',
    },
    {
      name: 'Agente de Ideación',
      port: ':8000',
      status: typeof services.agente_ideacion === 'object' ? 'healthy' : 'down',
      details: services.agente_ideacion,
      role: 'Descubrimiento de herramientas, recuperación contextual y síntesis LLM',
    },
    {
      name: 'Agente de Publicación',
      port: ':8001',
      status: typeof services.agente_publicacion === 'object' ? 'healthy' : 'down',
      details: services.agente_publicacion,
      role: 'Generación de variantes por canal, validación y entrega a Postiz',
    },
    {
      name: 'LLM Gateway',
      port: ':8003',
      status: typeof services.llm_gateway === 'object' ? 'healthy' : 'down',
      details: services.llm_gateway,
      role: 'Puerta de enlace balanceada a Ollama con fallback semántico',
    },
    {
      name: 'Redis Stack',
      port: ':6379',
      status: services.redis === 'ok' ? 'healthy' : 'down',
      details: services.redis,
      role: 'Almacén de checkpoints (RedisSaver), SSE streaming y TaskStore',
    },
    {
      name: 'PostgreSQL + pgvector',
      port: ':5432',
      status: services.postgres === 'ok' ? 'healthy' : 'down',
      details: services.postgres,
      role: 'Memoria vectorial RAG semántica e historial durable chat_history',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Server className="w-5 h-5 text-indigo-400" /> Arquitectura del Sistema & Catálogo de Microservicios
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Monitoreo en tiempo real de los 6 servicios principales y herramientas descubiertas en runtime (Tool Discovery).
          </p>
        </div>

        <button
          onClick={checkSystemHealth}
          className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 flex items-center gap-1.5 transition self-start md:self-auto"
        >
          <RotateCw className="w-3.5 h-3.5" />
          <span>Verificar Conectividad</span>
        </button>
      </div>

      {/* Top 4 KPI Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bo-surface border border-slate-800">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Tareas en Sistema</span>
          <div className="text-xl font-bold text-white mt-1 font-mono">
            {overview.tasks.total}
          </div>
          <span className="text-[11px] text-emerald-400 mt-1 block">
            {overview.tasks.completed} completadas en Redis
          </span>
        </div>

        <div className="p-4 rounded-xl bo-surface border border-slate-800">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Memoria RAG (pgvector)</span>
          <div className="text-xl font-bold text-indigo-400 mt-1 font-mono">
            {ragStats.ideas || overview.rag.ideas || 0} ideas / {ragStats.publicaciones || overview.rag.publicaciones || 0} posts
          </div>
          <span className="text-[11px] text-slate-400 mt-1 block font-mono">
            nomic-embed-text (768d)
          </span>
        </div>

        <div className="p-4 rounded-xl bo-surface border border-slate-800">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Patrón de Orquestación</span>
          <div className="text-xl font-bold text-cyan-400 mt-1">
            Supervisor Stateless
          </div>
          <span className="text-[11px] text-slate-400 mt-1 block">
            Checkpointer RedisSaver
          </span>
        </div>

        <div className="p-4 rounded-xl bo-surface border border-slate-800">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Bus de Eventos</span>
          <div className="text-xl font-bold text-amber-400 mt-1">
            RabbitMQ Duradero
          </div>
          <span className="text-[11px] text-slate-400 mt-1 block">
            Colas idempotentes
          </span>
        </div>
      </div>

      {/* Grid de Estado de Microservicios */}
      <div className="p-6 rounded-2xl bo-surface border border-slate-800 space-y-4">
        <h3 className="text-sm font-bold text-white flex items-center gap-2 pb-2 border-b border-slate-800">
          <Activity className="w-4 h-4 text-emerald-400" /> Estado de Microservicios en Vivo
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {serviceList.map((svc) => {
            const isOk = svc.status === 'healthy';
            return (
              <div
                key={svc.name}
                className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-2 bo-card-interactive"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className={`w-2.5 h-2.5 rounded-full ${isOk ? 'bg-emerald-400 shadow-sm shadow-emerald-400' : 'bg-rose-500'}`} />
                    <span className="font-bold text-slate-200 text-xs">{svc.name}</span>
                  </div>
                  <span className="font-mono text-[10px] text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded border border-slate-700">
                    {svc.port}
                  </span>
                </div>

                <p className="text-[11px] text-slate-400 leading-relaxed">{svc.role}</p>

                <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-[10px] font-mono">
                  <span className={isOk ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}>
                    {isOk ? 'CONECTADO (200 OK)' : 'NO RESPONDE'}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Catálogo de Tools Descubiertas (Tool Discovery) */}
      <div className="p-6 rounded-2xl bo-surface border border-slate-800 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-800">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Boxes className="w-4 h-4 text-indigo-400" /> Catálogo de Tools-as-a-Service (Tool Discovery)
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Descubrimiento automático en runtime mediante contratos OpenAPI y manifiestos `/.well-known/tool-manifest`.
            </p>
          </div>
          <span className="text-xs font-mono px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-indigo-300">
            {toolsCatalog.length} servicios de herramientas
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {toolsCatalog.map((tool, idx) => (
            <div
              key={idx}
              className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-2 bo-card-interactive"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-200 text-xs flex items-center gap-1.5">
                  <Wrench className="w-3.5 h-3.5 text-indigo-400" /> {tool.tool}
                </span>
                <span className="font-mono text-[10px] text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded border border-slate-700">
                  {tool.service}
                </span>
              </div>

              <p className="text-[11px] text-slate-400 line-clamp-2">{tool.description || 'Herramienta de integración multi-agente.'}</p>

              {tool.operations && tool.operations.length > 0 && (
                <div className="pt-2 border-t border-slate-800 flex flex-wrap gap-1">
                  {tool.operations.map((op, opIdx) => (
                    <span
                      key={opIdx}
                      className="px-1.5 py-0.5 rounded bg-slate-950 text-cyan-300 font-mono text-[10px] border border-cyan-900/40"
                    >
                      {op.id}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
          {toolsCatalog.length === 0 && (
            <div className="col-span-full py-8 text-center text-slate-500 text-xs">
              El catálogo de herramientas se sincroniza automáticamente al conectar con el orquestador.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
