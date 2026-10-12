/**
 * Aplicación principal Multi-Agent Studio
 */
const App = {
  clients: [],
  brandChannels: [],
  availablePostizIntegrations: [],
  selectedClient: null,
  tasks: [],
  ideas: [],
  selectedIdea: null,
  ideaBatch: null,
  latestIdeaBatch: null,
  activeStudioWorkflow: null,
  activeBatchTraceTaskId: null,
  batchResultsSignature: '',
  ideaLibraryOffset: 0,
  ideaLibraryTotal: 0,
  batchPollTimer: null,
  currentTask: null,
  currentTrace: null,
  activeTab: 'studio',
  isExecuting: false,
  streamSubscription: null,

  async init() {
    console.log('Iniciando Multi-Agent Studio...');
    this.bindEvents();
    await this.loadInitialData();
    this.initDefaultBriefs();

    // Actualización periódica de salud y overview
    setInterval(() => this.checkSystemHealth(), 15000);
  },

  bindEvents() {
    // Navegación por pestañas
    document.querySelectorAll('.tab-btn').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const tab = e.currentTarget.dataset.tab;
        this.switchTab(tab);
      });
    });

    // Envío del formulario de brief
    const form = document.getElementById('brief-form');
    if (form) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        this.submitBrief();
      });
    }

    // Botón de demo rápida
    const demoBtn = document.getElementById('btn-run-demo');
    if (demoBtn) {
      demoBtn.addEventListener('click', () => this.runDemo());
    }

    // Filtro de estado en historial
    const historyFilter = document.getElementById('history-status-filter');
    if (historyFilter) {
      historyFilter.addEventListener('change', (e) => {
        this.loadTasks(e.target.value);
      });
    }

    const publishMode = document.getElementById('publish-mode-select');
    if (publishMode) {
      publishMode.addEventListener('change', () => this.updatePublicationControls());
    }

    const channelSelect = document.getElementById('postiz-channel-select');
    if (channelSelect) {
      channelSelect.addEventListener('change', () => this.updatePublicationControls());
    }

    document.getElementById('btn-search-ideas')?.addEventListener('click', () => {
      this.ideaLibraryOffset = 0;
      this.loadIdeas();
    });
    document.getElementById('btn-ideas-prev')?.addEventListener('click', () => {
      this.ideaLibraryOffset = Math.max(0, this.ideaLibraryOffset - 50);
      this.loadIdeas();
    });
    document.getElementById('btn-ideas-next')?.addEventListener('click', () => {
      if (this.ideaLibraryOffset + 50 < this.ideaLibraryTotal) {
        this.ideaLibraryOffset += 50;
        this.loadIdeas();
      }
    });
    document.getElementById('idea-library-search')?.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        this.ideaLibraryOffset = 0;
        this.loadIdeas();
      }
    });
    document.getElementById('idea-library-list')?.addEventListener('click', (event) => {
      const item = event.target.closest('[data-idea-id]');
      if (item) this.selectIdea(Number(item.dataset.ideaId));
    });
    document.getElementById('batch-trace-list')?.addEventListener('click', (event) => {
      const button = event.target.closest('[data-batch-trace-task]');
      if (button) this.openBatchTaskTrace(button.dataset.batchTraceTask);
    });
    document.getElementById('results-content-container')?.addEventListener('click', (event) => {
      const button = event.target.closest('[data-batch-result-idea]');
      if (button) this.openBatchIdeaResult(Number(button.dataset.batchResultIdea));
    });
    document.getElementById('idea-detail')?.addEventListener('click', (event) => {
      if (event.target.closest('[data-copy-dossier]') && this.selectedIdea) {
        this.copyText(encodeURIComponent(this.selectedIdea.content || ''));
      }
    });
    document.getElementById('btn-publish-selected-idea')?.addEventListener('click', () => {
      this.publishSelectedIdea();
    });

    const linkChannelButton = document.getElementById('btn-link-postiz-channel');
    if (linkChannelButton) {
      linkChannelButton.addEventListener('click', () => this.linkSelectedPostizIntegration());
    }
  },

  async loadInitialData() {
    await Promise.all([
      this.loadClients(),
      this.loadTasks(),
      this.checkSystemHealth(),
      this.loadToolsCatalog(),
      this.loadRagStats(),
      this.loadPostizIntegrations(),
    ]);
    await this.loadIdeas();

    // Renderizar pipeline visual por defecto
    PipelineVisualizer.render();
  },

  // ── Gestión de Clientes y Marcas ────────────────────────────
  async loadClients() {
    try {
      this.clients = await API.getClients();
      const select = document.getElementById('client-select');
      if (!select) return;

      select.innerHTML = this.clients.map(c => `
        <option value="${c.id}">${c.nombre} (${c.producto_servicio ? c.producto_servicio.slice(0, 35) + '...' : c.pais})</option>
      `).join('');

      if (this.clients.length > 0) {
        this.onClientChange(this.clients[0].id);
        this.loadBrandChannels(this.clients[0].brand_id || this.clients[0].id);
      }

      select.addEventListener('change', (e) => {
        const clientId = parseInt(e.target.value, 10);
        this.selectedIdea = null;
        this.ideaLibraryOffset = 0;
        this.onClientChange(clientId);
        this.loadBrandChannels(this.selectedClient.brand_id || clientId);
        this.loadIdeas();
      });
    } catch (err) {
      this.showToast('Error cargando clientes: ' + err.message, 'error');
    }
  },

  onClientChange(clientId) {
    this.selectedClient = this.clients.find(c => c.id === clientId) || this.clients[0];
    this.selectedIdea = null;
    const ideaDetail = document.getElementById('idea-detail');
    if (ideaDetail) ideaDetail.textContent = 'Selecciona una idea para revisar su dossier completo.';
    const publishButton = document.getElementById('btn-publish-selected-idea');
    if (publishButton) publishButton.disabled = true;
    const preview = document.getElementById('client-preview-card');
    if (!preview || !this.selectedClient) return;

    preview.innerHTML = `
      <div class="glass-card p-4 rounded-xl border border-slate-700/70 text-xs space-y-2">
        <div class="flex items-center justify-between pb-2 border-b border-slate-700/60">
          <span class="font-bold text-slate-100 text-sm flex items-center gap-2">
            <i class="fa-solid fa-building text-indigo-400"></i> ${this.selectedClient.nombre}
          </span>
          <span class="text-[11px] px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
            ${this.selectedClient.pais || 'Colombia'}
          </span>
        </div>
        <div>
          <span class="text-slate-400 font-semibold block">Producto / Servicio:</span>
          <p class="text-slate-300 line-clamp-2">${this.selectedClient.producto_servicio || 'N/A'}</p>
        </div>
        <div>
          <span class="text-slate-400 font-semibold block">Restricciones de Tono:</span>
          <p class="text-slate-300 line-clamp-2">${this.selectedClient.restricciones_tono || 'N/A'}</p>
        </div>
        <div>
          <span class="text-slate-400 font-semibold block">Audiencia Objetivo:</span>
          <p class="text-slate-300 line-clamp-1">${this.selectedClient.audiencia_objetivo || 'N/A'}</p>
        </div>
      </div>
    `;
  },

  async loadBrandChannels(brandId) {
    const select = document.getElementById('postiz-channel-select');
    const status = document.getElementById('postiz-channel-status');
    if (!select || !brandId) return;

    select.replaceChildren();
    this.brandChannels = [];
    if (status) status.textContent = 'Cargando canales de la marca...';

    try {
      this.brandChannels = await API.getBrandChannels(brandId);
      if (this.brandChannels.length === 0) {
        const option = document.createElement('option');
        option.textContent = 'No hay canales activos asociados';
        option.disabled = true;
        select.appendChild(option);
        if (status) status.textContent = 'Sin canales asociados, vincula uno para publicar desde la biblioteca.';
      } else {
        this.brandChannels.forEach((channel) => {
          const option = document.createElement('option');
          option.value = channel.external_id;
          const setupState = channel.configured ? '' : ' · falta configuración Postiz';
          option.textContent = `${channel.display_name || channel.external_id} (${channel.provider}${setupState})`;
          select.appendChild(option);
        });
        if (status) status.textContent = 'Selecciona los canales destino al publicar una idea.';
      }
      this.updatePublicationControls();
    } catch (err) {
      if (status) status.textContent = 'No se pudieron cargar canales. El copy puede generarse sin publicación externa.';
      console.warn('Error cargando canales Postiz:', err);
    }
  },

  async loadPostizIntegrations() {
    const select = document.getElementById('postiz-integration-select');
    const button = document.getElementById('btn-link-postiz-channel');
    const status = document.getElementById('postiz-integration-status');
    if (!select) return;

    select.replaceChildren();
    try {
      this.availablePostizIntegrations = await API.getPostizIntegrations();
      if (this.availablePostizIntegrations.length === 0) {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'No hay integraciones Postiz disponibles';
        select.appendChild(option);
        if (status) status.textContent = 'Configura POSTIZ_API_KEY y conecta canales en Postiz para vincularlos.';
        if (button) button.disabled = true;
        return;
      }

      this.availablePostizIntegrations.forEach((integration) => {
        const option = document.createElement('option');
        option.value = integration.external_id;
        option.textContent = `${integration.display_name} (${integration.provider})`;
        select.appendChild(option);
      });
      if (status) status.textContent = 'Vincula una integración disponible a la marca seleccionada.';
      if (button) button.disabled = false;
    } catch (err) {
      const option = document.createElement('option');
      option.value = '';
      option.textContent = 'Catálogo Postiz no disponible';
      select.appendChild(option);
      if (status) status.textContent = 'No se pudo consultar Postiz. Revisa POSTIZ_API_KEY y el servicio tool-postiz.';
      if (button) button.disabled = true;
      console.warn('Error cargando integraciones Postiz:', err);
    }
  },

  async linkSelectedPostizIntegration() {
    const brandId = this.selectedClient?.brand_id;
    const integrationId = document.getElementById('postiz-integration-select')?.value;
    const status = document.getElementById('postiz-integration-status');
    const button = document.getElementById('btn-link-postiz-channel');
    if (!brandId || !integrationId) {
      this.showToast('Selecciona una integración Postiz disponible.', 'warning');
      return;
    }

    if (button) button.disabled = true;
    if (status) status.textContent = 'Vinculando canal a la marca...';
    try {
      await API.linkBrandChannel(brandId, integrationId);
      await this.loadBrandChannels(brandId);
      if (status) status.textContent = 'Canal vinculado. Ya puedes seleccionarlo al publicar una idea.';
      this.showToast('Canal Postiz vinculado a la marca.', 'success');
    } catch (err) {
      if (status) status.textContent = err.message;
      this.showToast('No se pudo vincular el canal: ' + err.message, 'error');
    } finally {
      if (button) button.disabled = this.availablePostizIntegrations.length === 0;
    }
  },

  updatePublicationControls() {
    const mode = document.getElementById('publish-mode-select')?.value || 'draft';
    const publishAt = document.getElementById('publish-at-input');
    const channelSelect = document.getElementById('postiz-channel-select');
    const selectedCount = channelSelect?.selectedOptions.length || 0;
    const selectedIds = Array.from(channelSelect?.selectedOptions || []).map((option) => option.value);
    const incompleteCount = this.brandChannels.filter(
      (channel) => selectedIds.includes(channel.external_id) && !channel.configured
    ).length;
    const status = document.getElementById('postiz-channel-status');

    if (publishAt) {
      publishAt.disabled = mode !== 'schedule';
      publishAt.required = mode === 'schedule';
    }
    if (status && this.brandChannels.length > 0) {
      if (!selectedCount) {
        status.textContent = 'Selecciona los canales destino para preparar variantes al publicar.';
      } else if (incompleteCount) {
        status.textContent = `${selectedCount} canal(es): se generarán variantes; ${incompleteCount} sin configuración Postiz se omitirán.`;
      } else {
        status.textContent = `${selectedCount} canal(es): se generará una variante por plataforma.`;
      }
    }
    const publishButton = document.getElementById('btn-publish-selected-idea');
    if (publishButton) publishButton.disabled = !this.selectedIdea || !selectedCount;
  },

  // ── Plantillas de Brief ──────────────────────────────────────
  initDefaultBriefs() {
    const templates = [
      {
        title: '🌱 EcoBrand - Protector Solar',
        clientId: 1,
        format: 'reel',
        content: 'Crear un Reel para presentar una crema solar natural y biodegradable durante el verano colombiano, destacando cero impacto en arrecifes.',
      },
      {
        title: '💳 TechStart - Pagos QR',
        clientId: 2,
        format: 'reel',
        content: 'Lanzar un Reel dinámico explicando cómo pequeños comerciantes y cafeterías pueden recibir pagos con código QR al instante y sin comisiones ocultas.',
      },
      {
        title: '💪 FitLife - Reto 30 Días',
        clientId: 3,
        format: 'post',
        content: 'Diseñar un carrusel educativo para invitar a la comunidad al Reto 30 Días de Hábitos Saludables con suplementos naturales basados en evidencia.',
      },
    ];

    const container = document.getElementById('brief-templates-container');
    if (!container) return;

    container.innerHTML = templates.map((t, idx) => `
      <button type="button" class="px-3 py-1.5 rounded-lg text-xs bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700 transition flex items-center gap-2 text-left" onclick="App.applyTemplate(${idx})">
        ${t.title}
      </button>
    `).join('');

    this.templates = templates;
  },

  applyTemplate(idx) {
    const t = this.templates[idx];
    if (!t) return;

    const select = document.getElementById('client-select');
    if (select) {
      select.value = t.clientId;
      this.onClientChange(t.clientId);
      this.loadBrandChannels(this.selectedClient.brand_id || t.clientId);
      this.loadIdeas();
    }

    const contentInput = document.getElementById('brief-content');
    if (contentInput) contentInput.value = t.content;

    const formatSelect = document.getElementById('format-select');
    if (formatSelect) formatSelect.value = t.format;

    this.showToast(`Plantilla "${t.title}" cargada`, 'info');
  },

  // ── Ejecución de Tareas (Multi-Agente) ────────────────────────
  async submitBrief() {
    if (this.isExecuting) return;

    const contentInput = document.getElementById('brief-content');
    const content = contentInput ? contentInput.value.trim() : '';
    const clientId = parseInt(document.getElementById('client-select').value, 10);
    const contentFormat = document.getElementById('format-select').value;
    const count = Number(document.getElementById('idea-count')?.value || 1);
    const briefs = (document.getElementById('idea-briefs')?.value || '')
      .split('\n').map((brief) => brief.trim()).filter(Boolean);
    if (briefs.length > count) {
      this.showToast('Usa como máximo un brief individual por idea del lote.', 'warning');
      return;
    }
    const payload = {
      client_id: clientId,
      brand_id: this.selectedClient?.brand_id || clientId,
      content,
      briefs,
      topics: (document.getElementById('idea-topics')?.value || '')
        .split(',').map((topic) => topic.trim()).filter(Boolean),
      count,
      content_format: contentFormat,
    };

    this.setExecutionState(true);
    this.showToast('Generando ideas para la biblioteca...', 'info');

    try {
      const response = await API.generateIdeas(payload);
      this.ideaBatch = { id: response.generation_batch_id, brandId: payload.brand_id };
      this.latestIdeaBatch = null;
      this.activeStudioWorkflow = 'batch';
      this.activeBatchTraceTaskId = null;
      this.batchResultsSignature = '';
      this.switchTab('traceability');
      this.setExecutionState(false);
      this.showToast(`Lote iniciado: ${payload.count} idea(s).`, 'success');
      this.pollIdeaBatch(this.ideaBatch.id, payload.brand_id);
    } catch (err) {
      this.setExecutionState(false);
      this.showToast('Error iniciando lote: ' + err.message, 'error');
    }
  },

  async pollIdeaBatch(batchId, brandId) {
    if (this.batchPollTimer) clearInterval(this.batchPollTimer);
    let terminal = false;
    const poll = async () => {
      try {
        const batch = await API.getIdeaBatch(batchId, brandId);
        this.latestIdeaBatch = batch;
        if (this.activeStudioWorkflow === 'batch') {
          this.renderBatchTrace(batch);
          this.renderBatchResults(batch);
        }
        await this.loadIdeas();
        const taskIds = (batch.ideas || []).map((idea) => idea.task_id).filter(Boolean);
        if (!this.activeBatchTraceTaskId || !taskIds.includes(this.activeBatchTraceTaskId)) {
          this.activeBatchTraceTaskId = taskIds[0] || null;
        }
        if (this.activeStudioWorkflow === 'batch' && this.activeTab === 'traceability' && this.activeBatchTraceTaskId) {
          this.currentTaskId = this.activeBatchTraceTaskId;
          await this.loadTaskDetails(this.activeBatchTraceTaskId, { renderResult: false });
        }
        if (['completed', 'partial', 'failed'].includes(batch.status)) {
          clearInterval(this.batchPollTimer);
          this.batchPollTimer = null;
          terminal = true;
        }
      } catch (error) {
        console.warn('No se pudo consultar el lote:', error);
      }
    };
    await poll();
    if (!terminal) this.batchPollTimer = setInterval(poll, 3000);
  },

  renderBatchTrace(batch) {
    const panel = document.getElementById('batch-trace-panel');
    const list = document.getElementById('batch-trace-list');
    const summary = document.getElementById('batch-trace-summary');
    if (!panel || !list || !batch) return;
    panel.classList.remove('hidden');
    if (summary) {
      summary.textContent = `${batch.completed || 0}/${batch.total || 0} completadas · ${batch.failed || 0} fallidas · ${batch.status}`;
    }
    const librarySummary = document.getElementById('idea-batch-status');
    if (librarySummary) {
      librarySummary.textContent = `Lote ${batch.completed || 0}/${batch.total || 0} · ${batch.status}`;
    }
    const ideas = batch.ideas || [];
    if (!ideas.length) {
      list.innerHTML = '<p class="text-xs text-slate-500">Preparando las tareas del lote...</p>';
      return;
    }
    list.innerHTML = ideas.map((idea) => {
      const index = Number(idea.generation_index || 0) + 1;
      const isActive = idea.task_id === this.activeBatchTraceTaskId;
      const statusLabel = idea.status === 'completed' ? 'Completada'
        : idea.status === 'failed' ? 'Fallida'
          : idea.status === 'running' ? 'Ideación en curso' : 'Pendiente';
      const statusClass = idea.status === 'completed' ? 'text-emerald-300'
        : idea.status === 'failed' ? 'text-rose-300'
          : idea.status === 'running' ? 'text-cyan-300' : 'text-slate-400';
      return `
        <article class="border ${isActive ? 'border-cyan-700 bg-cyan-950/20' : 'border-slate-800 bg-slate-950/30'} p-3 min-w-0">
          <div class="flex items-center justify-between gap-2">
            <span class="text-xs font-semibold text-slate-200">Idea ${index}</span>
            <span class="text-[11px] ${statusClass}">${statusLabel}</span>
          </div>
          <p class="mt-2 truncate text-xs text-slate-300">${this.escapeHtml(idea.title || (idea.status === 'running' ? 'Generando dossier...' : 'Esperando turno...'))}</p>
          ${idea.error ? `<p class="mt-1 line-clamp-2 text-[11px] text-rose-300">${this.escapeHtml(idea.error)}</p>` : ''}
          <div class="mt-3 flex items-center justify-between gap-2">
            <span class="font-mono text-[10px] text-slate-500">${idea.task_id ? idea.task_id.slice(0, 8) : 'sin tarea'}</span>
            ${idea.task_id ? `<button type="button" data-batch-trace-task="${this.escapeHtml(idea.task_id)}" class="text-[11px] text-cyan-300 hover:text-cyan-200">Ver traza</button>` : ''}
          </div>
        </article>
      `;
    }).join('');
  },

  renderBatchResults(batch) {
    const container = document.getElementById('results-content-container');
    if (!container || !batch) return;
    const ideas = batch.ideas || [];
    const signature = ideas.map((idea) => [idea.task_id, idea.status, idea.idea_id, idea.title, idea.error].join(':')).join('|');
    if (signature === this.batchResultsSignature) return;
    this.batchResultsSignature = signature;
    container.innerHTML = `
      <div class="space-y-4">
        <div class="flex flex-wrap items-end justify-between gap-3 border-b border-slate-800 pb-4">
          <div>
            <h2 class="text-lg font-bold text-slate-100">Resultados del lote</h2>
            <p class="mt-1 text-xs text-slate-400">${batch.completed || 0} de ${batch.total || 0} dossiers listos. Cada idea conserva su propio resultado.</p>
          </div>
          <span class="font-mono text-[11px] text-slate-500">${this.escapeHtml(batch.generation_batch_id || '')}</span>
        </div>
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
          ${ideas.map((idea) => {
            const dossier = idea.dossier || {};
            const index = Number(idea.generation_index || 0) + 1;
            const completed = idea.status === 'completed' && Object.keys(dossier).length > 0;
            return `
              <article class="border border-slate-800 bg-slate-950/30 p-4 min-w-0">
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0">
                    <p class="text-[11px] uppercase text-amber-300">Idea ${index}${idea.idea_id ? ` · #${Number(idea.idea_id)}` : ''}</p>
                    <h3 class="mt-1 text-sm font-semibold text-slate-100">${this.escapeHtml(dossier.title || idea.title || (idea.status === 'failed' ? 'Generación fallida' : 'Generando...'))}</h3>
                  </div>
                  <span class="shrink-0 text-[11px] ${completed ? 'text-emerald-300' : idea.status === 'failed' ? 'text-rose-300' : 'text-cyan-300'}">${completed ? 'Lista' : idea.status === 'failed' ? 'Fallida' : 'En proceso'}</span>
                </div>
                ${completed ? `
                  <p class="mt-3 text-xs leading-relaxed text-slate-300">${this.escapeHtml(dossier.concept || '')}</p>
                  ${dossier.objective ? `<p class="mt-2 text-[11px] text-slate-400"><span class="text-slate-300">Objetivo:</span> ${this.escapeHtml(dossier.objective)}</p>` : ''}
                  <details class="mt-3 border-t border-slate-800 pt-2">
                    <summary class="cursor-pointer text-xs text-cyan-300">Dossier completo</summary>
                    <pre class="mt-2 max-h-80 overflow-auto whitespace-pre-wrap text-[11px] text-slate-300">${this.escapeHtml(JSON.stringify(dossier, null, 2))}</pre>
                  </details>
                  <button type="button" data-batch-result-idea="${Number(idea.idea_id)}" class="mt-3 text-xs text-amber-300 hover:text-amber-200">Abrir en biblioteca</button>
                ` : idea.status === 'failed'
                  ? `<p class="mt-3 text-xs text-rose-300">${this.escapeHtml(idea.error || 'No se pudo generar esta idea.')}</p>`
                  : `<p class="mt-3 text-xs text-slate-500">El dossier aparecerá aquí cuando termine esta tarea.</p>`}
              </article>
            `;
          }).join('')}
        </div>
      </div>
    `;
  },

  async openBatchTaskTrace(taskId) {
    this.activeBatchTraceTaskId = taskId;
    this.currentTaskId = taskId;
    this.renderBatchTrace(this.latestIdeaBatch);
    this.switchTab('traceability');
  },

  async openBatchIdeaResult(ideaId) {
    if (!ideaId || !this.selectedClient) return;
    await this.selectIdea(ideaId);
    this.switchTab('library');
  },

  async loadIdeas() {
    const list = document.getElementById('idea-library-list');
    if (!list || !this.selectedClient) return;
    const brandId = this.selectedClient.brand_id || this.selectedClient.id;
    const query = document.getElementById('idea-library-search')?.value.trim() || '';
    try {
      const result = await API.getIdeas(brandId, {
        query,
        limit: 50,
        offset: this.ideaLibraryOffset,
      });
      this.ideas = result.items || [];
      this.ideaLibraryTotal = result.total || 0;
      const count = document.getElementById('idea-library-count');
      if (count) count.textContent = `${this.ideaLibraryTotal} ideas guardadas`;
      const previous = document.getElementById('btn-ideas-prev');
      const next = document.getElementById('btn-ideas-next');
      if (previous) previous.disabled = this.ideaLibraryOffset === 0;
      if (next) next.disabled = this.ideaLibraryOffset + 50 >= this.ideaLibraryTotal;
      if (!this.ideas.length) {
        list.innerHTML = '<p class="py-8 text-center text-xs text-slate-500">No hay ideas para esta búsqueda.</p>';
        return;
      }
      list.innerHTML = this.ideas.map((idea) => `
        <button type="button" data-idea-id="${Number(idea.id)}" class="w-full text-left py-4 px-2 hover:bg-slate-900/70 transition ${this.selectedIdea?.id === idea.id ? 'border-l-2 border-amber-400 pl-3' : ''}">
          <span class="block text-sm font-semibold text-slate-200">${this.escapeHtml(idea.title || `Idea ${idea.id}`)}</span>
          <span class="mt-1 block text-[11px] text-slate-500">#${idea.id} · ${idea.created_at ? new Date(idea.created_at).toLocaleDateString() : 'guardada'}</span>
          <span class="mt-2 block line-clamp-2 text-xs leading-relaxed text-slate-400">${this.escapeHtml(idea.dossier?.concept || idea.content || '')}</span>
        </button>
      `).join('');
      if (this.selectedIdea && this.ideas.some((idea) => idea.id === this.selectedIdea.id)) {
        this.renderSelectedIdea();
      }
    } catch (error) {
      list.innerHTML = `<p class="py-8 text-center text-xs text-rose-300">${this.escapeHtml(error.message)}</p>`;
    }
  },

  async selectIdea(ideaId) {
    try {
      const brandId = this.selectedClient.brand_id || this.selectedClient.id;
      this.selectedIdea = await API.getIdea(ideaId, brandId);
      this.renderSelectedIdea();
      this.updatePublicationControls();
    } catch (error) {
      this.showToast('No se pudo abrir el dossier: ' + error.message, 'error');
    }
  },

  renderSelectedIdea() {
    const container = document.getElementById('idea-detail');
    const idea = this.selectedIdea;
    if (!container || !idea) return;
    const dossier = idea.dossier || {};
    const summaryFields = [
      ['Concepto', dossier.concept],
      ['Objetivo', dossier.objective],
      ['Audiencia', dossier.audience],
      ['Mensaje clave', dossier.key_message],
      ['CTA', dossier.cta],
      ['Por qué funciona', dossier.why_it_works],
    ].filter(([, value]) => value);
    container.innerHTML = `
      <div class="flex flex-wrap items-start justify-between gap-3 border-b border-slate-800 pb-4">
        <div><p class="text-[11px] uppercase text-amber-300">Idea #${Number(idea.id)}</p>
        <h3 class="mt-1 text-lg font-bold text-white">${this.escapeHtml(dossier.title || idea.title || 'Idea guardada')}</h3></div>
        <button type="button" data-copy-dossier class="text-xs text-slate-400 hover:text-white" title="Copiar dossier"><i class="fa-regular fa-copy"></i></button>
      </div>
      <div class="mt-4 grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
        ${summaryFields.map(([label, value]) => `<div><h4 class="text-[11px] uppercase text-slate-500">${label}</h4><p class="mt-1 whitespace-pre-wrap text-xs leading-relaxed text-slate-200">${this.escapeHtml(value)}</p></div>`).join('')}
      </div>
      <details class="mt-5 border-t border-slate-800 pt-3">
        <summary class="cursor-pointer text-xs font-semibold text-cyan-300">Dossier completo</summary>
        <pre class="mt-3 max-h-[30rem] overflow-auto whitespace-pre-wrap text-[11px] leading-relaxed text-slate-300">${this.escapeHtml(JSON.stringify(dossier, null, 2))}</pre>
      </details>
    `;
    const publishButton = document.getElementById('btn-publish-selected-idea');
    if (publishButton) this.updatePublicationControls();
  },

  async publishSelectedIdea() {
    if (!this.selectedIdea) return;
    const mode = document.getElementById('publish-mode-select')?.value || 'draft';
    const integrations = Array.from(
      document.getElementById('postiz-channel-select')?.selectedOptions || []
    ).map((option) => option.value).filter(Boolean);
    const publishAt = document.getElementById('publish-at-input')?.value || '';
    const incomplete = this.brandChannels.filter(
      (channel) => integrations.includes(channel.external_id) && !channel.configured
    );
    if (!integrations.length) {
      this.showToast('Selecciona al menos un canal vinculado.', 'warning');
      return;
    }
    if (incomplete.length) {
      this.showToast('Configura los canales seleccionados en Postiz antes de publicar.', 'warning');
      return;
    }
    if (mode === 'schedule' && !publishAt) {
      this.showToast('Indica la fecha y hora para programar.', 'warning');
      return;
    }
    if (mode === 'now' && !window.confirm('¿Confirmas publicar ahora en los canales seleccionados?')) return;

    const button = document.getElementById('btn-publish-selected-idea');
    if (button) button.disabled = true;
    try {
      const result = await API.publishIdea(this.selectedIdea.id, {
        brand_id: this.selectedClient.brand_id || this.selectedClient.id,
        publish_mode: mode,
        publish_at: publishAt ? new Date(publishAt).toISOString() : null,
        integration_ids: integrations,
        settings: {},
      });
      this.currentTaskId = result.task_id;
      this.activeStudioWorkflow = 'task';
      this.switchTab('traceability');
      this.startTaskStream(result.task_id);
      this.showToast('Publicación aprobada y enviada al agente.', 'success');
    } catch (error) {
      this.showToast('No se pudo iniciar la publicación: ' + error.message, 'error');
      if (button) button.disabled = false;
    }
  },

  escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (character) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[character]));
  },

  async runDemo() {
    if (this.isExecuting) return;
    this.setExecutionState(true);
    this.showToast('Lanzando demo rápida...', 'info');

    try {
      const resp = await API.createDemo({
        brand_id: 1,
        content: 'Crear un Reel para presentar una crema solar natural durante el verano colombiano',
        content_format: 'reel',
        wait: false,
      });

      const taskId = resp.task_id;
      if (taskId) {
        this.activeStudioWorkflow = 'task';
        this.currentTaskId = taskId;
        this.switchTab('traceability');
        this.startTaskStream(taskId);
        this.loadTasks();
      }
    } catch (err) {
      this.setExecutionState(false);
      this.showToast('Error en demo: ' + err.message, 'error');
    }
  },

  startTaskStream(taskId) {
    this.activeStudioWorkflow = 'task';
    const batchTasks = this.latestIdeaBatch?.ideas || [];
    if (!batchTasks.some((idea) => idea.task_id === taskId)) {
      document.getElementById('batch-trace-panel')?.classList.add('hidden');
    }
    if (this.streamSubscription) {
      this.streamSubscription.close();
    }

    const statusBar = document.getElementById('live-status-bar');
    if (statusBar) statusBar.classList.remove('hidden');

    this.streamSubscription = API.streamTask(
      taskId,
      (data) => {
        // En cada tick de progreso
        const trace = data.trace;
        if (trace) {
          this.currentTrace = trace;
          this.updateTraceView(trace);
        }

        const statusLabel = document.getElementById('live-status-label');
        if (statusLabel) {
          statusLabel.textContent = `Tarea ${taskId.slice(0, 8)}... — Estado: ${data.status.toUpperCase()}`;
        }
      },
      (finalData) => {
        // Cuando termina la tarea
        this.setExecutionState(false);
        if (statusBar) statusBar.classList.add('hidden');

        if (finalData.trace) {
          this.currentTrace = finalData.trace;
          this.currentTask = finalData.trace.raw_task;
          this.updateTraceView(finalData.trace);
          this.renderResults(this.currentTask);
        }

        this.loadTasks();
        this.showToast('¡Pipeline multi-agente completado!', 'success');
      },
      (err) => {
        console.warn('Finalizó stream:', err);
        this.setExecutionState(false);
        if (statusBar) statusBar.classList.add('hidden');
        this.loadTaskDetails(taskId);
      }
    );
  },

  setExecutionState(isExecuting) {
    this.isExecuting = isExecuting;
    const btn = document.getElementById('btn-submit-brief');
    const demoBtn = document.getElementById('btn-run-demo');
    const spinner = document.getElementById('exec-spinner');

    if (btn) {
      btn.disabled = isExecuting;
      btn.classList.toggle('opacity-50', isExecuting);
    }
    if (demoBtn) {
      demoBtn.disabled = isExecuting;
      demoBtn.classList.toggle('opacity-50', isExecuting);
    }
    if (spinner) {
      spinner.classList.toggle('hidden', !isExecuting);
    }
  },

  // ── Carga y Visualización de Trazabilidad ───────────────────
  async loadTaskDetails(taskId, { renderResult = true } = {}) {
    try {
      const trace = await API.getTaskTrace(taskId);
      this.currentTrace = trace;
      this.currentTask = trace.raw_task;

      this.updateTraceView(trace);
      if (renderResult) this.renderResults(this.currentTask);
    } catch (err) {
      this.showToast('Error cargando trazabilidad de la tarea: ' + err.message, 'error');
    }
  },

  updateTraceView(trace) {
    // 1. Pipeline visual con nodos
    PipelineVisualizer.render(trace.pipeline_stages);

    // 2. Timeline cronológico y herramientas
    TraceViewer.renderTimeline(trace);

    // 3. Historial de chat PostgreSQL
    TraceViewer.renderChatHistory(trace.chat_history);

    // 4. Raw JSON
    TraceViewer.renderRawJson(trace.raw_task);

    // Info header de tarea
    const taskIdDisplay = document.getElementById('current-task-id-display');
    if (taskIdDisplay) {
      taskIdDisplay.textContent = trace.task_id;
    }

    const durationDisplay = document.getElementById('current-task-duration-display');
    if (durationDisplay) {
      durationDisplay.textContent = trace.total_duration_seconds ? `${trace.total_duration_seconds}s` : 'En progreso...';
    }

    const statusBadge = document.getElementById('current-task-status-badge');
    if (statusBadge) {
      statusBadge.textContent = trace.status.toUpperCase();
      statusBadge.className = `px-2.5 py-0.5 rounded-full text-xs font-semibold ${
        trace.status === 'completed' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' :
        trace.status === 'running' ? 'bg-cyan-950 text-cyan-300 border border-cyan-800' :
        'bg-rose-950 text-rose-300 border border-rose-800'
      }`;
    }
  },

  // ── Renderizado de Resultados y Dossier ──────────────────────
  renderResults(task) {
    const container = document.getElementById('results-content-container');
    if (!container || !task) return;

    const result = task.result || {};
    const idea = result.idea || '';
    const publication = result.publication || '';
    const publicationVariants = (result.publication_variants || [])
      .filter((variant) => variant.platform && variant.platform !== 'platform-neutral');
    const preprod = result.preproduction || {};
    const brief = task.brief || {};

    const hasResults = idea || publication;
    if (!hasResults) {
      container.innerHTML = `
        <div class="glass-card p-10 rounded-2xl text-center text-slate-400">
          <i class="fa-solid fa-hourglass-half text-3xl mb-3 text-slate-500"></i>
          <p>Esta tarea aún no tiene resultados o está en ejecución.</p>
        </div>
      `;
      return;
    }

    let html = `
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <!-- Columna Izquierda: Idea y Dossier (8 cols) -->
        <div class="lg:col-span-7 space-y-6">
          <!-- Tarjeta de Idea -->
          <div class="glass-card p-6 rounded-2xl border border-slate-700/70">
            <div class="flex items-center justify-between pb-3 border-b border-slate-700/60 mb-4">
              <div class="flex items-center gap-2">
                <span class="w-8 h-8 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center">
                  <i class="fa-solid fa-lightbulb"></i>
                </span>
                <h3 class="text-base font-bold text-slate-100">Idea de Campaña (Agente de Ideación)</h3>
              </div>
              <span class="text-xs font-mono text-slate-400">ID: ${result.idea_id || 'N/A'}</span>
            </div>

            <div class="prose prose-invert max-w-none text-xs text-slate-200 leading-relaxed whitespace-pre-line mb-4 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
              ${idea}
            </div>

            <div class="flex items-center justify-end gap-2">
              <button class="px-3 py-1.5 rounded-lg text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition" onclick="App.copyText('${encodeURIComponent(idea)}')">
                <i class="fa-regular fa-copy mr-1"></i> Copiar Idea
              </button>
            </div>
          </div>

          <!-- Dossier Audiovisual (si existe preproduction) -->
          ${preprod && Object.keys(preprod).length > 0 ? this.renderPreproductionDossier(preprod) : ''}
        </div>

        <!-- Columna Derecha: Publicación y Mockup Social (5 cols) -->
        <div class="lg:col-span-5 space-y-6">
          <!-- Mockup de Red Social -->
          <div class="glass-card p-6 rounded-2xl border border-slate-700/70">
            <div class="flex items-center justify-between pb-3 border-b border-slate-700/60 mb-4">
              <div class="flex items-center gap-2">
                <span class="w-8 h-8 rounded-lg bg-sky-500/20 text-sky-400 flex items-center justify-center">
                  <i class="fa-solid fa-share-nodes"></i>
                </span>
                <h3 class="text-base font-bold text-slate-100">Publicación Generada</h3>
              </div>
              <span class="text-xs font-mono text-slate-400">ID: ${result.publication_id || 'N/A'}</span>
            </div>

            ${publicationVariants.length ? `
              <div class="mb-4 space-y-3">
                <h4 class="text-xs font-bold uppercase tracking-wider text-slate-300">Versiones por plataforma</h4>
                ${publicationVariants.map((variant) => `
                  <div class="rounded-lg border border-slate-700 bg-slate-900/70 p-3">
                    <div class="mb-2 flex items-center justify-between gap-3">
                      <span class="text-xs font-semibold text-cyan-300">${variant.platform}</span>
                      <span class="text-[10px] text-slate-500">${(variant.integration_ids || []).length} canal(es) · ${variant.content.length} caracteres</span>
                    </div>
                    <p class="whitespace-pre-wrap text-xs leading-relaxed text-slate-200">${variant.content}</p>
                    <button class="mt-2 rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1 text-[11px] text-slate-300 hover:bg-slate-700" onclick="App.copyText('${encodeURIComponent(variant.content)}')">
                      <i class="fa-regular fa-copy mr-1"></i> Copiar ${variant.platform}
                    </button>
                  </div>
                `).join('')}
              </div>
            ` : ''}

            ${publicationVariants.length === 0 ? `
            <!-- Mockup neutral cuando no hay destinos por plataforma -->
            <div class="mockup-instagram mx-auto p-4 mb-4">
              <div class="flex items-center justify-between pb-3 border-b border-neutral-800 mb-3">
                <div class="flex items-center gap-2.5">
                  <div class="w-8 h-8 rounded-full bg-gradient-to-tr from-amber-500 to-rose-500 p-0.5">
                    <div class="w-full h-full rounded-full bg-neutral-900 flex items-center justify-center text-[11px] font-bold text-white">
                      ${this.selectedClient ? this.selectedClient.nombre.slice(0, 2).toUpperCase() : 'AG'}
                    </div>
                  </div>
                  <div>
                    <div class="text-xs font-bold text-white">${this.selectedClient ? this.selectedClient.nombre : 'Brand'}</div>
                    <div class="text-[10px] text-neutral-400">Publicación patrocinada</div>
                  </div>
                </div>
                <i class="fa-solid fa-ellipsis text-neutral-400 text-xs"></i>
              </div>

              <!-- Media Placeholder -->
              <div class="aspect-square bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 rounded-lg flex flex-col items-center justify-center p-6 text-center border border-neutral-800 mb-3">
                <i class="fa-solid ${brief.content_format === 'reel' ? 'fa-video text-rose-400' : 'fa-image text-indigo-400'} text-4xl mb-3 opacity-80"></i>
                <div class="text-xs font-semibold text-slate-200">${preprod.title || 'Campaña Oficial'}</div>
                <div class="text-[11px] text-slate-400 mt-1">${preprod.format || (brief.content_format === 'reel' ? 'Video Vertical 9:16' : 'Post / Carrusel')}</div>
              </div>

              <!-- Action Icons -->
              <div class="flex items-center justify-between text-neutral-300 mb-3 text-sm">
                <div class="flex items-center gap-3">
                  <i class="fa-regular fa-heart hover:text-rose-500 cursor-pointer"></i>
                  <i class="fa-regular fa-comment hover:text-indigo-400 cursor-pointer"></i>
                  <i class="fa-regular fa-paper-plane hover:text-sky-400 cursor-pointer"></i>
                </div>
                <i class="fa-regular fa-bookmark hover:text-amber-400 cursor-pointer"></i>
              </div>

              <!-- Caption -->
              <div class="text-xs text-neutral-200 leading-relaxed whitespace-pre-wrap font-sans">
                <span class="font-bold mr-1.5 text-white">${this.selectedClient ? this.selectedClient.nombre : 'Brand'}</span>
                ${publication}
              </div>
            </div>
            ` : ''}

            <!-- Stats de publicación -->
            <div class="flex items-center justify-between text-xs text-slate-400 py-2 border-t border-slate-700/60 mb-4">
              <span>Longitud${publicationVariants.length ? ` (${publicationVariants[0].platform})` : ''}: <strong class="text-slate-200">${publication.length}</strong> caracteres</span>
              <span class="px-2 py-0.5 rounded ${publicationVariants.length ? 'bg-cyan-950 text-cyan-300' : publication.length <= 280 ? 'bg-emerald-950 text-emerald-300' : 'bg-amber-950 text-amber-300'}">
                ${publicationVariants.length ? `Variante ${publicationVariants[0].platform}` : publication.length <= 280 ? '≤ 280 (Twitter/X OK)' : 'Copy base largo'}
              </span>
            </div>

            <div class="flex items-center gap-2">
              <button class="flex-1 py-2 rounded-xl text-xs bg-indigo-600 hover:bg-indigo-500 text-white font-medium transition" onclick="App.copyText('${encodeURIComponent(publication)}')">
                <i class="fa-regular fa-copy mr-1"></i> Copiar Publicación
              </button>
              <button class="px-3 py-2 rounded-xl text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition" onclick="App.exportDossier('markdown')">
                <i class="fa-solid fa-file-arrow-down mr-1"></i> MD
              </button>
              <button class="px-3 py-2 rounded-xl text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition" onclick="App.exportDossier('json')">
                <i class="fa-solid fa-code mr-1"></i> JSON
              </button>
            </div>
          </div>
        </div>
      </div>
    `;

    container.innerHTML = html;
  },

  renderPreproductionDossier(preprod) {
    const scripts = preprod.script || [];
    const cameras = preprod.camera || [];

    return `
      <div class="glass-card p-6 rounded-2xl border border-slate-700/70 space-y-6">
        <div class="flex items-center justify-between pb-3 border-b border-slate-700/60">
          <div class="flex items-center gap-2">
            <span class="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
              <i class="fa-solid fa-clapperboard"></i>
            </span>
            <h3 class="text-base font-bold text-slate-100">Dossier Técnico de Preproducción</h3>
          </div>
          <span class="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono">
            ${preprod.format || 'Formato Audiovisual'} (${preprod.duration_seconds ? preprod.duration_seconds + 's' : '30s'})
          </span>
        </div>

        <!-- Ficha técnica rápida -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          <div class="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
            <span class="text-slate-400 font-semibold block mb-1">Concepto Central:</span>
            <p class="text-slate-200">${preprod.concept || 'N/A'}</p>
          </div>
          <div class="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
            <span class="text-slate-400 font-semibold block mb-1">Por Qué Funciona:</span>
            <p class="text-slate-200">${preprod.why_it_works || 'N/A'}</p>
          </div>
        </div>

        <!-- Guión Escena por Escena -->
        ${scripts.length > 0 ? `
          <div>
            <h4 class="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-2">
              <i class="fa-solid fa-film text-indigo-400"></i> Guión Escena por Escena
            </h4>
            <div class="overflow-x-auto rounded-xl border border-slate-700/50">
              <table class="w-full text-left script-table text-xs">
                <thead>
                  <tr>
                    <th class="p-2.5 w-12 text-center">#</th>
                    <th class="p-2.5 w-16">Dur.</th>
                    <th class="p-2.5">Visual & Acción</th>
                    <th class="p-2.5">Locución / Diálogo</th>
                    <th class="p-2.5">Texto en Pantalla</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-800/80">
                  ${scripts.map(s => `
                    <tr>
                      <td class="p-2.5 font-bold text-center text-indigo-400">${s.scene || 1}</td>
                      <td class="p-2.5 font-mono text-slate-400">${s.duration_seconds ? s.duration_seconds + 's' : '-'}</td>
                      <td class="p-2.5 text-slate-200">${s.visual || ''} <span class="text-slate-400 italic block mt-0.5">${s.action || ''}</span></td>
                      <td class="p-2.5 text-slate-300">${s.dialogue_or_voiceover || '-'}</td>
                      <td class="p-2.5 text-amber-300 font-mono text-[11px]">${s.on_screen_text || '-'}</td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </div>
        ` : ''}

        <!-- Dirección de Cámara -->
        ${cameras.length > 0 ? `
          <div>
            <h4 class="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-2">
              <i class="fa-solid fa-video text-cyan-400"></i> Especificaciones de Cámara
            </h4>
            <div class="overflow-x-auto rounded-xl border border-slate-700/50">
              <table class="w-full text-left script-table text-xs">
                <thead>
                  <tr>
                    <th class="p-2.5 w-12 text-center">#</th>
                    <th class="p-2.5">Plano (Shot)</th>
                    <th class="p-2.5">Ángulo</th>
                    <th class="p-2.5">Movimiento</th>
                    <th class="p-2.5">Encuadre</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-800/80">
                  ${cameras.map(c => `
                    <tr>
                      <td class="p-2.5 font-bold text-center text-cyan-400">${c.scene || 1}</td>
                      <td class="p-2.5 text-slate-200 font-semibold">${c.shot || '-'}</td>
                      <td class="p-2.5 text-slate-300">${c.angle || '-'}</td>
                      <td class="p-2.5 text-slate-300">${c.movement || '-'}</td>
                      <td class="p-2.5 text-slate-400 font-mono text-[11px]">${c.framing || '-'}</td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </div>
        ` : ''}

        <!-- Dirección de Arte, Audio y Notas -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          <div class="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
            <span class="text-slate-400 font-semibold block mb-1">Locación & Arte:</span>
            <p class="text-slate-300">${preprod.location_and_art_direction || 'N/A'}</p>
          </div>
          <div class="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
            <span class="text-slate-400 font-semibold block mb-1">Audio & Música:</span>
            <p class="text-slate-300">${preprod.audio || 'N/A'}</p>
          </div>
          <div class="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
            <span class="text-slate-400 font-semibold block mb-1">Notas de Edición:</span>
            <p class="text-slate-300">${preprod.editing_notes || 'N/A'}</p>
          </div>
        </div>
      </div>
    `;
  },

  // ── Historial de Tareas ─────────────────────────────────────
  async loadTasks(filterStatus = null) {
    try {
      this.tasks = await API.getTasks(filterStatus, 60);
      const container = document.getElementById('tasks-table-body');
      if (!container) return;

      if (this.tasks.length === 0) {
        container.innerHTML = `
          <tr>
            <td colspan="6" class="p-6 text-center text-slate-500 text-xs">No se encontraron tareas registradas.</td>
          </tr>
        `;
        return;
      }

      container.innerHTML = this.tasks.map(t => {
        const client = this.clients.find(c => c.id === t.client_id);
        const clientName = client ? client.nombre : `Cliente #${t.client_id}`;
        const dateStr = t.created_at ? new Date(t.created_at * 1000).toLocaleString() : '-';

        return `
          <tr class="hover:bg-slate-800/40 cursor-pointer transition" onclick="App.selectTaskFromHistory('${t.task_id}')">
            <td class="p-3 font-mono text-xs text-indigo-400">${t.task_id.slice(0, 8)}...</td>
            <td class="p-3 text-xs font-medium text-slate-200">${clientName}</td>
            <td class="p-3 text-xs text-slate-300 max-w-xs truncate">${t.brief_content}</td>
            <td class="p-3 text-xs">
              <span class="px-2 py-0.5 rounded text-[11px] font-semibold ${
                t.status === 'completed' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' :
                t.status === 'running' ? 'bg-cyan-950 text-cyan-300 border border-cyan-800' :
                'bg-rose-950 text-rose-300 border border-rose-800'
              }">
                ${t.status}
              </span>
            </td>
            <td class="p-3 text-xs font-mono text-slate-400">${t.duration_seconds ? t.duration_seconds + 's' : '-'}</td>
            <td class="p-3 text-xs text-slate-400">${dateStr}</td>
          </tr>
        `;
      }).join('');
    } catch (err) {
      console.warn('Error cargando historial:', err);
    }
  },

  async selectTaskFromHistory(taskId) {
    this.activeStudioWorkflow = 'task';
    this.currentTaskId = taskId;
    await this.loadTaskDetails(taskId);
    this.switchTab('traceability');
    this.showToast(`Tarea ${taskId.slice(0, 8)} cargada en trazabilidad`, 'info');
  },

  // ── Subsistemas y Salud ─────────────────────────────────────
  async checkSystemHealth() {
    try {
      const health = await API.getHealth();
      const services = health.services || {};

      const setBadge = (elementId, isOk) => {
        const el = document.getElementById(elementId);
        if (!el) return;
        el.className = `w-2.5 h-2.5 rounded-full ${isOk ? 'bg-emerald-400 shadow-sm shadow-emerald-400' : 'bg-rose-500 shadow-sm shadow-rose-500'}`;
      };

      setBadge('health-orchestrator', typeof services.orchestrator === 'object');
      setBadge('health-redis', services.redis === 'ok');
      setBadge('health-postgres', services.postgres === 'ok');
      setBadge('health-llm', typeof services.llm_gateway === 'object');

      // Overview
      const overview = await API.getOverview();
      const ragCountElem = document.getElementById('overview-rag-count');
      if (ragCountElem) {
        ragCountElem.textContent = `${overview.rag.ideas || 0} ideas / ${overview.rag.publicaciones || 0} posts`;
      }
      const tasksCountElem = document.getElementById('overview-tasks-count');
      if (tasksCountElem) {
        tasksCountElem.textContent = `${overview.tasks.total} tareas (${overview.tasks.completed} completadas)`;
      }
    } catch (err) {
      console.warn('Error verificando salud:', err);
    }
  },

  async loadToolsCatalog() {
    try {
      const toolsData = await API.getTools();
      const tools = toolsData.tools || [];
      const container = document.getElementById('tools-catalog-container');
      if (!container) return;

      container.innerHTML = tools.map(t => `
        <div class="glass-card p-4 rounded-xl border border-slate-700/60 text-xs space-y-2">
          <div class="flex items-center justify-between">
            <span class="font-bold text-slate-200 text-sm flex items-center gap-1.5">
              <i class="fa-solid fa-toolbox text-indigo-400"></i> ${t.tool}
            </span>
            <span class="px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono text-[10px]">${t.service}</span>
          </div>
          <p class="text-slate-300 text-xs">${t.description || ''}</p>
          <div class="pt-2 border-t border-slate-700/40 flex flex-wrap gap-1">
            ${(t.operations || []).map(op => `<span class="tool-badge px-1.5 py-0.5 rounded bg-slate-900 text-cyan-300">${op.id}</span>`).join('')}
          </div>
        </div>
      `).join('');
    } catch (err) {
      console.warn('Error catálogo tools:', err);
    }
  },

  async loadRagStats() {
    try {
      const stats = await API.getRagStats();
      const container = document.getElementById('rag-stats-badge');
      if (container && stats.data) {
        container.textContent = `${stats.data.ideas} ideas / ${stats.data.publicaciones} posts vectorizados`;
      }
    } catch (_) {}
  },

  // ── Utilidades de Navegación e Interfaz ──────────────────────
  switchTab(tabId) {
    this.activeTab = tabId;

    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tab === tabId);
    });

    document.querySelectorAll('.tab-content').forEach(content => {
      content.classList.toggle('hidden', content.id !== `tab-${tabId}`);
    });

    if (tabId === 'history') {
      this.loadTasks();
    }
    if (tabId === 'library') {
      this.loadIdeas();
      this.updatePublicationControls();
    }
    if (tabId === 'traceability' && this.activeStudioWorkflow === 'batch' && this.latestIdeaBatch) {
      this.renderBatchTrace(this.latestIdeaBatch);
      if (this.activeBatchTraceTaskId) {
        this.currentTaskId = this.activeBatchTraceTaskId;
        this.loadTaskDetails(this.activeBatchTraceTaskId, { renderResult: false });
      }
    }
    if (tabId === 'results' && this.activeStudioWorkflow === 'batch' && this.latestIdeaBatch) {
      this.renderBatchResults(this.latestIdeaBatch);
    }
  },

  copyText(encodedStr) {
    const text = decodeURIComponent(encodedStr);
    navigator.clipboard.writeText(text).then(() => {
      this.showToast('¡Copiado al portapapeles!', 'success');
    }).catch(() => {
      this.showToast('No se pudo copiar automáticamente', 'error');
    });
  },

  exportDossier(format) {
    if (!this.currentTask) return;
    let content = '';
    let filename = `campana-${this.currentTask.task_id.slice(0, 8)}.${format === 'json' ? 'json' : 'md'}`;

    if (format === 'json') {
      content = JSON.stringify(this.currentTask, null, 2);
    } else {
      const result = this.currentTask.result || {};
      const preprod = result.preproduction || {};
      content = `# Campaña Multi-Agente: ${preprod.title || 'Nueva Campaña'}\n\n`
        + `**ID Tarea:** ${this.currentTask.task_id}\n`
        + `**Cliente ID:** ${this.currentTask.client_id}\n\n`
        + `## 1. Idea de Campaña\n${result.idea}\n\n`
        + `## 2. Publicación para Redes Sociales\n${result.publication}\n\n`
        + ((result.publication_variants || []).length
          ? `## Versiones por plataforma\n${result.publication_variants.map(v => `### ${v.platform}\n${v.content}`).join('\n\n')}\n\n`
          : '')
        + (preprod.concept ? `## 3. Dossier de Preproducción\n`
          + `**Concepto:** ${preprod.concept}\n`
          + `**Por qué funciona:** ${preprod.why_it_works}\n` : '');
    }

    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    this.showToast(`Archivo ${filename} descargado`, 'success');
  },

  showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) return;

    const toast = document.createElement('div');
    const colors = {
      success: 'bg-emerald-950 border-emerald-700 text-emerald-200',
      error: 'bg-rose-950 border-rose-700 text-rose-200',
      warning: 'bg-amber-950 border-amber-700 text-amber-200',
      info: 'bg-indigo-950 border-indigo-700 text-indigo-200',
    };

    toast.className = `px-4 py-3 rounded-xl border shadow-lg text-xs flex items-center gap-2.5 transition transform duration-300 opacity-0 translate-y-2 ${colors[type] || colors.info}`;
    toast.innerHTML = `
      <i class="fa-solid ${type === 'success' ? 'fa-check' : type === 'error' ? 'fa-circle-exclamation' : 'fa-circle-info'} text-sm"></i>
      <span>${message}</span>
    `;

    toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.classList.remove('opacity-0', 'translate-y-2');
    }, 10);

    setTimeout(() => {
      toast.classList.add('opacity-0', 'translate-y-2');
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  },
};

window.App = App;

document.addEventListener('DOMContentLoaded', () => {
  App.init();
});
