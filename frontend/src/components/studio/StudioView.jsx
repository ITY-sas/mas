import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import {
  Sparkles,
  Link2,
  Unlink,
  Video,
  FileImage,
  Wand2,
  Layers,
  Building2,
  Check,
  AlertTriangle,
  HelpCircle,
  ShieldCheck,
  Share2,
  RotateCw,
  ExternalLink,
} from 'lucide-react';

export function StudioView() {
  const {
    clients,
    selectedClient,
    handleSelectClient,
    brandChannels,
    loadBrandChannels,
    availablePostizIntegrations,
    loadPostizIntegrations,
    linkBrandChannel,
    unlinkBrandChannel,
    submitBrief,
    isExecuting,
    showToast,
  } = useApp();

  const [contentFormat, setContentFormat] = useState('reel');
  const [ideaCount, setIdeaCount] = useState(5);
  const [mainBrief, setMainBrief] = useState('');
  const [individualBriefs, setIndividualBriefs] = useState('');
  const [topics, setTopics] = useState('');
  const [selectedIntegration, setSelectedIntegration] = useState('');
  const [isLinking, setIsLinking] = useState(false);

  const templates = [
    {
      title: '🌱 EcoBrand - Protector Solar',
      clientId: 1,
      format: 'reel',
      content:
        'Crear un Reel para presentar una crema solar natural y biodegradable durante el verano colombiano, destacando cero impacto en arrecifes.',
    },
    {
      title: '💳 TechStart - Pagos QR',
      clientId: 2,
      format: 'reel',
      content:
        'Lanzar un Reel dinámico explicando cómo pequeños comerciantes y cafeterías pueden recibir pagos con código QR al instante y sin comisiones ocultas.',
    },
    {
      title: '💪 FitLife - Reto 30 Días',
      clientId: 3,
      format: 'post',
      content:
        'Diseñar un carrusel educativo para invitar a la comunidad al Reto 30 Días de Hábitos Saludables con suplementos naturales basados en evidencia.',
    },
  ];

  const handleApplyTemplate = (t) => {
    const client = clients.find((c) => c.id === t.clientId);
    if (client) handleSelectClient(client);
    setContentFormat(t.format);
    setMainBrief(t.content);
    showToast(`Plantilla "${t.title}" cargada`, 'info');
  };

  const handleLinkIntegration = async () => {
    if (!selectedClient || !selectedIntegration) {
      showToast('Selecciona una integración Postiz disponible.', 'warning');
      return;
    }
    const brandId = selectedClient.brand_id || selectedClient.id;
    const target = availablePostizIntegrations.find((i) => i.external_id === selectedIntegration);
    const isOther = target?.linked_brand_id && target.linked_brand_id !== brandId;
    if (
      isOther &&
      !window.confirm(
        `El canal está actualmente vinculado a "${target.linked_brand_name}". ¿Deseas transferirlo a ${selectedClient.nombre}?`
      )
    ) {
      return;
    }
    setIsLinking(true);
    try {
      await linkBrandChannel(brandId, selectedIntegration, true);
      setSelectedIntegration('');
    } catch (err) {
      // Error handled in context
    } finally {
      setIsLinking(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (isExecuting) return;

    const briefsList = individualBriefs
      .split('\n')
      .map((b) => b.trim())
      .filter(Boolean);

    if (briefsList.length > ideaCount) {
      showToast(`Usa como máximo ${ideaCount} brief(s) individuales para este lote.`, 'warning');
      return;
    }

    const topicsList = topics
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);

    try {
      await submitBrief({
        content: mainBrief.trim(),
        briefs: briefsList,
        topics: topicsList,
        count: Number(ideaCount),
        content_format: contentFormat,
      });
    } catch (err) {
      // toast shown in context
    }
  };

  return (
    <div className="space-y-6">
      {/* Header section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-amber-400" /> Generador de Campañas & Lotes de Ideas
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Genera hasta 5 dossiers creativos en paralelo. Cada resultado se preserva en la biblioteca antes de cualquier publicación.
          </p>
        </div>
        <span className="text-xs px-2.5 py-1 rounded bg-slate-900 text-slate-400 border border-slate-800 font-mono">
          supervisor:8002
        </span>
      </div>

      {/* 1-Click Templates */}
      <div className="p-4 rounded-xl bo-surface border border-slate-800">
        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-2.5">
          Plantillas Rápidas de Prueba (1-Clic):
        </span>
        <div className="flex flex-wrap gap-2">
          {templates.map((t, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleApplyTemplate(t)}
              className="px-3 py-1.5 rounded-lg text-xs bg-slate-900/90 hover:bg-slate-800 text-slate-200 border border-slate-700/80 transition flex items-center gap-2 text-left"
            >
              <span>{t.title}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Main Form (8 cols) */}
        <div className="lg:col-span-8">
          <form onSubmit={handleSubmit} className="p-6 rounded-2xl bo-surface border border-slate-800 space-y-5">
            {/* Cliente y Formato */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Cliente / Marca:</label>
                <select
                  value={selectedClient?.id || 1}
                  onChange={(e) => {
                    const client = clients.find((c) => c.id === Number(e.target.value));
                    if (client) handleSelectClient(client);
                  }}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-medium"
                >
                  {clients.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.nombre} ({c.producto_servicio?.slice(0, 30) || c.pais})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Formato de Contenido:</label>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => setContentFormat('auto')}
                    className={`py-2 px-2 text-xs font-medium rounded-xl border text-center transition ${
                      contentFormat === 'auto'
                        ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300'
                        : 'bg-slate-900 border-slate-700 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Auto
                  </button>
                  <button
                    type="button"
                    onClick={() => setContentFormat('reel')}
                    className={`py-2 px-2 text-xs font-medium rounded-xl border text-center transition flex items-center justify-center gap-1 ${
                      contentFormat === 'reel'
                        ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300'
                        : 'bg-slate-900 border-slate-700 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Video className="w-3.5 h-3.5 text-rose-400" /> Reel
                  </button>
                  <button
                    type="button"
                    onClick={() => setContentFormat('post')}
                    className={`py-2 px-2 text-xs font-medium rounded-xl border text-center transition flex items-center justify-center gap-1 ${
                      contentFormat === 'post'
                        ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300'
                        : 'bg-slate-900 border-slate-700 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <FileImage className="w-3.5 h-3.5 text-cyan-400" /> Post
                  </button>
                </div>
              </div>
            </div>

            {/* Brief Principal */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-semibold text-slate-300">Brief Principal (Opcional):</label>
                <span className="text-[11px] text-slate-400">Si está vacío, usa el perfil de marca y señales de mercado</span>
              </div>
              <textarea
                rows={4}
                value={mainBrief}
                onChange={(e) => setMainBrief(e.target.value)}
                placeholder="Ejemplo: Crear una campaña de lanzamiento para un nuevo protector solar ecológico resistente al agua..."
                className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-sans leading-relaxed resize-y"
              />
            </div>

            {/* Briefs Individuales */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Briefs Individuales por Línea (Opcional):
              </label>
              <textarea
                rows={2}
                value={individualBriefs}
                onChange={(e) => setIndividualBriefs(e.target.value)}
                placeholder="Cada línea alimentará una idea independiente del lote..."
                className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-y"
              />
            </div>

            {/* Cantidad de ideas y Temas */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Ideas en este Lote:</label>
                <div className="flex gap-2">
                  {[1, 2, 3, 4, 5].map((count) => (
                    <button
                      key={count}
                      type="button"
                      onClick={() => setIdeaCount(count)}
                      className={`flex-1 py-1.5 rounded-lg text-xs font-bold font-mono transition border ${
                        ideaCount === count
                          ? 'bg-indigo-600 text-white border-indigo-500 shadow-sm shadow-indigo-600/30'
                          : 'bg-slate-900 text-slate-400 border-slate-700 hover:text-white'
                      }`}
                    >
                      {count}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Temas o Pilares (Opcional):</label>
                <input
                  type="text"
                  value={topics}
                  onChange={(e) => setTopics(e.target.value)}
                  placeholder="ej. educación, comunidad, producto"
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-medium"
                />
              </div>
            </div>

            {/* Gestión de Canales Sociales & Postiz */}
            <div className="pt-3 border-t border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Share2 className="w-4 h-4 text-cyan-400" />
                  <span className="text-xs font-semibold text-slate-200">
                    Canales de Publicación Social (Postiz)
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      if (selectedClient) {
                        const bId = selectedClient.brand_id || selectedClient.id;
                        loadBrandChannels(bId);
                      }
                      loadPostizIntegrations();
                      showToast('Sincronizando catálogo con Postiz...', 'info');
                    }}
                    className="text-[11px] text-slate-400 hover:text-cyan-300 flex items-center gap-1 transition px-2 py-0.5 rounded border border-slate-800 bg-slate-900/60"
                    title="Actualizar catálogo de Postiz"
                  >
                    <RotateCw className="w-3 h-3" />
                    <span>Sincronizar</span>
                  </button>
                  <a
                    href="http://localhost:5000"
                    target="_blank"
                    rel="noreferrer"
                    className="text-[11px] text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition"
                  >
                    <span>Abrir Postiz</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </div>

              {/* Canales actualmente vinculados a esta marca */}
              <div className="space-y-1.5">
                <span className="text-[11px] font-medium text-slate-400 block">
                  Canales Activos para {selectedClient?.nombre || 'esta Marca'}:
                </span>
                {brandChannels.length === 0 ? (
                  <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80 text-[11px] text-slate-400 flex items-center justify-between">
                    <span>Sin canales asociados. Vincula una integración de Postiz abajo para habilitar entrega directa.</span>
                    <span className="px-2 py-0.5 rounded bg-amber-950/60 text-amber-300 border border-amber-800/60 text-[10px]">
                      Sin vincular
                    </span>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {brandChannels.map((ch) => (
                      <div
                        key={ch.external_id}
                        className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between text-xs group"
                      >
                        <div className="min-w-0 pr-2">
                          <div className="font-semibold text-slate-200 truncate flex items-center gap-1.5">
                            <span className="w-2 h-2 rounded-full bg-emerald-400 shrink-0"></span>
                            <span className="truncate">{ch.display_name || ch.external_id}</span>
                          </div>
                          <span className="text-[10px] text-slate-400 uppercase font-mono">
                            {ch.provider} · {ch.configured ? 'Configurado' : 'Pendiente'}
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={async () => {
                            if (window.confirm(`¿Desvincular "${ch.display_name || ch.provider}" de ${selectedClient?.nombre}?`)) {
                              const bId = selectedClient.brand_id || selectedClient.id;
                              await unlinkBrandChannel(bId, ch.external_id);
                            }
                          }}
                          className="p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-rose-950/40 border border-transparent hover:border-rose-900/60 transition shrink-0"
                          title="Desvincular este canal"
                        >
                          <Unlink className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Selector para vincular una nueva integración disponible */}
              <div className="pt-2 border-t border-slate-800/60 space-y-1.5">
                <span className="text-[11px] font-medium text-slate-400 block">
                  Vincular o Reasignar Integración de Postiz:
                </span>
                <div className="flex flex-col sm:flex-row gap-2">
                  <select
                    value={selectedIntegration}
                    onChange={(e) => setSelectedIntegration(e.target.value)}
                    className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="">Selecciona integración detectada en Postiz...</option>
                    {availablePostizIntegrations.map((item) => {
                      const brandId = selectedClient?.brand_id || selectedClient?.id;
                      const isLinkedHere = item.linked_brand_id === brandId;
                      const isLinkedOther = item.linked_brand_id && item.linked_brand_id !== brandId;
                      let badge = isLinkedHere
                        ? ' [Ya Vinculado a esta Marca]'
                        : isLinkedOther
                        ? ` [En ${item.linked_brand_name || 'otra marca'}]`
                        : ' [Disponible]';
                      return (
                        <option
                          key={item.external_id}
                          value={item.external_id}
                          disabled={isLinkedHere}
                        >
                          {item.display_name} ({item.provider}){badge}
                        </option>
                      );
                    })}
                  </select>

                  <button
                    type="button"
                    onClick={handleLinkIntegration}
                    disabled={!selectedIntegration || isLinking}
                    className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-500 text-white font-medium text-xs transition border border-indigo-500 disabled:border-slate-700 flex items-center justify-center gap-1.5 shrink-0"
                  >
                    <Link2 className="w-3.5 h-3.5 text-cyan-300" />
                    <span>{isLinking ? 'Vinculando...' : 'Vincular a Marca'}</span>
                  </button>
                </div>
                <p className="text-[11px] text-slate-500">
                  {availablePostizIntegrations.length === 0
                    ? 'No se detectaron integraciones en Postiz. Abre Postiz para conectar cuentas sociales (LinkedIn, Instagram, etc.).'
                    : `${availablePostizIntegrations.length} cuenta(s) social(es) detectada(s) en Postiz.`}
                </p>
              </div>
            </div>

            {/* Submit Action */}
            <div className="pt-4 flex items-center justify-between border-t border-slate-800">
              <span className="text-[11px] text-slate-400 flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-emerald-400" /> Supervisor LangGraph con persistencia en Redis
              </span>

              <button
                type="submit"
                disabled={isExecuting}
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 via-indigo-500 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 text-white font-semibold text-xs transition shadow-lg shadow-indigo-600/30 flex items-center gap-2 disabled:opacity-50"
              >
                <Sparkles className="w-4 h-4" />
                <span>{isExecuting ? 'Procesando Lote...' : `Generar Lote (${ideaCount} ideas)`}</span>
              </button>
            </div>
          </form>
        </div>

        {/* Right: Brand Preview & Execution Guide (4 cols) */}
        <div className="lg:col-span-4 space-y-6">
          {/* Perfil de Marca Activo */}
          <div className="p-5 rounded-2xl bo-surface border border-slate-800 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <span className="text-xs font-bold text-white flex items-center gap-1.5">
                <Building2 className="w-3.5 h-3.5 text-indigo-400" /> {selectedClient?.nombre}
              </span>
              <span className="text-[10px] font-mono bg-indigo-950 text-indigo-300 border border-indigo-800/80 px-2 py-0.5 rounded">
                {selectedClient?.pais || 'Colombia'}
              </span>
            </div>

            <div className="text-xs space-y-2 text-slate-300">
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

              {/* Canales sociales en ficha de marca */}
              <div className="pt-2 border-t border-slate-800">
                <span className="text-slate-400 text-[10px] uppercase font-semibold block mb-1">
                  Canales Sociales Vinculados:
                </span>
                {brandChannels.length === 0 ? (
                  <span className="text-slate-500 text-[11px] italic">Sin canales vinculados</span>
                ) : (
                  <div className="flex flex-wrap gap-1.5">
                    {brandChannels.map((ch) => (
                      <span
                        key={ch.external_id}
                        className="text-[10px] px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-300 font-medium flex items-center gap-1"
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                        <span>{ch.display_name || ch.provider}</span>
                        <span className="text-slate-500 uppercase text-[9px]">({ch.provider})</span>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Ciclo de Ejecución Informativo */}
          <div className="p-5 rounded-2xl bo-surface border border-slate-800 space-y-3 text-xs">
            <span className="font-bold text-slate-200 block border-b border-slate-800 pb-2 flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-cyan-400" /> Ciclo de Vida de la Campaña
            </span>

            <div className="space-y-2.5 text-[11px] text-slate-300">
              <div className="flex items-start gap-2">
                <span className="w-4 h-4 rounded-full bg-slate-800 text-slate-400 flex items-center justify-center text-[9px] shrink-0 mt-0.5 font-bold">1</span>
                <span>Supervisor LangGraph checkpointea en RedisSaver y despacha a RabbitMQ.</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="w-4 h-4 rounded-full bg-slate-800 text-slate-400 flex items-center justify-center text-[9px] shrink-0 mt-0.5 font-bold">2</span>
                <span>Agente de Ideación invoca Tools: perfil, tendencias pgvector, competencia, RSS news.</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="w-4 h-4 rounded-full bg-slate-800 text-slate-400 flex items-center justify-center text-[9px] shrink-0 mt-0.5 font-bold">3</span>
                <span>El dossier completo se almacena en PostgreSQL y queda en la Biblioteca.</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="w-4 h-4 rounded-full bg-slate-800 text-slate-400 flex items-center justify-center text-[9px] shrink-0 mt-0.5 font-bold">4</span>
                <span>La publicación solo se despacha cuando seleccionas canales y apruebas los copys.</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
