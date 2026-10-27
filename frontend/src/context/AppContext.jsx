import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { API } from '../api/client';

const AppContext = createContext(null);

const DEFAULT_CLIENTS = [
  {
    id: 1,
    brand_id: 1,
    nombre: 'EcoBrand',
    perfil_marca: 'Marca de productos ecológicos y sostenibles dirigida a millennials conscientes del medio ambiente.',
    restricciones_tono: 'Cercano pero profesional. Evitar greenwashing. No usar mayúsculas excesivas.',
    historico: "Campañas 'Reto Zero Waste' (+340% engagement) y 'Cada Gota Cuenta'.",
    producto_servicio: 'Protector solar y cosmética natural con ingredientes responsables.',
    audiencia_objetivo: 'Personas de 18 a 35 años en Colombia interesadas en sostenibilidad.',
    objetivo_marketing: 'Aumentar reconocimiento y contenido compartible en redes sociales.',
    pais: 'Colombia',
    zona_horaria: 'America/Bogota',
  },
  {
    id: 2,
    brand_id: 2,
    nombre: 'TechStart',
    perfil_marca: 'Startup fintech que simplifica pagos para pequeños comercios en Latinoamérica.',
    restricciones_tono: 'Joven, directo, confiable. Usar datos y cifras. Evitar jerga compleja.',
    historico: "Campañas 'Pagos sin Fricción' (15K leads) y 'Tu Negocio en tu Bolsillo'.",
    producto_servicio: 'App móvil para recibir pagos y administrar ventas.',
    audiencia_objetivo: 'Comercios independientes y pequeñas empresas en Colombia.',
    objetivo_marketing: 'Generar registros y demostrar cobros digitales sencillos.',
    pais: 'Colombia',
    zona_horaria: 'America/Bogota',
  },
  {
    id: 3,
    brand_id: 3,
    nombre: 'FitLife',
    perfil_marca: 'Marca de nutrición y fitness con suplementos naturales y planes de hábitos.',
    restricciones_tono: 'Motivador pero no agresivo. Basar afirmaciones en evidencia científica.',
    historico: "Campañas '30 Días de Cambio' (22K participantes) y 'Nutre tu Mente'.",
    producto_servicio: 'Suplementos naturales y planes de entrenamiento personalizados.',
    audiencia_objetivo: 'Adultos de 25 a 45 años en Colombia interesados en salud integral.',
    objetivo_marketing: 'Aumentar consideración de producto y retos saludables.',
    pais: 'Colombia',
    zona_horaria: 'America/Bogota',
  },
];

