import React, { useState } from 'react';
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
  SlidersHorizontal,
  Save,
  Trash2,
  X,
  Database,
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
    updateBrand,
    deleteBrand,
  } = useApp();

  const [isBrandModalOpen, setIsBrandModalOpen] = useState(false);
  const [isSavingBrand, setIsSavingBrand] = useState(false);
  const [brandForm, setBrandForm] = useState({
    name: '',
    profile_marca: '',
    restricciones_tono: '',
    producto_servicio: '',
    audiencia_objetivo: '',
    similarity_threshold: 0.7,
    top_k: 5,
    contrast_enabled: true,
  });

  const handleOpenBrandModal = () => {
    if (!selectedClient) return;
    const rc = selectedClient.rag_config || {};
    setBrandForm({
      name: selectedClient.nombre || '',
      profile_marca: selectedClient.perfil_marca || '',
      restricciones_tono: selectedClient.restricciones_tono || '',
      producto_servicio: selectedClient.producto_servicio || '',
      audiencia_objetivo: selectedClient.audiencia_objetivo || '',
      similarity_threshold: rc.similarity_threshold !== undefined ? rc.similarity_threshold : 0.7,
      top_k: rc.top_k !== undefined ? rc.top_k : 5,
      contrast_enabled: rc.contrast_enabled !== undefined ? rc.contrast_enabled : true,
    });
    setIsBrandModalOpen(true);
  };

  const handleSaveBrand = async () => {
    if (!selectedClient) return;
    const brandId = selectedClient.brand_id || selectedClient.id;
    setIsSavingBrand(true);
    try {
      await updateBrand(brandId, {
        name: brandForm.name,
        profile_marca: brandForm.profile_marca,
        restricciones_tono: brandForm.restricciones_tono,
        producto_servicio: brandForm.producto_servicio,
        audiencia_objetivo: brandForm.audiencia_objetivo,
        rag_config: {
          similarity_threshold: brandForm.similarity_threshold,
          top_k: brandForm.top_k,
          contrast_enabled: brandForm.contrast_enabled,
        },
      });
      setIsBrandModalOpen(false);
    } catch (err) {
      // toast shown in context
    } finally {
      setIsSavingBrand(false);
    }
  };

  const handleArchiveBrand = async () => {
    if (!selectedClient) return;
    const brandId = selectedClient.brand_id || selectedClient.id;
    if (!window.confirm(`¿Estás seguro de archivar la marca ${selectedClient.nombre}?`)) return;
    setIsSavingBrand(true);
    try {
      await deleteBrand(brandId);
      setIsBrandModalOpen(false);
    } catch (err) {
      // toast shown in context
    } finally {
      setIsSavingBrand(false);
    }
  };

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
        <div className="flex items-center justify-between mb-1.5 px-1">
          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
            <Building2 className="w-3 h-3 text-indigo-400" /> Marca Activa
          </label>
          <button
            onClick={handleOpenBrandModal}
            className="text-[10px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1 p-0.5 rounded transition"
            title="Configurar perfil de marca y parámetros de memoria RAG"
          >
            <SlidersHorizontal className="w-3 h-3" />
            <span>Config RAG</span>
          </button>
        </div>
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

      {/* Modal de Configuración de Marca y Parámetros RAG */}
      {isBrandModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm select-text">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-2xl p-6 space-y-4 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Database className="w-5 h-5 text-indigo-400" />
                <h3 className="text-sm font-bold text-white">
                  Configuración de Marca #{selectedClient?.brand_id || selectedClient?.id} & Memoria RAG
                </h3>
              </div>
              <button
                onClick={() => setIsBrandModalOpen(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-indigo-300 uppercase tracking-wider">Perfil & Tono</h4>
                <div>
                  <label className="text-[11px] font-semibold text-slate-300 block mb-1">Nombre Comercial:</label>
                  <input
                    type="text"
                    value={brandForm.name}
                    onChange={(e) => setBrandForm({ ...brandForm, name: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500 font-medium"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-300 block mb-1">Perfil de Marca:</label>
                  <textarea
                    rows={3}
                    value={brandForm.profile_marca}
                    onChange={(e) => setBrandForm({ ...brandForm, profile_marca: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500 font-sans leading-relaxed resize-y"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-300 block mb-1">Restricciones de Tono:</label>
                  <textarea
                    rows={2}
                    value={brandForm.restricciones_tono}
                    onChange={(e) => setBrandForm({ ...brandForm, restricciones_tono: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500 font-sans leading-relaxed resize-y"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-300 block mb-1">Producto o Servicio:</label>
                  <input
                    type="text"
                    value={brandForm.producto_servicio}
                    onChange={(e) => setBrandForm({ ...brandForm, producto_servicio: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500 font-medium"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-300 block mb-1">Audiencia Objetivo:</label>
                  <input
                    type="text"
                    value={brandForm.audiencia_objetivo}
                    onChange={(e) => setBrandForm({ ...brandForm, audiencia_objetivo: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500 font-medium"
                  />
                </div>
              </div>

              <div className="space-y-3">
                <h4 className="text-xs font-bold text-cyan-300 uppercase tracking-wider">Parámetros RAG & pgvector</h4>
                <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
                  <div>
                    <label className="text-[11px] font-semibold text-slate-300 block mb-1">
                      Umbral de Similitud Coseno ({brandForm.similarity_threshold}):
                    </label>
                    <input
                      type="range"
                      min="0.30"
                      max="0.95"
                      step="0.05"
                      value={brandForm.similarity_threshold}
                      onChange={(e) => setBrandForm({ ...brandForm, similarity_threshold: parseFloat(e.target.value) })}
                      className="w-full accent-cyan-500"
                    />
                    <span className="text-[10px] text-slate-400 block mt-0.5">
                      Filtra documentos con similitud mínima mayor a {brandForm.similarity_threshold}.
                    </span>
                  </div>

                  <div>
                    <label className="text-[11px] font-semibold text-slate-300 block mb-1">Top K Recuerdos RAG:</label>
                    <input
                      type="number"
                      min="1"
                      max="20"
                      value={brandForm.top_k}
                      onChange={(e) => setBrandForm({ ...brandForm, top_k: parseInt(e.target.value) || 5 })}
                      className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500 font-mono"
                    />
                    <span className="text-[10px] text-slate-400 block mt-0.5">
                      Número máximo de ideas y publicaciones recuperadas para inyectar en el contexto.
                    </span>
                  </div>

                  <label className="flex items-center gap-2 cursor-pointer pt-1">
                    <input
                      type="checkbox"
                      checked={brandForm.contrast_enabled}
                      onChange={(e) => setBrandForm({ ...brandForm, contrast_enabled: e.target.checked })}
                      className="rounded bg-slate-900 border-slate-700 text-cyan-500 focus:ring-0"
                    />
                    <span className="text-xs text-slate-200">Activar contraste semántico con historial</span>
                  </label>
                </div>

                <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-[11px] text-slate-400 space-y-1">
                  <p className="font-semibold text-slate-300">Aislamiento por Marca (Tenant)</p>
                  <p>
                    Las búsquedas vectoriales excluyen automáticamente ideas y publicaciones con estado <code>archived</code>.
                  </p>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={handleArchiveBrand}
                disabled={isSavingBrand}
                className="px-3.5 py-2 rounded-xl bg-rose-950/40 hover:bg-rose-950 text-rose-300 border border-rose-800 text-xs font-semibold flex items-center gap-1.5"
              >
                <Trash2 className="w-3.5 h-3.5" /> Archivar Marca
              </button>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setIsBrandModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={handleSaveBrand}
                  disabled={isSavingBrand}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-sm disabled:opacity-50"
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>{isSavingBrand ? 'Guardando...' : 'Guardar Cambios'}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
