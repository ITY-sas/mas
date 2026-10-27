/**
 * Cliente de API y SSE para el BFF de Multi-Agent Studio
 */
export const API = {
  baseUrl: '',

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    try {
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...(options.headers || {}),
        },
        ...options,
      });

      if (!response.ok) {
        let errMessage = `Error ${response.status}: ${response.statusText}`;
        try {
          const errData = await response.json();
          if (errData.detail) {
            errMessage = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
          }
        } catch (_) {}
        throw new Error(errMessage);
      }

      return await response.json();
    } catch (err) {
      console.warn(`[API Info] ${endpoint}:`, err.message);
      throw err;
    }
  },

  // ── Salud y Sistema ─────────────────────────────
  async getHealth() {
    return this.request('/api/health');
  },

  async getOverview() {
    return this.request('/api/overview');
  },

  async getTools() {
    return this.request('/api/tools');
  },

  async getRagStats() {
    return this.request('/api/rag/stats');
  },

  // ── Clientes y Marcas ────────────────────────────
  async getClients() {
    return this.request('/api/clients');
  },

  async getClient(id) {
    return this.request(`/api/clients/${id}`);
  },

  async updateBrand(brandId, data) {
    return this.request(`/api/brands/${brandId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async deleteBrand(brandId) {
    return this.request(`/api/brands/${brandId}`, {
      method: 'DELETE',
    });
  },

  async getBrandChannels(brandId) {
    return this.request(`/api/brands/${brandId}/channels`);
  },

  async getPostizIntegrations() {
    return this.request('/api/postiz/integrations');
  },

  async linkBrandChannel(brandId, externalId, reassign = false) {
    return this.request(`/api/brands/${brandId}/channels`, {
      method: 'POST',
      body: JSON.stringify({ external_id: externalId, reassign }),
    });
  },

  async unlinkBrandChannel(brandId, externalId) {
    return this.request(`/api/brands/${brandId}/channels/${encodeURIComponent(externalId)}`, {
      method: 'DELETE',
    });
  },

  // ── Generación de Ideas ─────────────────────────
  async generateIdeas(batchData) {
    return this.request('/api/ideas/generate', {
      method: 'POST',
      body: JSON.stringify(batchData),
    });
  },

  async getIdeaBatch(batchId, brandId) {
    const query = new URLSearchParams({ brand_id: brandId });
    return this.request(`/api/idea-batches/${encodeURIComponent(batchId)}?${query}`);
  },

  async getIdeas(brandId, { query = '', limit = 50, offset = 0 } = {}) {
    const params = new URLSearchParams({
      brand_id: brandId,
      limit,
      offset,
    });
    if (query) params.set('query', query);
    return this.request(`/api/ideas?${params}`);
  },

  async getIdea(ideaId, brandId) {
    const params = new URLSearchParams({ brand_id: brandId });
    return this.request(`/api/ideas/${ideaId}?${params}`);
  },

  async updateIdea(ideaId, brandId, data) {
    const params = new URLSearchParams({ brand_id: brandId });
    return this.request(`/api/ideas/${ideaId}?${params}`, {
      method: 'PUT',
      body: JSON.stringify({ ...data, brand_id: Number(brandId) }),
    });
  },

  async deleteIdea(ideaId, brandId) {
    const params = new URLSearchParams({ brand_id: brandId });
    return this.request(`/api/ideas/${ideaId}?${params}`, {
      method: 'DELETE',
    });
  },

  // ── Publicación ─────────────────────────────────
  async publishIdea(ideaId, publication) {
    return this.request(`/api/ideas/${ideaId}/publish`, {
      method: 'POST',
      body: JSON.stringify(publication),
    });
  },

  async getPublications(brandId, limit = 100) {
    const params = new URLSearchParams({ brand_id: brandId, limit });
    return this.request(`/api/publications?${params}`);
  },

  async getSavedPublications(brandId, { ideaId = null, limit = 50, offset = 0, includeArchived = false } = {}) {
    const params = new URLSearchParams({ brand_id: brandId, limit, offset, include_archived: includeArchived });
    if (ideaId) params.set('idea_id', ideaId);
    return this.request(`/api/publications/saved?${params}`);
  },

  async getSavedPublication(pubId, brandId) {
    const params = new URLSearchParams({ brand_id: brandId });
    return this.request(`/api/publications/saved/${pubId}?${params}`);
  },

  async updatePublication(pubId, brandId, data) {
    const params = new URLSearchParams({ brand_id: brandId });
    return this.request(`/api/publications/saved/${pubId}?${params}`, {
      method: 'PUT',
      body: JSON.stringify({ ...data, brand_id: Number(brandId) }),
    });
  },

  async deletePublication(pubId, brandId) {
    const params = new URLSearchParams({ brand_id: brandId });
    return this.request(`/api/publications/saved/${pubId}?${params}`, {
      method: 'DELETE',
    });
  },

  async approvePreparedPublication(taskId, publication) {
    return this.request(`/api/publications/${encodeURIComponent(taskId)}/approve`, {
      method: 'POST',
      body: JSON.stringify(publication),
    });
  },

  async deliverPreparedPublication(taskId, publication) {
    return this.request(`/api/publications/${encodeURIComponent(taskId)}/deliver`, {
      method: 'POST',
      body: JSON.stringify(publication),
    });
  },

  // ── Tareas ──────────────────────────────────────
  async createTask(briefData) {
    return this.request('/api/tasks', {
      method: 'POST',
      body: JSON.stringify(briefData),
    });
  },

  async createDemo(demoData) {
    return this.request('/api/demo', {
      method: 'POST',
      body: JSON.stringify(demoData),
    });
  },

  async getTasks(status = null, limit = 100, brandId = null) {
    const query = new URLSearchParams();
    if (status) query.set('status', status);
    if (limit) query.set('limit', limit);
    if (brandId !== null && brandId !== undefined && brandId !== '') query.set('brand_id', brandId);
    return this.request(`/api/tasks?${query.toString()}`);
  },

  async getTask(taskId) {
    return this.request(`/api/tasks/${taskId}`);
  },

  async getTaskHistory(taskId) {
    return this.request(`/api/tasks/${taskId}/history`);
  },

  async getTaskTrace(taskId) {
    return this.request(`/api/tasks/${taskId}/trace`);
  },

  // ── Server-Sent Events (SSE) ────────────────────
  streamTask(taskId, onMessage, onDone, onError) {
    const sseUrl = `${this.baseUrl}/api/tasks/${taskId}/stream`;
    const eventSource = new EventSource(sseUrl);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (onMessage) onMessage(data);

        if (data.completed) {
          eventSource.close();
          if (onDone) onDone(data);
        }
      } catch (err) {
        console.error('Error parseando SSE data:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.warn('SSE conexión finalizada o error:', err);
      eventSource.close();
      if (onError) onError(err);
    };

    return eventSource;
  },
};
