import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import {
  BookOpen,
  Search,
  Copy,
  Calendar,
  Send,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Check,
  AlertCircle,
  FileCode,
  Layers,
} from 'lucide-react';

export function LibraryView() {
  const {
    selectedClient,
    ideas,
    selectedIdea,
    selectIdea,
    ideaLibraryOffset,
    setIdeaLibraryOffset,
    ideaLibraryTotal,
    ideaLibraryQuery,
    setIdeaLibraryQuery,
    isLoadingIdeas,
    loadIdeas,
    brandChannels,
    publishSelectedIdea,
    copyText,
    isExecuting,
    showToast,
  } = useApp();

  // Estados locales para publicación
  const [selectedChannels, setSelectedChannels] = useState([]);
  const [publishMode, setPublishMode] = useState('draft');
  const [publishAt, setPublishAt] = useState('');
  const [isPublishing, setIsPublishing] = useState(false);
  const [showJsonDossier, setShowJsonDossier] = useState(false);

  // Pre-seleccionar canal si no hay ninguno seleccionado
  useEffect(() => {
    if (brandChannels.length > 0 && selectedChannels.length === 0) {
      setSelectedChannels([brandChannels[0].external_id]);
    }
  }, [brandChannels]);

  // Buscar al presionar Enter
  const handleSearchKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      setIdeaLibraryOffset(0);
      loadIdeas(ideaLibraryQuery, 0);
    }
  };

  const handlePrevPage = () => {
    const newOffset = Math.max(0, ideaLibraryOffset - 50);
    setIdeaLibraryOffset(newOffset);
    loadIdeas(ideaLibraryQuery, newOffset);
  };

  const handleNextPage = () => {
    if (ideaLibraryOffset + 50 < ideaLibraryTotal) {
      const newOffset = ideaLibraryOffset + 50;
      setIdeaLibraryOffset(newOffset);
      loadIdeas(ideaLibraryQuery, newOffset);
    }
  };

  // Validación de canales y publicación
  const incompleteChannelsCount = brandChannels.filter(
    (c) => selectedChannels.includes(c.external_id) && !c.configured
  ).length;

  const handlePreparePublish = async () => {
    if (!selectedIdea) return;
    if (selectedChannels.length === 0) {
      showToast('Selecciona al menos un canal destino para preparar los copies.', 'warning');
      return;
    }
    if (publishMode === 'schedule' && !publishAt) {
      showToast('Selecciona la fecha y hora de programación.', 'warning');
      return;
    }

    setIsPublishing(true);
    try {
      await publishSelectedIdea({
        mode: publishMode,
        publishAt: publishMode === 'schedule' ? publishAt : null,
        integrations: selectedChannels,
      });
    } catch (err) {
      // error handled in context
    } finally {
      setIsPublishing(false);
    }
  };

  const dossier = selectedIdea?.dossier || {};
  const summaryFields = [
    { label: 'Concepto Central', value: dossier.concept },
    { label: 'Objetivo de Campaña', value: dossier.objective },
    { label: 'Audiencia Objetivo', value: dossier.audience },
    { label: 'Mensaje Clave', value: dossier.key_message },
    { label: 'Call to Action (CTA)', value: dossier.cta },
    { label: 'Por Qué Funciona (Razón Estratégica)', value: dossier.why_it_works },
  ].filter((f) => f.value);

  return (
    <div className="space-y-6">
      {/* Encabezado */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-indigo-400" /> Biblioteca de Ideas & Dossiers Persistidos
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Explora las campañas generadas para {selectedClient?.nombre || 'la marca'}. Selecciona una idea para revisar su preproducción y preparar copies.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs px-2.5 py-1 rounded-lg bg-indigo-950/80 text-indigo-300 border border-indigo-800 font-semibold flex items-center gap-1.5 shadow-sm">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span>Marca: {selectedClient?.nombre} (ID: {selectedClient?.brand_id || selectedClient?.id})</span>
          </span>
          <span className="text-xs font-mono px-3 py-1 rounded-lg bg-slate-900 border border-slate-800 text-cyan-300">
            {ideaLibraryTotal} dossiers en BD
          </span>
        </div>
      </div>

      {/* Grid Principal (Master - Detail) */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
        {/* Panel Izquierdo: Buscador & Listado (4 cols) */}
        <div className="xl:col-span-4 space-y-3">
          {/* Buscador */}
          <div className="flex gap-2">
            <div className="relative flex-1">
              <input
                type="search"
                value={ideaLibraryQuery}
                onChange={(e) => setIdeaLibraryQuery(e.target.value)}
                onKeyDown={handleSearchKeyDown}
                placeholder="Buscar en títulos y conceptos..."
                className="w-full bg-slate-900 border border-slate-700/80 rounded-xl pl-8 pr-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-medium"
              />
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
            </div>
            <button
              onClick={() => {
                setIdeaLibraryOffset(0);
                loadIdeas(ideaLibraryQuery, 0);
              }}
              className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium"
            >
              Buscar
            </button>
          </div>

          {/* Lista de Ideas */}
          <div className="rounded-xl bo-surface border border-slate-800 divide-y divide-slate-800/80 max-h-[620px] overflow-y-auto">
            {isLoadingIdeas ? (
              <div className="py-12 text-center text-xs text-slate-500">Cargando biblioteca...</div>
            ) : ideas.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-500 px-4">
                No hay ideas guardadas para esta búsqueda. Genera un lote en el Studio para verlas aquí.
              </div>
            ) : (
              ideas.map((idea) => {
                const isSelected = selectedIdea?.id === idea.id;
                const ideaDossier = idea.dossier || {};
                const title = ideaDossier.title || idea.title || `Idea #${idea.id}`;
                const concept = ideaDossier.concept || idea.content || '';
                const dateStr = idea.created_at ? new Date(idea.created_at).toLocaleDateString() : 'Guardada';

                return (
                  <button
                    key={idea.id}
                    onClick={() => selectIdea(idea.id)}
                    className={`w-full text-left p-3.5 transition block group ${
                      isSelected
                        ? 'bg-indigo-950/40 border-l-4 border-amber-400 pl-3'
                        : 'hover:bg-slate-900/60'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-bold text-white group-hover:text-indigo-300 truncate">
                        {title}
                      </span>
                      <span className="font-mono text-[10px] text-slate-400 shrink-0">
                        #{idea.id}
                      </span>
                    </div>

                    <p className="mt-1 text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                      {concept}
                    </p>

                    <div className="mt-2 flex items-center justify-between text-[10px] text-slate-400">
                      <span>{dateStr}</span>
                      {idea.generation_batch_id && (
                        <span className="font-mono text-cyan-400">lote</span>
                      )}
                    </div>
                  </button>
                );
              })
            )}
          </div>

          {/* Paginación */}
          <div className="flex items-center justify-between text-xs px-1">
            <button
              onClick={handlePrevPage}
              disabled={ideaLibraryOffset === 0 || isLoadingIdeas}
              className="px-2.5 py-1 rounded bg-slate-900 text-slate-300 border border-slate-800 disabled:opacity-30 hover:bg-slate-800 flex items-center gap-1"
            >
              <ChevronLeft className="w-3.5 h-3.5" /> Anterior
            </button>
            <span className="text-[11px] font-mono text-slate-400">
              {ideas.length > 0 ? `${ideaLibraryOffset + 1} - ${ideaLibraryOffset + ideas.length}` : '0'} de {ideaLibraryTotal}
            </span>
            <button
              onClick={handleNextPage}
              disabled={ideaLibraryOffset + 50 >= ideaLibraryTotal || isLoadingIdeas}
              className="px-2.5 py-1 rounded bg-slate-900 text-slate-300 border border-slate-800 disabled:opacity-30 hover:bg-slate-800 flex items-center gap-1"
            >
              Siguiente <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Panel Derecho: Detalle de Idea & Publicación (8 cols) */}
        <div className="xl:col-span-8 space-y-6">
          {selectedIdea ? (
            <div className="space-y-6">
              {/* Dossier Card */}
              <div className="p-6 rounded-2xl bo-surface border border-slate-800 space-y-5">
                <div className="flex flex-wrap items-start justify-between gap-3 pb-4 border-b border-slate-800">
                  <div>
                    <span className="text-[11px] font-mono uppercase text-amber-400 font-bold">
                      Idea #{selectedIdea.id}
                    </span>
                    <h3 className="text-lg font-bold text-white mt-0.5">
                      {dossier.title || selectedIdea.title || 'Idea de Campaña'}
                    </h3>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => copyText(selectedIdea.content || JSON.stringify(dossier, null, 2))}
                      className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-medium flex items-center gap-1.5 transition"
                    >
                      <Copy className="w-3.5 h-3.5" /> Copiar Dossier
                    </button>
                  </div>
                </div>

                {/* Campos Estratégicos */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {summaryFields.map((field, idx) => (
                    <div key={idx} className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                        {field.label}
                      </span>
                      <p className="text-xs text-slate-200 leading-relaxed whitespace-pre-wrap">
                        {field.value}
                      </p>
                    </div>
                  ))}
                </div>

                {/* Visor JSON Completo */}
                <div className="pt-2 border-t border-slate-800">
                  <button
                    onClick={() => setShowJsonDossier(!showJsonDossier)}
                    className="text-xs font-semibold text-cyan-400 hover:text-cyan-300 flex items-center gap-1.5"
                  >
                    <FileCode className="w-3.5 h-3.5" />
                    <span>{showJsonDossier ? 'Ocultar JSON Estructurado' : 'Ver Dossier JSON Estructurado'}</span>
                  </button>

                  {showJsonDossier && (
                    <pre className="mt-3 p-4 rounded-xl bg-slate-950 border border-slate-800 font-mono text-[11px] text-slate-300 max-h-80 overflow-auto whitespace-pre-wrap leading-relaxed">
                      {JSON.stringify(dossier, null, 2)}
                    </pre>
                  )}
                </div>
              </div>

              {/* Barra de Publicación y Programación */}
              <div className="p-6 rounded-2xl bo-surface border border-slate-800 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div>
                    <h4 className="text-sm font-bold text-white flex items-center gap-2">
                      <Send className="w-4 h-4 text-emerald-400" /> Preparación de Publicación en Redes
                    </h4>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Selecciona los canales destino. El agente generará variantes personalizadas sin publicar de inmediato.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
                  {/* Canales (7 cols) */}
                  <div className="md:col-span-7 space-y-2">
                    <label className="text-xs font-semibold text-slate-300 block">
                      Canales Vinculados a {selectedClient?.nombre}:
                    </label>

                    {brandChannels.length === 0 ? (
                      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-400">
                        No hay canales activos vinculados. Ve a la pestaña de Studio para asociar integraciones Postiz.
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {brandChannels.map((ch) => {
                          const isChecked = selectedChannels.includes(ch.external_id);
                          return (
                            <label
                              key={ch.external_id}
                              className={`p-2.5 rounded-xl border text-xs cursor-pointer transition flex items-center gap-2.5 ${
                                isChecked
                                  ? 'bg-indigo-950/40 border-indigo-500 text-indigo-200'
                                  : 'bg-slate-900 border-slate-800 text-slate-300 hover:bg-slate-800/60'
                              }`}
                            >
                              <input
                                type="checkbox"
                                checked={isChecked}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setSelectedChannels([...selectedChannels, ch.external_id]);
                                  } else {
                                    setSelectedChannels(selectedChannels.filter((id) => id !== ch.external_id));
                                  }
                                }}
                                className="rounded text-indigo-600 focus:ring-0 bg-slate-800 border-slate-700"
                              />
                              <div className="min-w-0">
                                <span className="font-semibold block truncate">
                                  {ch.display_name || ch.external_id}
                                </span>
                                <span className="text-[10px] text-slate-400 block font-mono">
                                  {ch.provider} {!ch.configured && '· no configurado'}
                                </span>
                              </div>
                            </label>
                          );
                        })}
                      </div>
                    )}

                    {incompleteChannelsCount > 0 && (
                      <p className="text-[11px] text-amber-300 flex items-center gap-1">
                        <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                        {incompleteChannelsCount} canal(es) seleccionado(s) no tienen configuración completa en Postiz.
                      </p>
                    )}
                  </div>

                  {/* Modo y Fecha (5 cols) */}
                  <div className="md:col-span-5 space-y-3">
                    <div>
                      <label className="text-xs font-semibold text-slate-300 block mb-1">Modo de Envío:</label>
                      <select
                        value={publishMode}
                        onChange={(e) => setPublishMode(e.target.value)}
                        className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-medium"
                      >
                        <option value="draft">Guardar como Borrador</option>
                        <option value="schedule">Programar para fecha futura</option>
                        <option value="now">Publicar Inmediatamente</option>
                      </select>
                    </div>

                    {publishMode === 'schedule' && (
                      <div>
                        <label className="text-xs font-semibold text-slate-300 block mb-1">Fecha & Hora Objetivo:</label>
                        <input
                          type="datetime-local"
                          value={publishAt}
                          onChange={(e) => setPublishAt(e.target.value)}
                          className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
                        />
                      </div>
                    )}

                    <div className="pt-2">
                      <button
                        type="button"
                        onClick={handlePreparePublish}
                        disabled={selectedChannels.length === 0 || isPublishing || isExecuting}
                        className="w-full py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold text-xs transition shadow-md shadow-emerald-600/30 flex items-center justify-center gap-2 disabled:opacity-40"
                      >
                        <Sparkles className="w-4 h-4" />
                        <span>{isPublishing ? 'Preparando...' : 'Preparar Copies para Revisar'}</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-16 rounded-2xl bo-surface border border-slate-800 text-center text-slate-400 space-y-3">
              <BookOpen className="w-10 h-10 text-slate-600 mx-auto" />
              <h3 className="text-base font-bold text-slate-200">Ninguna idea seleccionada</h3>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                Selecciona una idea del panel izquierdo para inspeccionar su dossier creativo, justificación y opciones de publicación.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