export function AppProvider({ children }) {
  // Navegación
  const [activeTab, setActiveTab] = useState('dashboard');

  // Datos de clientes y marcas
  const [clients, setClients] = useState(DEFAULT_CLIENTS);
  const [selectedClient, setSelectedClient] = useState(DEFAULT_CLIENTS[0]);
  const [brandChannels, setBrandChannels] = useState([]);
  const [availablePostizIntegrations, setAvailablePostizIntegrations] = useState([]);

  // Biblioteca de Ideas
  const [ideas, setIdeas] = useState([]);
  const [selectedIdea, setSelectedIdea] = useState(null);
  const [ideaLibraryOffset, setIdeaLibraryOffset] = useState(0);
  const [ideaLibraryTotal, setIdeaLibraryTotal] = useState(0);
  const [ideaLibraryQuery, setIdeaLibraryQuery] = useState('');
  const [isLoadingIdeas, setIsLoadingIdeas] = useState(false);

  // Publicaciones
  const [publications, setPublications] = useState([]);
  const [isLoadingPublications, setIsLoadingPublications] = useState(false);

  // Trazabilidad, Pipeline y Lotes
  const [currentTaskId, setCurrentTaskId] = useState(null);
  const [currentTask, setCurrentTask] = useState(null);
  const [currentTrace, setCurrentTrace] = useState(null);
  const [ideaBatch, setIdeaBatch] = useState(null);
  const [latestIdeaBatch, setLatestIdeaBatch] = useState(null);
  const [activeBatchTraceTaskId, setActiveBatchTraceTaskId] = useState(null);
  const [activeStudioWorkflow, setActiveStudioWorkflow] = useState(null);

  // Historial de Tareas
  const [tasks, setTasks] = useState([]);
  const [isLoadingTasks, setIsLoadingTasks] = useState(false);

  // Estado del sistema y salud
  const [health, setHealth] = useState(null);
  const [overview, setOverview] = useState({
    tasks: { total: 0, completed: 0, running: 0, failed: 0 },
    rag: { ideas: 0, publicaciones: 0 },
    clients_count: 0,
    tools_count: 0,
  });
  const [toolsCatalog, setToolsCatalog] = useState([]);
  const [ragStats, setRagStats] = useState({ ideas: 0, publicaciones: 0 });

  // Ejecución en progreso
  const [isExecuting, setIsExecuting] = useState(false);
  const [liveStreamStatus, setLiveStreamStatus] = useState('');
  const streamSubRef = useRef(null);
  const batchPollTimerRef = useRef(null);

  // Notificaciones Toast
  const [toasts, setToasts] = useState([]);

  const showToast = useCallback((message, type = 'info') => {
    const id = Date.now() + Math.random().toString(36).substring(2, 6);
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  }, []);

  const copyText = useCallback((text) => {
    if (!text) return;
    navigator.clipboard.writeText(text).then(
      () => showToast('¡Copiado al portapapeles!', 'success'),
      () => showToast('No se pudo copiar automáticamente', 'error')
    );
  }, [showToast]);

  // ── Carga de Canales e Integraciones ──────────────────────────
  const loadBrandChannels = useCallback(async (brandId) => {
    if (!brandId) return;
    try {
      const channels = await API.getBrandChannels(brandId);
      setBrandChannels(channels || []);
    } catch (err) {
      console.warn('Error cargando canales:', err);
      setBrandChannels([]);
    }
  }, []);

  const loadPostizIntegrations = useCallback(async () => {
    try {
      const integrations = await API.getPostizIntegrations();
      setAvailablePostizIntegrations(integrations || []);
    } catch (err) {
      console.warn('Error cargando catálogo Postiz:', err);
      setAvailablePostizIntegrations([]);
    }
  }, []);

  const linkBrandChannel = useCallback(async (brandId, externalId, reassign = false) => {
    if (!brandId || !externalId) return;
    try {
      const res = await API.linkBrandChannel(brandId, externalId, reassign);
      await Promise.all([
        loadBrandChannels(brandId),
        loadPostizIntegrations(),
      ]);
      if (res?.transferred) {
        showToast('Canal transferido exitosamente a esta marca.', 'success');
      } else {
        showToast('Canal Postiz vinculado a la marca exitosamente.', 'success');
      }
      return res;
    } catch (err) {
      showToast('No se pudo vincular el canal: ' + err.message, 'error');
      throw err;
    }
  }, [loadBrandChannels, loadPostizIntegrations, showToast]);

  const unlinkBrandChannel = useCallback(async (brandId, externalId) => {
    if (!brandId || !externalId) return;
    try {
      await API.unlinkBrandChannel(brandId, externalId);
      await Promise.all([
        loadBrandChannels(brandId),
        loadPostizIntegrations(),
      ]);
      showToast('Canal Postiz desvinculado de la marca.', 'info');
    } catch (err) {
      showToast('No se pudo desvincular el canal: ' + err.message, 'error');
      throw err;
    }
  }, [loadBrandChannels, loadPostizIntegrations, showToast]);

  // ── Carga de Ideas (Biblioteca) ──────────────────────────────
  const loadIdeas = useCallback(async (query = ideaLibraryQuery, offset = ideaLibraryOffset, overrideBrandId = null) => {
    const brandId = overrideBrandId || selectedClient?.brand_id || selectedClient?.id;
    if (!brandId) return;
    setIsLoadingIdeas(true);
    try {
      const result = await API.getIdeas(brandId, {
        query,
        limit: 50,
        offset,
      });
      setIdeas(result.items || []);
      setIdeaLibraryTotal(result.total || 0);
    } catch (err) {
      console.warn('Error cargando ideas:', err);
      setIdeas([]);
    } finally {
      setIsLoadingIdeas(false);
    }
  }, [selectedClient, ideaLibraryQuery, ideaLibraryOffset]);

  const selectIdea = useCallback(async (ideaId) => {
    if (!selectedClient) return;
    const brandId = selectedClient.brand_id || selectedClient.id;
    try {
      const fullIdea = await API.getIdea(ideaId, brandId);
      setSelectedIdea(fullIdea);
    } catch (err) {
      showToast('Error cargando dossier de idea: ' + err.message, 'error');
    }
  }, [selectedClient, showToast]);

  const updateIdea = useCallback(async (ideaId, data) => {
    if (!selectedClient) return;
    const brandId = selectedClient.brand_id || selectedClient.id;
    try {
      const res = await API.updateIdea(ideaId, brandId, data);
      await Promise.all([loadIdeas(), selectIdea(ideaId)]);
      showToast('Idea actualizada y re-indexada en memoria vectorial RAG.', 'success');
      return res;
    } catch (err) {
      showToast('Error al actualizar idea: ' + err.message, 'error');
      throw err;
    }
  }, [selectedClient, loadIdeas, selectIdea, showToast]);

  const deleteIdea = useCallback(async (ideaId) => {
    if (!selectedClient) return;
    const brandId = selectedClient.brand_id || selectedClient.id;
    try {
      const res = await API.deleteIdea(ideaId, brandId);
      setSelectedIdea(null);
      await loadIdeas();
      showToast('Idea archivada exitosamente.', 'info');
      return res;
    } catch (err) {
      showToast('Conflicto: ' + err.message, 'error');
      throw err;
    }
  }, [selectedClient, loadIdeas, showToast]);

  // ── Carga de Publicaciones ──────────────────────────────────
  const loadPublications = useCallback(async (overrideBrandId = null) => {
    const brandId = overrideBrandId || selectedClient?.brand_id || selectedClient?.id;
    if (!brandId) return;
    setIsLoadingPublications(true);
    try {
      const result = await API.getPublications(brandId);
      setPublications(result.items || []);
    } catch (err) {
      console.warn('Error cargando publicaciones:', err);
      setPublications([]);
    } finally {
      setIsLoadingPublications(false);
    }
  }, [selectedClient]);

  const updatePublication = useCallback(async (pubId, data) => {
    if (!selectedClient) return;
    const brandId = selectedClient.brand_id || selectedClient.id;
    try {
      const res = await API.updatePublication(pubId, brandId, data);
      await loadPublications();
      showToast('Publicación actualizada exitosamente.', 'success');
      return res;
    } catch (err) {
      showToast('Error de ciclo de vida / inmutabilidad: ' + err.message, 'error');
      throw err;
    }
  }, [selectedClient, loadPublications, showToast]);

  const deletePublication = useCallback(async (pubId) => {
    if (!selectedClient) return;
    const brandId = selectedClient.brand_id || selectedClient.id;
    try {
      const res = await API.deletePublication(pubId, brandId);
      await loadPublications();
      showToast('Publicación archivada exitosamente.', 'info');
      return res;
    } catch (err) {
      showToast('Error de ciclo de vida / inmutabilidad: ' + err.message, 'error');
      throw err;
    }
  }, [selectedClient, loadPublications, showToast]);

  // ── Selección y Gestión de Clientes / Marcas ────────────────
  const loadClients = useCallback(async () => {
    try {
      const clientsList = await API.getClients();
      if (clientsList && clientsList.length > 0) {
        setClients(clientsList);
        setSelectedClient((prev) => {
          if (!prev) return clientsList[0];
          const found = clientsList.find((c) => (c.brand_id || c.id) === (prev.brand_id || prev.id));
          return found || clientsList[0];
        });
      }
    } catch (err) {
      console.warn('Error cargando clientes:', err);
    }
  }, []);

  const updateBrand = useCallback(async (brandId, data) => {
    try {
      const res = await API.updateBrand(brandId, data);
      await loadClients();
      showToast('Configuración de marca y RAG actualizada exitosamente.', 'success');
      return res;
    } catch (err) {
      showToast('Error al actualizar marca: ' + err.message, 'error');
      throw err;
    }
  }, [loadClients, showToast]);

  const deleteBrand = useCallback(async (brandId) => {
    try {
      const res = await API.deleteBrand(brandId);
      await loadClients();
      showToast('Marca archivada exitosamente.', 'info');
      return res;
    } catch (err) {
      showToast('Error al archivar marca: ' + err.message, 'error');
      throw err;
    }
  }, [loadClients, showToast]);

  const handleSelectClient = useCallback((client) => {
    if (!client) return;
    setSelectedClient(client);
    setSelectedIdea(null);
    setIdeaLibraryOffset(0);
    const brandId = client.brand_id || client.id;
    loadBrandChannels(brandId);
    loadIdeas('', 0, brandId);
    loadPublications(brandId);
  }, [loadBrandChannels, loadIdeas, loadPublications]);

  // ── Carga de Historial de Tareas (Redis) ────────────────────
  const loadTasks = useCallback(async (statusFilter = null, brandId = null) => {
    setIsLoadingTasks(true);
    try {
      const result = await API.getTasks(statusFilter, 100, brandId);
      setTasks(result || []);
    } catch (err) {
      console.warn('Error cargando tareas de Redis:', err);
      setTasks([]);
    } finally {
      setIsLoadingTasks(false);
    }
  }, []);

  // ── Salud y Sistema ─────────────────────────────────────────
  const checkSystemHealth = useCallback(async () => {
    try {
      const [healthData, overviewData, ragData] = await Promise.all([
        API.getHealth(),
        API.getOverview(),
        API.getRagStats(),
      ]);
      setHealth(healthData);
      setOverview(overviewData);
      if (ragData?.data) {
        setRagStats(ragData.data);
      }
    } catch (err) {
      console.warn('Error en monitoreo de salud:', err);
    }
  }, []);

  const loadToolsCatalog = useCallback(async () => {
    try {
      const toolsData = await API.getTools();
      setToolsCatalog(toolsData.tools || []);
    } catch (err) {
      console.warn('Error catálogo tools:', err);
    }
  }, []);

  // ── Detalle de Tarea y Trazabilidad ─────────────────────────
  const loadTaskDetails = useCallback(async (taskId) => {
    try {
      const trace = await API.getTaskTrace(taskId);
      setCurrentTrace(trace);
      setCurrentTask(trace.raw_task);
      setCurrentTaskId(taskId);
    } catch (err) {
      showToast('Error al cargar traza de tarea: ' + err.message, 'error');
    }
  }, [showToast]);

  // ── SSE Stream de Tarea ─────────────────────────────────────
  const startTaskStream = useCallback((taskId) => {
    setActiveStudioWorkflow('task');
    setCurrentTaskId(taskId);
    setIsExecuting(true);
    setLiveStreamStatus(`Conectando stream para tarea ${taskId.slice(0, 8)}...`);

    if (streamSubRef.current) {
      streamSubRef.current.close();
    }

    streamSubRef.current = API.streamTask(
      taskId,
      (data) => {
        if (data.trace) {
          setCurrentTrace(data.trace);
          setCurrentTask(data.trace.raw_task);
        }
        setLiveStreamStatus(`Tarea ${taskId.slice(0, 8)} · Fase: ${(data.status || 'running').toUpperCase()}`);
      },
      (finalData) => {
        setIsExecuting(false);
        setLiveStreamStatus('');
        if (finalData.trace) {
          setCurrentTrace(finalData.trace);
          setCurrentTask(finalData.trace.raw_task);
        }
        loadTasks();
        const postizStatus = finalData.trace?.raw_task?.result?.postiz?.status;
        if (postizStatus === 'prepared') {
          setActiveTab('results');
          showToast('Copies preparados listos para revisión y aprobación.', 'success');
        } else if (postizStatus === 'created') {
          setActiveTab('results');
          showToast('¡Publicación enviada exitosamente a Postiz!', 'success');
        } else if (postizStatus === 'failed') {
          setActiveTab('results');
          showToast('Postiz reportó error en la entrega. Revisa la traza.', 'error');
        } else {
          showToast('Ejecución multi-agente finalizada.', 'success');
        }
      },
      (err) => {
        setIsExecuting(false);
        setLiveStreamStatus('');
        loadTaskDetails(taskId);
      }
    );
  }, [loadTaskDetails, loadTasks, showToast]);

  // ── Polling de Lote de Ideas ────────────────────────────────
  const pollIdeaBatch = useCallback((batchId, brandId) => {
    if (batchPollTimerRef.current) clearInterval(batchPollTimerRef.current);
    let terminal = false;

    const poll = async () => {
      try {
        const batch = await API.getIdeaBatch(batchId, brandId);
        setLatestIdeaBatch(batch);
        loadIdeas();

        const taskIds = (batch.ideas || []).map((i) => i.task_id).filter(Boolean);
        if (taskIds.length > 0) {
          setActiveBatchTraceTaskId((prev) => (prev && taskIds.includes(prev) ? prev : taskIds[0]));
        }

        if (['completed', 'partial', 'failed'].includes(batch.status)) {
          clearInterval(batchPollTimerRef.current);
          batchPollTimerRef.current = null;
          terminal = true;
          setIsExecuting(false);
          setLiveStreamStatus('');
          showToast(`Lote ${batch.status}: ${batch.completed || 0}/${batch.total || 0} ideas completadas.`, 'success');
        }
      } catch (err) {
        console.warn('Error consultando lote:', err);
      }
    };

    poll();
    if (!terminal) {
      batchPollTimerRef.current = setInterval(poll, 3000);
    }
  }, [loadIdeas, showToast]);

  // ── Acciones de Negocio ─────────────────────────────────────

  // Generar Lote
  const submitBrief = useCallback(async ({ content, briefs, topics, count, content_format }) => {
    if (isExecuting || !selectedClient) return;
    const brandId = selectedClient.brand_id || selectedClient.id;

    setIsExecuting(true);
    setLiveStreamStatus(`Iniciando generación de lote (${count} ideas)...`);
    showToast(`Iniciando generación de ${count} idea(s)...`, 'info');

    try {
      const response = await API.generateIdeas({
        client_id: selectedClient.id,
        brand_id: brandId,
        content,
        briefs,
        topics,
        count,
        content_format,
      });

      setIdeaBatch({ id: response.generation_batch_id, brandId });
      setLatestIdeaBatch(null);
      setActiveStudioWorkflow('batch');
      setActiveBatchTraceTaskId(null);
      setActiveTab('traceability');
      showToast(`Lote iniciado: ${count} idea(s). Monitoreando...`, 'success');
      pollIdeaBatch(response.generation_batch_id, brandId);
    } catch (err) {
      setIsExecuting(false);
      setLiveStreamStatus('');
      showToast('Error iniciando lote: ' + err.message, 'error');
      throw err;
    }
  }, [isExecuting, selectedClient, pollIdeaBatch, showToast]);

  // Demo Rápida
  const runDemo = useCallback(async () => {
    if (isExecuting) return;
    setIsExecuting(true);
    setLiveStreamStatus('Lanzando demo rápida con EcoBrand...');
    showToast('Lanzando demo rápida (EcoBrand)...', 'info');

    try {
      const resp = await API.createDemo({
        brand_id: 1,
        content: 'Crear un Reel para presentar una crema solar natural durante el verano colombiano',
        content_format: 'reel',
        wait: false,
      });

      const taskId = resp.task_id;
      if (taskId) {
        setActiveStudioWorkflow('task');
        setActiveTab('traceability');
        startTaskStream(taskId);
        loadTasks();
      }
    } catch (err) {
      setIsExecuting(false);
      setLiveStreamStatus('');
      showToast('Error en demo rápida: ' + err.message, 'error');
    }
  }, [isExecuting, showToast, startTaskStream, loadTasks]);

  // Preparar Copies desde la Biblioteca
  const publishSelectedIdea = useCallback(async ({ mode, publishAt, integrations }) => {
    if (!selectedIdea || !selectedClient) return;
    const brandId = selectedClient.brand_id || selectedClient.id;

    try {
      const result = await API.publishIdea(selectedIdea.id, {
        brand_id: brandId,
        publish_mode: mode,
        publish_at: publishAt ? new Date(publishAt).toISOString() : null,
        integration_ids: integrations,
        settings: {},
      });

      setActiveStudioWorkflow('task');
      setActiveTab('traceability');
      startTaskStream(result.task_id);
      showToast('El publicador está preparando copys personalizados. Se abrirán para tu revisión.', 'info');
    } catch (err) {
      showToast('Error al solicitar preparación: ' + err.message, 'error');
      throw err;
    }
  }, [selectedIdea, selectedClient, startTaskStream, showToast]);

  // Aprobar Copys Preparados
  const approvePreparedPublication = useCallback(async (taskId, variants) => {
    if (!selectedClient) return;
    const brandId = selectedClient.brand_id || selectedClient.id;

    try {
      const approval = await API.approvePreparedPublication(taskId, {
        brand_id: brandId,
        publication_variants: variants,
      });

      if (currentTask && currentTask.task_id === taskId) {
        setCurrentTask({
          ...currentTask,
          result: {
            ...currentTask.result,
            publication_variants: approval.publication_variants,
            publication: approval.publication_variants[0]?.content || '',
            postiz: approval.postiz,
          },
        });
      }

      await loadPublications();
      showToast('Copies aprobados y guardados como pendientes. No se han enviado aún.', 'success');
    } catch (err) {
      showToast('Error al guardar aprobación: ' + err.message, 'error');
      throw err;
    }
  }, [selectedClient, currentTask, loadPublications, showToast]);

  // Entregar Copys a Postiz
  const deliverPreparedPublication = useCallback(async (taskId, variants) => {
    if (!currentTask || currentTask.task_id !== taskId) return;
    const brief = currentTask.brief || {};
    const config = brief.publication || {};

    if (config.mode === 'now' && !window.confirm('¿Confirmas publicar inmediatamente los copies en Postiz?')) {
      return;
    }

    try {
      const delivery = await API.deliverPreparedPublication(taskId, {
        brand_id: brief.brand_id,
        publish_mode: config.mode || 'draft',
        publish_at: config.publish_at || null,
        integration_ids: config.integration_ids || [],
        settings: config.settings || {},
        publication_variants: variants,
      });

      setActiveStudioWorkflow('task');
      setActiveTab('traceability');
      startTaskStream(delivery.task_id);
      showToast('Copies aprobados; despachando entrega hacia Postiz...', 'info');
    } catch (err) {
      showToast('Error al entregar a Postiz: ' + err.message, 'error');
      throw err;
    }
  }, [currentTask, startTaskStream, showToast]);

  // Enviar publicación aprobada desde lista de publicaciones
  const sendApprovedPublication = useCallback(async (publication) => {
    if (!selectedClient) return;
    const brandId = selectedClient.brand_id || selectedClient.id;
    const integrationIds = (publication.channels || []).map((c) => c.external_id).filter(Boolean);
    const variants = (publication.channels || [])
      .filter((c) => c.content?.trim())
      .map((c) => ({
        platform: c.provider || 'platform-neutral',
        integration_ids: [c.external_id],
        content: c.content.trim(),
      }));

    if (!publication.prepare_task_id || !variants.length) {
      showToast('La entrega no contiene copies válidos.', 'warning');
      return;
    }

    if (publication.mode === 'now' && !window.confirm('¿Confirmas enviar ahora los copies aprobados a Postiz?')) {
      return;
    }

    try {
      const delivery = await API.deliverPreparedPublication(publication.prepare_task_id, {
        brand_id: brandId,
        publish_mode: publication.mode || 'draft',
        publish_at: publication.publish_at || null,
        integration_ids: integrationIds,
        settings: publication.settings || {},
        publication_variants: variants,
      });

      setActiveStudioWorkflow('task');
      setActiveTab('traceability');
      startTaskStream(delivery.task_id);
      showToast('Despacho enviado a Postiz.', 'info');
    } catch (err) {
      showToast('Error enviando a Postiz: ' + err.message, 'error');
      await loadPublications();
    }
  }, [selectedClient, startTaskStream, loadPublications, showToast]);

  // Exportar Dossier a MD o JSON
  const exportDossier = useCallback((format = 'markdown') => {
    if (!currentTask) {
      showToast('No hay tarea seleccionada para exportar.', 'warning');
      return;
    }

    let content = '';
    const filename = `campana-${currentTask.task_id.slice(0, 8)}.${format === 'json' ? 'json' : 'md'}`;

    if (format === 'json') {
      content = JSON.stringify(currentTask, null, 2);
    } else {
      const result = currentTask.result || {};
      const preprod = result.preproduction || {};
      content = `# Campaña Multi-Agente: ${preprod.title || 'Nueva Campaña'}\n\n`
        + `**ID Tarea:** ${currentTask.task_id}\n`
        + `**Cliente ID:** ${currentTask.client_id}\n\n`
        + `## 1. Idea de Campaña\n${result.idea || 'N/A'}\n\n`
        + `## 2. Publicación para Redes Sociales\n${result.publication || 'N/A'}\n\n`
        + ((result.publication_variants || []).length
          ? `## Versiones por plataforma\n${result.publication_variants.map((v) => `### ${v.platform}\n${v.content}`).join('\n\n')}\n\n`
          : '')
        + (preprod.concept
          ? `## 3. Dossier de Preproducción\n`
          + `**Concepto:** ${preprod.concept}\n`
          + `**Por qué funciona:** ${preprod.why_it_works || 'N/A'}\n`
          : '');
    }

    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    showToast(`Archivo ${filename} descargado exitosamente.`, 'success');
  }, [currentTask, showToast]);

  const initExecutedRef = useRef(false);
  const activeBrandIdRef = useRef(null);

  // Carga inicial: corre estrictamente una sola vez al montar la aplicación
  useEffect(() => {
    if (initExecutedRef.current) return;
    initExecutedRef.current = true;

    async function init() {
      let initialBrandId = 1;
      try {
        const clientsList = await API.getClients();
        if (clientsList && clientsList.length > 0) {
          setClients(clientsList);
          const firstClient = clientsList[0];
          setSelectedClient(firstClient);
          initialBrandId = firstClient.brand_id || firstClient.id;
        }
      } catch (err) {
        console.warn('Error inicial cargando clientes:', err);
      }

      activeBrandIdRef.current = initialBrandId;

      await Promise.all([
        loadBrandChannels(initialBrandId),
        loadIdeas('', 0, initialBrandId),
        loadPublications(initialBrandId),
        checkSystemHealth(),
        loadTasks(),
        loadToolsCatalog(),
        loadPostizIntegrations(),
      ]);
    }

    init();

    const healthInterval = setInterval(checkSystemHealth, 30000);
    return () => {
      clearInterval(healthInterval);
      if (streamSubRef.current) streamSubRef.current.close();
      if (batchPollTimerRef.current) clearInterval(batchPollTimerRef.current);
    };
  }, []);

  // Sincronización al cambiar el cliente activo (por ID)
  useEffect(() => {
    if (!selectedClient) return;
    const brandId = selectedClient.brand_id || selectedClient.id;
    // Si ya fue cargada por init o por selección manual, no repetir
    if (activeBrandIdRef.current === brandId) return;
    activeBrandIdRef.current = brandId;

    loadBrandChannels(brandId);
    loadIdeas('', 0, brandId);
    loadPublications(brandId);
  }, [selectedClient?.id, selectedClient?.brand_id]);

  const value = {
    activeTab,
    setActiveTab,
    clients,
    selectedClient,
    handleSelectClient,
    brandChannels,
    loadBrandChannels,
    availablePostizIntegrations,
    loadPostizIntegrations,
    linkBrandChannel,
    unlinkBrandChannel,
    ideas,
    selectedIdea,
    ideaLibraryOffset,
    setIdeaLibraryOffset,
    ideaLibraryTotal,
    ideaLibraryQuery,
    setIdeaLibraryQuery,
    isLoadingIdeas,
    loadIdeas,
    selectIdea,
    publications,
    isLoadingPublications,
    loadPublications,
    currentTaskId,
    setCurrentTaskId,
    currentTask,
    currentTrace,
    ideaBatch,
    latestIdeaBatch,
    activeBatchTraceTaskId,
    setActiveBatchTraceTaskId,
    activeStudioWorkflow,
    setActiveStudioWorkflow,
    tasks,
    isLoadingTasks,
    loadTasks,
    health,
    overview,
    toolsCatalog,
    ragStats,
    isExecuting,
    liveStreamStatus,
    toasts,
    showToast,
    copyText,
    exportDossier,
    submitBrief,
    runDemo,
    publishSelectedIdea,
    approvePreparedPublication,
    deliverPreparedPublication,
    sendApprovedPublication,
    loadTaskDetails,
    checkSystemHealth,
    loadClients,
    updateBrand,
    deleteBrand,
    updateIdea,
    deleteIdea,
    updatePublication,
    deletePublication,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
}
