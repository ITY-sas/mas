import React from 'react';
import { useApp } from '../../context/AppContext';
import {
  LayoutDashboard,
  Sparkles,
  BookOpen,
  Send,
  GitBranch,
  FileText,
  Clock,
  Server,
  Building2,
  ExternalLink,
  Activity,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';

export function Sidebar() {
  const {
    activeTab,
    setActiveTab,
    clients,
    selectedClient,
    handleSelectClient,
    health,
    ideas,
    publications,
    isExecuting,
  } = useApp();

  const services = health?.services || {};
  const isOrchOk = typeof services.orchestrator === 'object';
  const isRedisOk = services.redis === 'ok';
  const isPgOk = services.postgres === 'ok';
  const isLlmOk = typeof services.llm_gateway === 'object';

  const navItems = [
    {
      group: 'PANEL PRINCIPAL',
      items: [
        { id: 'dashboard', label: 'Dashboard General', icon: LayoutDashboard },
      ],
    },
    {
      group: 'GESTIÓN CREATIVA',
      items: [
        { id: 'studio', label: 'Generador de Lotes', icon: Sparkles, badge: 'Studio' },
        { id: 'library', label: 'Biblioteca de Ideas', icon: BookOpen, count: ideas.length },
        { id: 'publications', label: 'Publicaciones Postiz', icon: Send, count: publications.length },
      ],
    },
    {
      group: 'OBSERVABILIDAD & AUDITORÍA',
      items: [
        {
          id: 'traceability',
          label: 'Pipeline & Trazabilidad',
          icon: GitBranch,
          badge: isExecuting ? 'EN VIVO' : undefined,
          badgeColor: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 animate-pulse',
        },
        { id: 'results', label: 'Resultados & Dossiers', icon: FileText },
        { id: 'history', label: 'Historial de Tareas', icon: Clock },
      ],
    },
    {
      group: 'SISTEMA',
      items: [
        { id: 'system', label: 'Arquitectura & Servicios', icon: Server },
      ],
    },
  ];

  return (
    <aside className="w-64 bg-[#0a0f1d] border-r border-slate-800/80 flex flex-col h-screen select-none shrink-0 sticky top-0 z-30">
      {/* Brand Header */}
      <div className="p-4 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-cyan-500 flex items-center justify-center text-white shadow-md shadow-indigo-600/30">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-sm tracking-tight text-white">Multi-Agent Studio</span>
            </div>
            <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/80 px-1.5 py-0.5 rounded border border-cyan-900/60 inline-block">
              LangGraph v2.0
            </span>
          </div>
        </div>
      </div>

      {/* Brand / Client Switcher */}
      <div className="px-3 pt-3 pb-2 border-b border-slate-800/60 bg-slate-950/40">
        <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1 mb-1.5 px-1">
          <Building2 className="w-3 h-3 text-indigo-400" /> Marca Activa
        </label>
        <select
          value={selectedClient?.id || 1}
          onChange={(e) => {
            const client = clients.find((c) => c.id === Number(e.target.value));
            if (client) handleSelectClient(client);
          }}
          className="w-full bg-slate-900 border border-slate-700/80 text-xs text-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 font-medium"
        >
          {clients.map((c) => (
            <option key={c.id} value={c.id}>
              {c.nombre} ({c.pais || 'Colombia'})
            </option>
          ))}
        </select>
        {selectedClient && (
          <div className="mt-1.5 px-1 flex items-center justify-between text-[11px] text-slate-400">
            <span className="truncate">{selectedClient.producto_servicio?.slice(0, 24) || selectedClient.pais}</span>
            <span className="font-mono text-[10px] text-indigo-300 bg-indigo-950 px-1 rounded">ID #{selectedClient.id}</span>
          </div>
        )}
      </div>

      {/* Navigation Groups */}
      <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-4">
        {navItems.map((group) => (
          <div key={group.group} className="space-y-0.5">
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 px-2.5 py-1">
              {group.group}
            </div>
            {group.items.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center justify-between px-2.5 py-2 rounded-lg text-xs font-medium transition-colors ${
                    isActive
                      ? 'bg-indigo-600/15 text-indigo-300 font-semibold border border-indigo-500/30'
                      : 'text-slate-300 hover:text-white hover:bg-slate-800/50'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className={`w-4 h-4 ${isActive ? 'text-indigo-400' : 'text-slate-400'}`} />
                    <span>{item.label}</span>
                  </div>

                  {item.badge && (
                    <span
                      className={`text-[9px] font-mono px-1.5 py-0.5 rounded border ${
                        item.badgeColor || 'bg-slate-800 text-slate-400 border-slate-700'
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}

                  {typeof item.count === 'number' && (
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800/80 text-slate-400 border border-slate-700/60">
                      {item.count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Health Vitals & Footer */}
      <div className="p-3 border-t border-slate-800/80 bg-slate-950/60 space-y-2">
        <div className="flex items-center justify-between text-[11px] text-slate-400 px-1">
          <span className="flex items-center gap-1 font-semibold text-slate-300">
            <Activity className="w-3 h-3 text-emerald-400" /> Servicios Vitals
          </span>
          <span className="text-[10px] font-mono text-slate-400">Puerto :3000</span>
        </div>

        <div className="grid grid-cols-4 gap-1 text-[10px] font-mono bg-slate-900/90 p-1.5 rounded-lg border border-slate-800">
          <div className="flex flex-col items-center gap-1" title="Orquestador Supervisor :8002">
            <span className={`w-2 h-2 rounded-full ${isOrchOk ? 'bg-emerald-400' : 'bg-rose-500'}`} />
            <span className="text-slate-400">Orq</span>
          </div>
          <div className="flex flex-col items-center gap-1" title="Redis Checkpoints & TaskStore :6379">
            <span className={`w-2 h-2 rounded-full ${isRedisOk ? 'bg-emerald-400' : 'bg-rose-500'}`} />
            <span className="text-slate-400">Redis</span>
          </div>
          <div className="flex flex-col items-center gap-1" title="PostgreSQL Memoria RAG & Chat :5432">
            <span className={`w-2 h-2 rounded-full ${isPgOk ? 'bg-emerald-400' : 'bg-rose-500'}`} />
            <span className="text-slate-400">PG</span>
          </div>
          <div className="flex flex-col items-center gap-1" title="LLM Gateway :8003">
            <span className={`w-2 h-2 rounded-full ${isLlmOk ? 'bg-emerald-400' : 'bg-rose-500'}`} />
            <span className="text-slate-400">LLM</span>
          </div>
        </div>

        <a
          href="http://localhost:4007"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-between px-2 py-1 rounded text-[11px] text-slate-400 hover:text-slate-200 hover:bg-slate-800/40 transition"
        >
          <span>Abrir Postiz</span>
          <ExternalLink className="w-3 h-3 text-slate-400" />
        </a>
      </div>
    </aside>
  );
}
