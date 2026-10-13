/**
 * Visualizador detallado de trazabilidad, herramientas y memoria del agente
 */
const TraceViewer = {
  renderTimeline(trace) {
    const container = document.getElementById('trace-timeline-container');
    if (!container || !trace) return;

    const stages = trace.pipeline_stages || [];
    if (stages.length === 0) {
      container.innerHTML = `<div class="p-6 text-center text-slate-400">Sin datos de trazabilidad para esta tarea.</div>`;
      return;
    }

    let html = `
      <div class="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-700">
    `;

    stages.forEach((st, idx) => {
      let iconColor = 'text-slate-400 border-slate-700 bg-slate-900';
      if (st.status === 'completed') iconColor = 'text-emerald-400 border-emerald-500 bg-emerald-950/80';
      if (st.status === 'running') iconColor = 'text-cyan-400 border-cyan-400 bg-cyan-950/80 animate-pulse';
      if (st.status === 'failed') iconColor = 'text-rose-400 border-rose-500 bg-rose-950/80';

      html += `
        <div class="relative group">
          <div class="absolute -left-6 top-1.5 w-5 h-5 rounded-full border-2 ${iconColor} flex items-center justify-center text-[10px]">
            ${idx + 1}
          </div>

          <div class="glass-card p-4 rounded-xl border border-slate-700/60 transition hover:border-slate-500">
            <div class="flex items-center justify-between flex-wrap gap-2 mb-2">
              <div class="flex items-center gap-2">
                <span class="font-semibold text-sm text-slate-200">${st.name}</span>
                <span class="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-800 text-slate-300 border border-slate-700">${st.component}</span>
              </div>
              <span class="text-xs px-2.5 py-0.5 rounded-full font-medium ${
                st.status === 'completed' ? 'bg-emerald-900/60 text-emerald-300' :
                st.status === 'running' ? 'bg-cyan-900/60 text-cyan-300' :
                st.status === 'failed' ? 'bg-rose-900/60 text-rose-300' : 'bg-slate-800 text-slate-400'
              }">
                ${st.status.toUpperCase()}
              </span>
            </div>

            <p class="text-xs text-slate-400 mb-3">${st.framework}</p>

            ${st.tools_used && st.tools_used.length > 0 ? `
              <div class="mb-3">
                <div class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Herramientas invocadas (Tools-as-a-Service):</div>
                <div class="flex flex-wrap gap-1.5">
                  ${st.tools_used.map(t => `
                    <span class="tool-badge px-2 py-1 rounded bg-slate-800 text-cyan-300 border border-cyan-900/50 flex items-center gap-1.5">
                      <i class="fa-solid fa-screwdriver-wrench text-[10px] text-cyan-400"></i> ${t}
                    </span>
                  `).join('')}
                </div>
              </div>
            ` : ''}

            <!-- Contexto o detalles -->
            ${st.context_retrieved ? `
              <div class="mt-3 pt-3 border-t border-slate-700/50 text-xs">
                <div class="text-slate-400 font-semibold mb-2">Contexto recuperado en memoria:</div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px]">
                  ${st.context_retrieved.trends_context ? `
                    <div class="p-2 rounded bg-slate-900/70 border border-slate-800">
                      <span class="text-indigo-400 font-semibold block mb-1">Tendencias (pgvector):</span>
                      <p class="text-slate-300 line-clamp-3">${st.context_retrieved.trends_context}</p>
                    </div>
                  ` : ''}
                  ${st.context_retrieved.competitors_context ? `
                    <div class="p-2 rounded bg-slate-900/70 border border-slate-800">
                      <span class="text-amber-400 font-semibold block mb-1">Competencia:</span>
                      <p class="text-slate-300 line-clamp-3">${st.context_retrieved.competitors_context}</p>
                    </div>
                  ` : ''}
                  ${st.context_retrieved.news_rss ? `
                    <div class="p-2 rounded bg-slate-900/70 border border-slate-800">
                      <span class="text-sky-400 font-semibold block mb-1">Noticias Google News:</span>
                      <p class="text-slate-300 line-clamp-3">${st.context_retrieved.news_rss}</p>
                    </div>
                  ` : ''}
                  ${st.context_retrieved.trending_topics ? `
                    <div class="p-2 rounded bg-slate-900/70 border border-slate-800">
                      <span class="text-emerald-400 font-semibold block mb-1">Trending Topics:</span>
                      <p class="text-slate-300 line-clamp-3">${st.context_retrieved.trending_topics}</p>
                    </div>
                  ` : ''}
                </div>
              </div>
            ` : ''}

            ${st.details ? `
              <div class="mt-2 text-[11px] text-slate-400 font-mono bg-slate-900/60 p-2 rounded border border-slate-800">
                ${Object.entries(st.details).map(([k, v]) => `
                  <div><span class="text-slate-500">${k}:</span> ${typeof v === 'object' ? JSON.stringify(v) : v}</div>
                `).join('')}
              </div>
            ` : ''}
          </div>
        </div>
      `;
    });

    html += `</div>`;
    container.innerHTML = html;
  },

  renderChatHistory(messages = []) {
    const container = document.getElementById('chat-history-container');
    if (!container) return;

    if (!messages || messages.length === 0) {
      container.innerHTML = `<div class="p-6 text-center text-slate-500 text-sm">No hay mensajes registrados en PostgreSQL para esta tarea aún.</div>`;
      return;
    }

    let html = `<div class="space-y-4">`;
    messages.forEach((m) => {
      const isUser = m.role === 'user';
      html += `
        <div class="flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}">
          ${!isUser ? `
            <div class="w-8 h-8 rounded-full bg-indigo-600/40 border border-indigo-400 flex items-center justify-center text-indigo-300 text-xs shrink-0">
              <i class="fa-solid fa-robot"></i>
            </div>
          ` : ''}

          <div class="max-w-[85%] rounded-2xl p-4 ${
            isUser ? 'bg-indigo-600 text-white rounded-tr-none' : 'glass-card border border-slate-700/70 text-slate-200 rounded-tl-none'
          }">
            <div class="flex items-center justify-between text-[11px] opacity-75 mb-1.5 gap-3">
              <span class="font-semibold uppercase">${m.role}</span>
              <span class="font-mono">${new Date(m.created_at).toLocaleTimeString()}</span>
            </div>
            <div class="text-xs whitespace-pre-wrap leading-relaxed">${this.escapeHtml(m.content)}</div>
          </div>

          ${isUser ? `
            <div class="w-8 h-8 rounded-full bg-slate-800 border border-slate-600 flex items-center justify-center text-slate-300 text-xs shrink-0">
              <i class="fa-solid fa-user"></i>
            </div>
          ` : ''}
        </div>
      `;
    });
    html += `</div>`;
    container.innerHTML = html;
  },

  renderRawJson(task) {
    const container = document.getElementById('raw-json-container');
    if (!container) return;
    container.textContent = JSON.stringify(task, null, 2);
  },

  renderStageDetail(trace, stageIndex) {
    const detailPanel = document.getElementById('trace-detail-panel');
    if (!detailPanel || !trace || !trace.pipeline_stages) return;

    const stage = trace.pipeline_stages[stageIndex];
    if (!stage) return;

    detailPanel.innerHTML = `
      <div class="glass-card p-5 rounded-2xl border border-indigo-500/40 mt-6 animate-fade-in">
        <div class="flex items-center justify-between pb-3 border-b border-slate-700/60 mb-4">
          <div class="flex items-center gap-3">
            <span class="px-3 py-1 rounded-lg bg-indigo-950 text-indigo-300 border border-indigo-800 font-semibold text-xs">
              Etapa ${stageIndex + 1}
            </span>
            <h4 class="text-base font-bold text-slate-100">${stage.name}</h4>
          </div>
          <span class="text-xs font-mono text-slate-400">${stage.component}</span>
        </div>

        <div class="space-y-4 text-xs">
          <div>
            <span class="text-slate-400 block font-semibold mb-1">Mecanismo / Patrón:</span>
            <p class="text-slate-300 bg-slate-900/70 p-2.5 rounded-lg border border-slate-800">${stage.framework}</p>
          </div>

          ${stage.tools_used && stage.tools_used.length > 0 ? `
            <div>
              <span class="text-slate-400 block font-semibold mb-1">Contratos de herramientas ejecutados:</span>
              <div class="flex flex-wrap gap-2">
                ${stage.tools_used.map(t => `
                  <span class="px-2.5 py-1 rounded-md bg-slate-800 text-cyan-300 border border-cyan-900/60 font-mono text-xs">
                    ${t}
                  </span>
                `).join('')}
              </div>
            </div>
          ` : ''}

          ${stage.output ? `
            <div>
              <span class="text-slate-400 block font-semibold mb-1">Salida generada:</span>
              <pre class="bg-slate-950 p-3 rounded-lg border border-slate-800 text-slate-300 overflow-x-auto text-[11px] max-h-60 leading-relaxed font-mono">${JSON.stringify(stage.output, null, 2)}</pre>
            </div>
          ` : ''}
        </div>
      </div>
    `;
  },

  escapeHtml(text) {
    if (!text) return '';
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  },
};

window.TraceViewer = TraceViewer;
