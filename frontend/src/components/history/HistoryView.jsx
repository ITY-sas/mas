import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import {
  Clock,
  RotateCw,
  Search,
  CheckCircle2,
  AlertCircle,
  CircleDot,
  Copy,
  ArrowRight,
  Filter,
  Building2,
  Layers,
} from 'lucide-react';

export function HistoryView() {
  const {
    tasks,
    isLoadingTasks,
    loadTasks,
    clients,
    selectedClient,
    loadTaskDetails,
    setCurrentTaskId,
    setActiveTab,
    copyText,
  } = useApp();

  const [statusFilter, setStatusFilter] = useState('');
  const [brandFilter, setBrandFilter] = useState('active'); // 'active', 'all', or specific client id
  const [searchQuery, setSearchQuery] = useState('');

  const activeBrandId = selectedClient?.brand_id || selectedClient?.id;

  const handleSelectTask = (taskId) => {
    setCurrentTaskId(taskId);
    loadTaskDetails(taskId);
    setActiveTab('traceability');
  };

  const filteredTasks = tasks.filter((t) => {
    const taskBrand = t.brand_id || t.client_id;
    const matchesBrand =
      brandFilter === 'all'
        ? true
        : brandFilter === 'active'
        ? taskBrand === activeBrandId
        : String(taskBrand) === String(brandFilter);

    const matchesStatus = !statusFilter || t.status === statusFilter;
    const matchesSearch =
      !searchQuery ||
      t.task_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (t.brief_content && t.brief_content.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesBrand && matchesStatus && matchesSearch;
  });

  const getBrandBadgeStyle = (brandId) => {
    switch (Number(brandId)) {
      case 1:
        return 'bg-emerald-950/80 text-emerald-300 border-emerald-800/80';
      case 2:
        return 'bg-indigo-950/80 text-indigo-300 border-indigo-800/80';
      case 3:
        return 'bg-amber-950/80 text-amber-300 border-amber-800/80';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Clock className="w-5 h-5 text-indigo-400" /> Registro de Tareas Multi-Agente (Redis TaskStore)
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Auditoría histórica de ejecuciones de ideación, supervisión y entrega. Filtra por marca activa o consulta el histórico global.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs px-2.5 py-1 rounded-lg bg-indigo-950/80 text-indigo-300 border border-indigo-800 font-semibold flex items-center gap-1.5 shadow-sm">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span>
              {brandFilter === 'active'
                ? `Marca Activa: ${selectedClient?.nombre || 'Marca'} (ID: ${activeBrandId})`
                : brandFilter === 'all'
                ? 'Histórico Global (Todas)'
                : `Filtro Marca ID: ${brandFilter}`}
            </span>
          </span>
          <span className="text-xs font-mono px-3 py-1 rounded-lg bg-slate-900 border border-slate-800 text-slate-300">
            {filteredTasks.length} de {tasks.length} tareas
          </span>
          <button
            onClick={() => loadTasks(statusFilter || null)}
            disabled={isLoadingTasks}
            className="px-3.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 flex items-center gap-1.5 transition self-start md:self-auto"
          >
            <RotateCw className={`w-3.5 h-3.5 ${isLoadingTasks ? 'animate-spin' : ''}`} />
            <span>Refrescar</span>
          </button>
        </div>
      </div>

      {/* Filtros de Búsqueda, Marca y Estado */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
        {/* Buscador de texto */}
        <div className="relative md:col-span-5">
          <input
            type="search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Buscar por ID de tarea o brief..."
            className="w-full bg-slate-900 border border-slate-700/80 rounded-xl pl-8 pr-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-medium"
          />
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
        </div>

        {/* Filtro por Marca */}
        <div className="md:col-span-4">
          <select
            value={brandFilter}
            onChange={(e) => setBrandFilter(e.target.value)}
            className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-medium"
          >
            <option value="active">
              🎯 Solo Marca Activa ({selectedClient?.nombre} · ID {activeBrandId})
            </option>
            <option value="all">🌐 Todas las Marcas ({tasks.length} tareas)</option>
            {clients.map((c) => (
              <option key={c.id} value={c.id}>
                🏢 {c.nombre} (ID: {c.id})
              </option>
            ))}
          </select>
        </div>

        {/* Filtro por Estado */}
        <div className="md:col-span-3">
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              loadTasks(e.target.value || null);
            }}
            className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-medium"
          >
            <option value="">Todos los Estados</option>
            <option value="completed">Completadas</option>
            <option value="running">En Ejecución</option>
            <option value="failed">Fallidas</option>
          </select>
        </div>
      </div>

      {/* Tabla de Tareas */}
      <div className="p-6 rounded-2xl bo-surface border border-slate-800">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 uppercase text-[10px] font-semibold tracking-wider">
                <th className="p-3">ID Tarea</th>
                <th className="p-3">Cliente / Marca</th>
                <th className="p-3">Brief / Contenido</th>
                <th className="p-3">Estado</th>
                <th className="p-3">Duración</th>
                <th className="p-3">Fecha & Hora</th>
                <th className="p-3 text-right">Acción</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {isLoadingTasks ? (
                <tr>
                  <td colSpan={7} className="py-10 text-center text-slate-500 text-xs">
                    Cargando tareas desde Redis...
                  </td>
                </tr>
              ) : filteredTasks.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-10 text-center text-slate-500 text-xs">
                    No se encontraron tareas registradas para el filtro seleccionado.
                  </td>
                </tr>
              ) : (
                filteredTasks.map((t) => {
                  const taskBrand = t.brand_id || t.client_id;
                  const client = clients.find((c) => c.id === taskBrand);
                  const clientName = client ? client.nombre : `Cliente #${taskBrand}`;
                  const isCurrentBrand = taskBrand === activeBrandId;
                  const dateStr = t.created_at
                    ? new Date(t.created_at * 1000).toLocaleString()
                    : '-';

                  return (
                    <tr
                      key={t.task_id}
                      onClick={() => handleSelectTask(t.task_id)}
                      className={`hover:bg-slate-800/40 cursor-pointer transition group ${
                        isCurrentBrand ? 'bg-indigo-950/10' : ''
                      }`}
                    >
                      <td className="p-3 font-mono text-[11px] text-indigo-400">
                        <div className="flex items-center gap-1.5">
                          <span>{t.task_id.slice(0, 8)}...</span>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              copyText(t.task_id);
                            }}
                            className="text-slate-600 hover:text-slate-300 opacity-0 group-hover:opacity-100 transition"
                            title="Copiar ID completo"
                          >
                            <Copy className="w-3 h-3" />
                          </button>
                        </div>
                      </td>
                      <td className="p-3">
                        <span
                          className={`text-[10px] font-semibold px-2 py-0.5 rounded border inline-flex items-center gap-1 ${getBrandBadgeStyle(
                            taskBrand
                          )}`}
                        >
                          <Building2 className="w-2.5 h-2.5" />
                          <span>{clientName}</span>
                          <span className="opacity-70 font-mono">#{taskBrand}</span>
                        </span>
                      </td>
                      <td className="p-3 text-slate-300 max-w-xs truncate font-medium">
                        {t.brief_content || 'Brief estándar por perfil'}
                      </td>
                      <td className="p-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase font-mono ${
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
                      <td className="p-3 font-mono text-slate-400 text-[11px]">
                        {t.duration_seconds ? `${t.duration_seconds}s` : '-'}
                      </td>
                      <td className="p-3 text-slate-400 text-[11px]">{dateStr}</td>
                      <td className="p-3 text-right">
                        <span className="text-indigo-400 hover:underline font-semibold flex items-center justify-end gap-1">
                          Auditar <ArrowRight className="w-3 h-3" />
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
