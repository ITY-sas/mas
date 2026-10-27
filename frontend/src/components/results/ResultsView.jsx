import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import {
  FileText,
  Copy,
  Download,
  Film,
  Video,
  Share2,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Clapperboard,
  Heart,
  MessageCircle,
  Bookmark,
  Send,
  Eye,
  BookOpen,
  Lock,
} from 'lucide-react';

export function ResultsView() {
  const {
    currentTask,
    latestIdeaBatch,
    activeStudioWorkflow,
    selectedClient,
    copyText,
    exportDossier,
    approvePreparedPublication,
    deliverPreparedPublication,
    selectIdea,
    setActiveTab,
    showToast,
  } = useApp();

  // Variantes editables en vivo para preparaciones pendientes
  const [editedVariants, setEditedVariants] = useState([]);
  const [isApproving, setIsApproving] = useState(false);
  const [isDelivering, setIsDelivering] = useState(false);

  const result = currentTask?.result || {};
  const idea = result.idea || '';
  const publication = result.publication || '';
  const postizResult = result.postiz || {};
  const publicationVariants = (result.publication_variants || []).filter(
    (v) => v.platform && v.platform !== 'platform-neutral'
  );
  const preprod = result.preproduction || {};
  const brief = currentTask?.brief || {};
  const publicationConfig = brief.publication || {};

  const isPrepared =
    brief.workflow === 'prepare_publication' &&
    ['prepared', 'approved_pending'].includes(postizResult.status);
  const isApprovedPending = postizResult.status === 'approved_pending';

  // Inicializar variantes editables
  useEffect(() => {
    if (result.publication_variants) {
      setEditedVariants(result.publication_variants.map((v) => ({ ...v })));
    }
  }, [result.publication_variants]);

  const handleVariantContentChange = (index, newContent) => {
    setEditedVariants((prev) => {
      const copy = [...prev];
      copy[index] = { ...copy[index], content: newContent };
      return copy;
    });
  };

  const handleApprove = async () => {
    if (!currentTask) return;
    setIsApproving(true);
    try {
      await approvePreparedPublication(currentTask.task_id, editedVariants);
    } catch (err) {
      // error handled in context
    } finally {
      setIsApproving(false);
    }
  };

  const handleDeliver = async () => {
    if (!currentTask) return;
    setIsDelivering(true);
    try {
      await deliverPreparedPublication(currentTask.task_id, editedVariants);
    } catch (err) {
      // error handled in context
    } finally {
      setIsDelivering(false);
    }
  };

  const handleOpenIdeaInLibrary = async (ideaId) => {
    if (!ideaId) return;
    await selectIdea(ideaId);
    setActiveTab('library');
  };

  // ── MODO 1: Resultados de Lote Completo ────────────────────────
  if (activeStudioWorkflow === 'batch' && latestIdeaBatch) {
    const ideas = latestIdeaBatch.ideas || [];
    return (
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-amber-400" /> Resultados del Lote de Campaña
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              {latestIdeaBatch.completed || 0} de {latestIdeaBatch.total || 0} dossiers completados. Cada idea conserva su propio dossier técnico.
            </p>
          </div>
          <span className="font-mono text-xs text-slate-400 bg-slate-900 px-3 py-1 rounded-full border border-slate-800">
            {latestIdeaBatch.generation_batch_id || 'Lote'}
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {ideas.map((item, idx) => {
            const dossier = item.dossier || {};
            const isCompleted = item.status === 'completed' && Object.keys(dossier).length > 0;

            return (
              <div
                key={idx}
                className="p-5 rounded-2xl bo-surface border border-slate-800 space-y-4 bo-card-interactive"
              >
                <div className="flex items-start justify-between gap-3 pb-2 border-b border-slate-800">
                  <div>
                    <span className="text-[10px] font-mono uppercase text-amber-400 font-bold">
                      Idea {idx + 1} {item.idea_id ? `• #${item.idea_id}` : ''}
                    </span>
                    <h3 className="text-sm font-bold text-white mt-0.5">
                      {dossier.title || item.title || (item.status === 'failed' ? 'Generación fallida' : 'Generando...')}
                    </h3>
                  </div>

                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold border ${
                      isCompleted
                        ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                        : item.status === 'failed'
                        ? 'bg-rose-950 text-rose-300 border-rose-800'
                        : 'bg-cyan-950 text-cyan-300 border-cyan-800 animate-pulse'
                    }`}
                  >
                    {isCompleted ? 'Lista' : item.status === 'failed' ? 'Fallida' : 'En proceso'}
                  </span>
                </div>

                {isCompleted ? (
                  <div className="space-y-3 text-xs">
                    <div>
                      <span className="text-[10px] uppercase font-semibold text-slate-400 block">Concepto:</span>
                      <p className="text-slate-200 mt-0.5 leading-relaxed">{dossier.concept || 'N/A'}</p>
                    </div>

                    {dossier.objective && (
                      <div>
                        <span className="text-[10px] uppercase font-semibold text-slate-400 block">Objetivo:</span>
                        <p className="text-slate-300 mt-0.5">{dossier.objective}</p>
                      </div>
                    )}

                    <div className="pt-2 flex items-center justify-between border-t border-slate-800/80">
                      <button
                        onClick={() => copyText(JSON.stringify(dossier, null, 2))}
                        className="text-xs text-slate-400 hover:text-white flex items-center gap-1"
                      >
                        <Copy className="w-3 h-3" /> Copiar JSON
                      </button>

                      {item.idea_id && (
                        <button
                          onClick={() => handleOpenIdeaInLibrary(item.idea_id)}
                          className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs flex items-center gap-1.5 transition"
                        >
                          <BookOpen className="w-3.5 h-3.5" /> Abrir en Biblioteca
                        </button>
                      )}
                    </div>
                  </div>
                ) : item.status === 'failed' ? (
                  <p className="text-xs text-rose-300">{item.error || 'No se pudo generar esta idea.'}</p>
                ) : (
                  <p className="text-xs text-slate-500 py-6 text-center">
                    El agente está sintetizando las herramientas y el dossier aparecerá aquí en breve...
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // ── MODO 2: Resultados de Tarea Individual ─────────────────────
  if (!currentTask || (!idea && !publication)) {
    return (
      <div className="p-16 rounded-2xl bo-surface border border-slate-800 text-center text-slate-400 space-y-3">
        <Clapperboard className="w-10 h-10 text-slate-600 mx-auto" />
        <h3 className="text-base font-bold text-slate-200">No hay resultados activos para visualizar</h3>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          Ejecuta una campaña desde el Studio o selecciona una tarea desde el Historial para revisar su dossier y publicación.
        </p>
      </div>
    );
  }

  const scripts = preprod.script || [];
  const cameras = preprod.camera || [];

  return (
    <div className="space-y-6">
      {/* Header con opciones de exportación */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <FileText className="w-5 h-5 text-indigo-400" /> Resultados & Dossier Creativo Completo
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Tarea <span className="font-mono text-slate-300">{currentTask.task_id}</span> para{' '}
            <span className="font-semibold text-slate-200">{selectedClient?.nombre}</span>
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => exportDossier('markdown')}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold flex items-center gap-1.5 transition"
          >
            <Download className="w-3.5 h-3.5" /> Exportar Markdown
          </button>
          <button
            onClick={() => exportDossier('json')}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold flex items-center gap-1.5 transition"
          >
            <Download className="w-3.5 h-3.5" /> Exportar JSON
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Columna Izquierda (7 cols): Idea & Dossier Técnico */}
        <div className="lg:col-span-7 space-y-6">
          {/* Card: Idea de Campaña */}
          {idea && (
            <div className="p-6 rounded-2xl bo-surface border border-slate-800 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <span className="w-8 h-8 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center">
                    <Sparkles className="w-4 h-4" />
                  </span>
                  <div>
                    <h3 className="text-sm font-bold text-white">Idea de Campaña (Agente de Ideación)</h3>
                    <span className="text-[10px] font-mono text-slate-400">ID #{result.idea_id || 'N/A'}</span>
                  </div>
                </div>

                <button
                  onClick={() => copyText(idea)}
                  className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs flex items-center gap-1 border border-slate-700"
                >
                  <Copy className="w-3 h-3" /> Copiar Idea
                </button>
              </div>

              <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 text-xs text-slate-200 whitespace-pre-line leading-relaxed">
                {idea}
              </div>
            </div>
          )}

          {/* Card: Dossier Técnico de Preproducción */}
          {preprod && Object.keys(preprod).length > 0 && (
            <div className="p-6 rounded-2xl bo-surface border border-slate-800 space-y-5">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <span className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                    <Clapperboard className="w-4 h-4" />
                  </span>
                  <div>
                    <h3 className="text-sm font-bold text-white">Dossier Técnico de Preproducción</h3>
                    <span className="text-[10px] font-mono text-slate-400">
                      {preprod.format || 'Audiovisual'} ({preprod.duration_seconds || 30}s)
                    </span>
                  </div>
                </div>
              </div>

              {/* Ficha rápida */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="text-[10px] font-bold uppercase text-slate-400 block mb-1">
                    Concepto Central:
                  </span>
                  <p className="text-slate-200">{preprod.concept || 'N/A'}</p>
                </div>
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="text-[10px] font-bold uppercase text-slate-400 block mb-1">
                    Por Qué Funciona:
                  </span>
                  <p className="text-slate-200">{preprod.why_it_works || 'N/A'}</p>
                </div>
              </div>

              {/* Guión Escena por Escena */}
              {scripts.length > 0 && (
                <div>
                  <h4 className="text-xs font-bold text-slate-200 uppercase tracking-wider mb-2 flex items-center gap-2">
                    <Film className="w-3.5 h-3.5 text-indigo-400" /> Guión Escena por Escena
                  </h4>
                  <div className="overflow-x-auto rounded-xl border border-slate-800">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-900 text-slate-400 uppercase text-[10px] font-semibold tracking-wider">
                        <tr>
                          <th className="p-2.5 w-12 text-center">#</th>
                          <th className="p-2.5 w-16">Dur.</th>
                          <th className="p-2.5">Visual & Acción</th>
                          <th className="p-2.5">Locución / Diálogo</th>
                          <th className="p-2.5">Texto en Pantalla</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/80 font-sans">
                        {scripts.map((s, sIdx) => (
                          <tr key={sIdx} className="hover:bg-slate-900/50">
                            <td className="p-2.5 font-bold text-center text-indigo-400">{s.scene || sIdx + 1}</td>
                            <td className="p-2.5 font-mono text-slate-400">{s.duration_seconds ? `${s.duration_seconds}s` : '-'}</td>
                            <td className="p-2.5 text-slate-200">
                              {s.visual || ''}
                              {s.action && <span className="text-slate-400 italic block mt-0.5">{s.action}</span>}
                            </td>
                            <td className="p-2.5 text-slate-300">{s.dialogue_or_voiceover || '-'}</td>
                            <td className="p-2.5 text-amber-300 font-mono text-[11px]">{s.on_screen_text || '-'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Especificaciones de Cámara */}
              {cameras.length > 0 && (
                <div>
                  <h4 className="text-xs font-bold text-slate-200 uppercase tracking-wider mb-2 flex items-center gap-2">
                    <Video className="w-3.5 h-3.5 text-cyan-400" /> Especificaciones de Cámara
                  </h4>
                  <div className="overflow-x-auto rounded-xl border border-slate-800">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-900 text-slate-400 uppercase text-[10px] font-semibold tracking-wider">
                        <tr>
                          <th className="p-2.5 w-12 text-center">#</th>
                          <th className="p-2.5">Plano (Shot)</th>
                          <th className="p-2.5">Ángulo</th>
                          <th className="p-2.5">Movimiento</th>
                          <th className="p-2.5">Encuadre</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/80 font-sans">
                        {cameras.map((c, cIdx) => (
                          <tr key={cIdx} className="hover:bg-slate-900/50">
                            <td className="p-2.5 font-bold text-center text-cyan-400">{c.scene || cIdx + 1}</td>
                            <td className="p-2.5 text-slate-200 font-semibold">{c.shot || '-'}</td>
                            <td className="p-2.5 text-slate-300">{c.angle || '-'}</td>
                            <td className="p-2.5 text-slate-300">{c.movement || '-'}</td>
                            <td className="p-2.5 text-slate-400 font-mono text-[11px]">{c.framing || '-'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Locación, Audio y Notas */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs pt-1">
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">Locación & Arte:</span>
                  <p className="text-slate-300">{preprod.location_and_art_direction || 'N/A'}</p>
                </div>
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">Audio & Música:</span>
                  <p className="text-slate-300">{preprod.audio || 'N/A'}</p>
                </div>
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">Notas de Edición:</span>
                  <p className="text-slate-300">{preprod.editing_notes || 'N/A'}</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Columna Derecha (5 cols): Publicación & Mockup Social */}
        <div className="lg:col-span-5 space-y-6">
          {/* Card: Publicación Generada */}
          <div className="p-6 rounded-2xl bo-surface border border-slate-800 space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <span className="w-8 h-8 rounded-lg bg-sky-500/20 text-sky-400 flex items-center justify-center">
                  <Share2 className="w-4 h-4" />
                </span>
                <div>
                  <h3 className="text-sm font-bold text-white">Publicación Multicanal</h3>
                  <span className="text-[10px] font-mono text-slate-400">ID #{result.publication_id || 'N/A'}</span>
                </div>
              </div>
              {['created', 'sent', 'scheduled'].includes(postizResult.status) && (
                <span className="px-2.5 py-1 rounded-lg text-[11px] font-mono bg-emerald-950/80 text-emerald-300 border border-emerald-800 flex items-center gap-1 font-semibold">
                  <Lock className="w-3.5 h-3.5 text-emerald-400" /> Inmutable · Enviado
                </span>
              )}
            </div>

            {/* Variantes por Plataforma (Editables en modo preparación) */}
            {editedVariants.length > 0 && (
              <div className="space-y-3">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                  Variantes por Plataforma:
                </span>
                {editedVariants.map((variant, vIdx) => (
                  <div key={vIdx} className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-cyan-300">{variant.platform}</span>
                      <span className="text-[10px] font-mono text-slate-400">
                        {variant.content.length} caracteres
                      </span>
                    </div>

                    {isPrepared ? (
                      <div>
                        <label className="text-[10px] text-slate-400 block mb-1">
                          Copy Editable / Para Revisar:
                        </label>
                        <textarea
                          rows={4}
                          value={variant.content}
                          onChange={(e) => handleVariantContentChange(vIdx, e.target.value)}
                          className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 font-sans leading-relaxed resize-y"
                        />
                      </div>
                    ) : (
                      <p className="text-xs text-slate-200 whitespace-pre-wrap leading-relaxed">
                        {variant.content}
                      </p>
                    )}

                    <div className="flex justify-end">
                      <button
                        onClick={() => copyText(variant.content)}
                        className="text-[11px] text-slate-400 hover:text-white flex items-center gap-1"
                      >
                        <Copy className="w-3 h-3" /> Copiar {variant.platform}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Postiz State Card */}
            <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 text-xs space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span
                  className={`font-semibold ${
                    postizResult.status === 'failed'
                      ? 'text-rose-400'
                      : isPrepared
                      ? 'text-amber-400'
                      : postizResult.status === 'created'
                      ? 'text-emerald-400'
                      : 'text-slate-300'
                  }`}
                >
                  {isApprovedPending
                    ? 'Copy aprobado; pendiente de envío'
                    : isPrepared
                    ? 'Preparado; pendiente de aprobación'
                    : postizResult.status === 'created'
                    ? 'Solicitud aceptada por Postiz'
                    : postizResult.status === 'failed'
                    ? 'Postiz reportó un error'
                    : postizResult.status || 'Estado de Postiz'}
                </span>
                <span className="text-slate-400 text-[11px]">
                  Modo: {publicationConfig.mode || postizResult.mode || 'draft'}
                </span>
              </div>

              <p className="text-[11px] text-slate-400">
                Canales: {(publicationConfig.integration_ids || postizResult.integrations || []).join(', ') || 'ninguno'}
              </p>

              {postizResult.error && (
                <p className="text-[11px] text-rose-300">{postizResult.error}</p>
              )}

              {/* Botones de Aprobación y Entrega */}
              {isPrepared && (
                <div className="pt-2 flex flex-wrap gap-2 border-t border-slate-800/80">
                  <button
                    type="button"
                    onClick={handleApprove}
                    disabled={isApproving}
                    className="flex-1 py-2 px-3 rounded-xl border border-amber-700 bg-amber-950/40 text-amber-200 text-xs font-semibold hover:bg-amber-900/50 transition disabled:opacity-50"
                  >
                    {isApprovedPending ? 'Guardar Cambios Pendientes' : 'Aprobar y Dejar Pendiente'}
                  </button>

                  <button
                    type="button"
                    onClick={handleDeliver}
                    disabled={isDelivering}
                    className="flex-1 py-2 px-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition disabled:opacity-50 shadow-md shadow-emerald-600/20"
                  >
                    {isApprovedPending ? 'Enviar a Postiz' : 'Aprobar y Enviar'}
                  </button>
                </div>
              )}
            </div>

            {/* Mockup de Red Social */}
            {publicationVariants.length === 0 && publication && (
              <div className="p-4 rounded-2xl bg-black border border-neutral-800 space-y-3 shadow-2xl">
                <div className="flex items-center justify-between pb-2 border-b border-neutral-800">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-amber-500 to-rose-500 flex items-center justify-center text-[10px] font-bold text-white">
                      {selectedClient ? selectedClient.nombre.slice(0, 2).toUpperCase() : 'AG'}
                    </div>
                    <div>
                      <span className="text-xs font-bold text-white block leading-tight">
                        {selectedClient?.nombre || 'Marca'}
                      </span>
                      <span className="text-[10px] text-neutral-400">Patrocinado</span>
                    </div>
                  </div>
                </div>

                {/* Media box */}
                <div className="aspect-video bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 rounded-xl border border-neutral-800 flex flex-col items-center justify-center p-4 text-center">
                  <Video className="w-8 h-8 text-rose-400 mb-2 opacity-80" />
                  <span className="text-xs font-bold text-slate-200">{preprod.title || 'Campaña Oficial'}</span>
                  <span className="text-[10px] text-slate-400 mt-0.5">{preprod.format || 'Formato Audiovisual'}</span>
                </div>

                {/* Botones de acción */}
                <div className="flex items-center justify-between text-neutral-300 text-sm px-1">
                  <div className="flex items-center gap-3">
                    <Heart className="w-4 h-4 hover:text-rose-500 cursor-pointer" />
                    <MessageCircle className="w-4 h-4 hover:text-indigo-400 cursor-pointer" />
                    <Send className="w-4 h-4 hover:text-sky-400 cursor-pointer" />
                  </div>
                  <Bookmark className="w-4 h-4 hover:text-amber-400 cursor-pointer" />
                </div>

                {/* Caption */}
                <p className="text-xs text-neutral-200 whitespace-pre-wrap leading-relaxed px-1">
                  <span className="font-bold mr-1.5 text-white">{selectedClient?.nombre || 'Marca'}</span>
                  {publication}
                </p>
              </div>
            )}

            {/* Contador de caracteres & Copiar */}
            <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-xs">
              <span className="text-slate-400">
                Longitud: <strong className="text-white">{publication.length}</strong> chars
              </span>
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                  publication.length <= 280
                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                    : 'bg-amber-950 text-amber-300 border border-amber-800'
                }`}
              >
                {publication.length <= 280 ? '≤ 280 (X/Twitter OK)' : 'Copy Base'}
              </span>
            </div>

            <button
              onClick={() => copyText(publication)}
              className="w-full py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition flex items-center justify-center gap-1.5 shadow-md shadow-indigo-600/30"
            >
              <Copy className="w-3.5 h-3.5" /> Copiar Publicación
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
