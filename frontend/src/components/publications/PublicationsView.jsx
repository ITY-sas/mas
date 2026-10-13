import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import {
  Send,
  Search,
  RotateCw,
  Copy,
  PenSquare,
  ExternalLink,
  GitBranch,
  Calendar,
  AlertCircle,
  CheckCircle2,
  Clock,
  Share2,
} from 'lucide-react';

export function PublicationsView() {
  const {
    selectedClient,
    publications,
    isLoadingPublications,
    loadPublications,
    sendApprovedPublication,
    loadTaskDetails,
    setCurrentTaskId,
    setActiveTab,
    copyText,
  } = useApp();

  const [statusFilter, setStatusFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  // Asegurar carga de publicaciones al montar o cambiar cliente
  useEffect(() => {
    if (selectedClient) {
      loadPublications();
    }
  }, [selectedClient?.id, selectedClient?.brand_id]);

  const statusLabels = {
    preparing: 'Preparando Copy',
    awaiting_approval: 'Pendiente de Aprobación',
    approved_pending: 'Aprobado · Pendiente de Envío',
    sending: 'Enviando a Redes',
    sent: 'Enviado a Postiz',
    scheduled: 'Programado',
    draft: 'Borrador Guardado',
    failed: 'Error de Entrega',
    skipped: 'Omitido',
    pending: 'Pendiente',
  };

  const statusStyles = {
    preparing: 'bg-cyan-950 text-cyan-300 border-cyan-800',
    awaiting_approval: 'bg-amber-950 text-amber-300 border-amber-800',
    approved_pending: 'bg-amber-900/60 text-amber-200 border-amber-700',
    sending: 'bg-cyan-950 text-cyan-300 border-cyan-800',
    sent: 'bg-emerald-950 text-emerald-300 border-emerald-800',
    scheduled: 'bg-sky-950 text-sky-300 border-sky-800',
    draft: 'bg-slate-800 text-slate-300 border-slate-700',
    failed: 'bg-rose-950 text-rose-300 border-rose-800',
    skipped: 'bg-slate-900 text-slate-400 border-slate-700',
    pending: 'bg-slate-800 text-slate-300 border-slate-700',
  };

  const modeLabels = {
    now: 'Envío Inmediato',
    schedule: 'Programado',
    draft: 'Borrador',
  };

  const filteredPublications = publications.filter((pub) => {
    const searchable = [
      pub.task_id,
      pub.error,
      ...(pub.channels || []).flatMap((c) => [c.display_name, c.provider, c.content]),
    ]
      .join(' ')
      .toLowerCase();

    const matchesStatus = !statusFilter || pub.status === statusFilter;
    const matchesSearch = !searchQuery || searchable.includes(searchQuery.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Send className="w-5 h-5 text-emerald-400" /> Historial de Entregas & Publicaciones Postiz
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Seguimiento por marca de copies preparados, aprobaciones y despachos hacia Postiz. El estado refleja la respuesta de entrega.
          </p>
        </div>
        <button
          onClick={loadPublications}
          disabled={isLoadingPublications}
          className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 flex items-center gap-1.5 transition self-start md:self-auto"
        >
          <RotateCw className={`w-3.5 h-3.5 ${isLoadingPublications ? 'animate-spin' : ''}`} />
          <span>Actualizar Entregas</span>
        </button>
      </div>

      {/* Filtros y Buscador */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <input
            type="search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Buscar por copy, canal, proveedor o ID de tarea..."
            className="w-full bg-slate-900 border border-slate-700/80 rounded-xl pl-8 pr-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-medium"
          />
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
        </div>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-medium sm:w-64"
        >
          <option value="">Todos los Estados ({publications.length})</option>
          <option value="awaiting_approval">Pendiente de Aprobación</option>
          <option value="approved_pending">Aprobado · Pendiente de Envío</option>
          <option value="sending">Enviando</option>
          <option value="sent">Enviado a Postiz</option>
          <option value="scheduled">Programado</option>
          <option value="draft">Borrador</option>
          <option value="failed">Error</option>
          <option value="skipped">Omitido</option>
        </select>
      </div>

      {/* Contador de resultados */}
      <div className="text-[11px] text-slate-400 font-mono">
        Mostrando {filteredPublications.length} de {publications.length} entregas registradas
      </div>

      {/* Lista de Publicaciones */}
      <div className="space-y-4">
        {isLoadingPublications ? (
          <div className="p-12 text-center text-xs text-slate-500">Cargando publicaciones...</div>
        ) : filteredPublications.length === 0 ? (
          <div className="p-12 rounded-xl bo-surface border border-slate-800 text-center text-slate-500 text-xs">
            {publications.length === 0
              ? 'Aún no hay entregas o preparaciones registradas para esta marca.'
              : 'No hay publicaciones que coincidan con los filtros aplicados.'}
          </div>
        ) : (
          filteredPublications.map((pub, idx) => {
            const status = pub.status || 'pending';
            const createdAtStr = pub.created_at
              ? new Date(pub.created_at * 1000).toLocaleString()
              : 'Fecha no disponible';
            const publishAtStr = pub.publish_at ? new Date(pub.publish_at).toLocaleString() : '';

            const isPendingApproval = status === 'awaiting_approval';
            const isApprovedPending =
              status === 'approved_pending' ||
              (status === 'failed' && pub.workflow === 'deliver_publication' && pub.prepare_task_id);

            return (
              <div
                key={pub.task_id || idx}
                className="p-5 rounded-2xl bo-surface border border-slate-800 space-y-4 bo-card-interactive"
              >
                {/* Header de la Publicación */}
                <div className="flex flex-wrap items-start justify-between gap-3 pb-3 border-b border-slate-800/80">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-white">
                        {pub.idea_id ? `Idea #${pub.idea_id}` : 'Publicación Multicanal'}
                      </span>
                      <span className="font-mono text-[11px] text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                        {pub.task_id ? pub.task_id.slice(0, 8) : 'N/A'}
                      </span>
                    </div>
                    <p className="mt-1 text-[11px] text-slate-400">
                      {modeLabels[pub.mode] || pub.mode || 'Entrega'} • {createdAtStr}
                      {publishAtStr && ` • Fecha Programada: ${publishAtStr}`}
                    </p>
                  </div>

                  {/* Acciones y Badges */}
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`px-2.5 py-1 rounded text-xs font-semibold border ${
                        statusStyles[status] || statusStyles.pending
                      }`}
                    >
                      {statusLabels[status] || status}
                    </span>

                    {/* Botón Revisar Copy */}
                    {isPendingApproval && (
                      <button
                        onClick={() => {
                          setCurrentTaskId(pub.task_id);
                          loadTaskDetails(pub.task_id);
                          setActiveTab('results');
                        }}
                        className="px-2.5 py-1 rounded bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold flex items-center gap-1 transition"
                      >
                        <PenSquare className="w-3.5 h-3.5" /> Revisar Copy
                      </button>
                    )}

                    {/* Botón Enviar a Postiz */}
                    {isApprovedPending && (
                      <button
                        onClick={() => sendApprovedPublication(pub)}
                        className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1 transition shadow-sm"
                      >
                        <Send className="w-3.5 h-3.5" />
                        <span>{status === 'failed' ? 'Reintentar Envío' : 'Enviar a Postiz'}</span>
                      </button>
                    )}

                    {/* Botón Trazabilidad */}
                    <button
                      onClick={() => {
                        setCurrentTaskId(pub.task_id);
                        loadTaskDetails(pub.task_id);
                        setActiveTab('traceability');
                      }}
                      className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 flex items-center gap-1 transition"
                    >
                      <GitBranch className="w-3.5 h-3.5 text-cyan-400" /> Traza
                    </button>

                    {/* Enlace Postiz */}
                    <a
                      href="http://localhost:4007"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 flex items-center gap-1 transition"
                    >
                      <span>Postiz</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                </div>

                {/* Error si existió */}
                {pub.error && (
                  <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-800/80 text-xs text-rose-300 flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                    <span>{pub.error}</span>
                  </div>
                )}

                {/* Variantes por Canal */}
                <div className="space-y-3">
                  {(pub.channels || []).map((ch, chIdx) => (
                    <div
                      key={chIdx}
                      className="p-3.5 rounded-xl bg-slate-900/70 border border-slate-800 space-y-2"
                    >
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-slate-200">{ch.display_name || ch.external_id}</span>
                          <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/80 px-1.5 py-0.5 rounded border border-cyan-900/50">
                            {ch.provider}
                          </span>
                        </div>
                        <button
                          onClick={() => copyText(ch.content)}
                          className="text-[11px] text-slate-400 hover:text-white flex items-center gap-1 transition"
                        >
                          <Copy className="w-3 h-3" /> Copiar Copy
                        </button>
                      </div>

                      <p className="text-xs text-slate-300 whitespace-pre-wrap leading-relaxed">
                        {ch.content || 'Sin copy disponible para este canal.'}
                      </p>
                    </div>
                  ))}
                  {(!pub.channels || pub.channels.length === 0) && (
                    <p className="text-xs text-slate-500 italic">No hay canales asociados a esta entrega.</p>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
