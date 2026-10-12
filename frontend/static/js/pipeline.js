/**
 * Renderizado y gestión interactiva del grafo de pipeline multi-agente
 */
const PipelineVisualizer = {
  containerId: 'pipeline-container',

  render(stages = [], activeStageIndex = 0) {
    const container = document.getElementById(this.containerId);
    if (!container) return;

    // Si no hay etapas pasadas, renderizamos la estructura estática por defecto
    const defaultStages = [
      {
        id: 'stage-ingress',
        title: '1. Ingesta & Supervisor',
        service: 'orchestrator :8002',
        desc: 'LangGraph Supervisor, checkpointer en Redis (RedisSaver) y despacho a RabbitMQ.',
        badge: 'Supervisor',
        icon: 'fa-sitemap',
        tools: ['TaskStore.create', 'interrupt()'],
      },
      {
        id: 'stage-ideacion',
        title: '2. Agente de Ideación',
        service: 'agente-ideacion :8000',
        desc: 'Grafo de 4 nodos: perfil, tendencias, competencia, RAG semántico y Google News RSS.',
        badge: 'Microservicio',
        icon: 'fa-lightbulb',
        tools: ['client.profile', 'trends.search', 'competitors.search', 'rag.similar', 'news.news', 'llm-gateway'],
      },
      {
        id: 'stage-resume',
        title: '3. Reanudación Orquestador',
        service: 'orchestrator :8002',
        desc: 'Recepción del resultado de ideación; la publicación requiere una solicitud manual.',
        badge: 'Supervisor',
        icon: 'fa-rotate-right',
        tools: ['RedisSaver.resume', 'dispatch_publicacion'],
      },
      {
        id: 'stage-publicacion',
        title: '4. Agente de Publicación',
        service: 'agente-publicacion :8001',
        desc: 'Solo se ejecuta al publicar una idea seleccionada con canales y modo aprobados.',
        badge: 'Microservicio',
        icon: 'fa-share-nodes',
        tools: ['client.profile', 'trends.search', 'trending.trending', 'llm-gateway', 'postiz'],
      },
      {
        id: 'stage-persist',
        title: '5. Memoria & Persistencia',
        service: 'PostgreSQL + Redis',
        desc: 'Guarda embeddings en pgvector, turnos en chat_history y notifica task.completed.',
        badge: 'Persistencia',
        icon: 'fa-database',
        tools: ['rag.save_idea', 'rag.save_publicacion', 'chat_history'],
      },
    ];

    let html = `
      <div class="relative w-full overflow-x-auto pb-4">
        <div class="flex items-center justify-between min-w-[950px] gap-3">
    `;

    defaultStages.forEach((stage, idx) => {
      // Determinar estado actual de la etapa
      let statusClass = 'node-pending';
      let statusIcon = '<i class="fa-solid fa-clock text-slate-400"></i>';
      let statusBadge = '<span class="px-2 py-0.5 rounded text-xs bg-slate-800 text-slate-400">Pendiente</span>';

      if (stages && stages.length > idx) {
        const stageData = stages[idx];
        const st = stageData.status;
        if (st === 'running') {
          statusClass = 'node-running';
          statusIcon = '<i class="fa-solid fa-circle-notch fa-spin text-cyan-400"></i>';
          statusBadge = '<span class="px-2 py-0.5 rounded text-xs bg-cyan-950 text-cyan-300 border border-cyan-800">Ejecutando...</span>';
        } else if (st === 'completed') {
          statusClass = 'node-completed';
          statusIcon = '<i class="fa-solid fa-circle-check text-emerald-400"></i>';
          statusBadge = '<span class="px-2 py-0.5 rounded text-xs bg-emerald-950 text-emerald-300 border border-emerald-800">Completado</span>';
        } else if (st === 'failed') {
          statusClass = 'node-failed';
          statusIcon = '<i class="fa-solid fa-circle-xmark text-rose-400"></i>';
          statusBadge = '<span class="px-2 py-0.5 rounded text-xs bg-rose-950 text-rose-300 border border-rose-800">Falló</span>';
        } else if (st === 'skipped') {
          statusClass = 'node-skipped';
          statusIcon = '<i class="fa-solid fa-circle-minus text-slate-500"></i>';
          statusBadge = '<span class="px-2 py-0.5 rounded text-xs bg-slate-900 text-slate-500 border border-slate-700">No aplica</span>';
        }
      }

      html += `
        <div class="pipeline-node flex-1 glass-card p-4 rounded-xl border border-slate-700/60 ${statusClass} cursor-pointer" onclick="PipelineVisualizer.selectStage(${idx})">
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2">
              <span class="w-7 h-7 rounded-lg bg-slate-800 flex items-center justify-center text-indigo-400 text-sm">
                <i class="fa-solid ${stage.icon}"></i>
              </span>
              <span class="text-xs font-semibold text-slate-300">${stage.title}</span>
            </div>
            <div>${statusIcon}</div>
          </div>

          <div class="text-[11px] text-slate-400 font-mono mb-2">${stage.service}</div>
          <p class="text-xs text-slate-300 line-clamp-2 mb-3 leading-relaxed">${stage.desc}</p>

          <div class="flex items-center justify-between pt-2 border-t border-slate-700/40">
            ${statusBadge}
            <span class="text-[10px] text-slate-400 font-mono">${stage.tools.length} componentes</span>
          </div>

          <div class="mt-2 flex flex-wrap gap-1">
            ${stage.tools.slice(0, 3).map(t => `<span class="tool-badge px-1.5 py-0.5 rounded bg-slate-800/80 text-slate-300 border border-slate-700/50">${t}</span>`).join('')}
            ${stage.tools.length > 3 ? `<span class="tool-badge px-1.5 py-0.5 rounded bg-slate-800/80 text-slate-400">+${stage.tools.length - 3}</span>` : ''}
          </div>
        </div>
      `;

      // Conector entre nodos
      if (idx < defaultStages.length - 1) {
        const isConnectorActive = stages && stages.length > idx && stages[idx].status === 'completed';
        const lineClass = isConnectorActive ? 'bg-gradient-to-r from-emerald-500 to-indigo-500' : 'bg-slate-700';
        html += `
          <div class="flex items-center justify-center px-1 text-slate-500">
            <div class="w-6 h-0.5 ${lineClass}"></div>
            <i class="fa-solid fa-chevron-right text-[10px] -ml-1 text-slate-400"></i>
          </div>
        `;
      }
    });

    html += `
        </div>
      </div>
    `;

    container.innerHTML = html;
  },

  selectStage(stageIndex) {
    if (window.App && window.App.currentTrace) {
      window.TraceViewer.renderStageDetail(window.App.currentTrace, stageIndex);
      const detailElem = document.getElementById('trace-detail-panel');
      if (detailElem) detailElem.scrollIntoView({ behavior: 'smooth' });
    }
  },
};

window.PipelineVisualizer = PipelineVisualizer;
