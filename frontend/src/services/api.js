import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120_000,
  headers: { 'Content-Type': 'application/json' },
})

// Attach token from localStorage
api.interceptors.request.use((config) => {
  const raw = localStorage.getItem('documind-auth')
  if (raw) {
    try {
      const { state } = JSON.parse(raw)
      if (state?.accessToken) config.headers.Authorization = `Bearer ${state.accessToken}`
    } catch {}
  }
  return config
}, (error) => Promise.reject(error))

// Auto-refresh on 401
api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const raw = localStorage.getItem('documind-auth')
      if (raw) {
        try {
          const { state } = JSON.parse(raw)
          if (state?.refreshToken) {
            const { data } = await axios.post('/api/v1/auth/refresh', { refresh_token: state.refreshToken })
            api.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`
            original.headers.Authorization = `Bearer ${data.access_token}`
            return api(original)
          }
        } catch { window.location.href = '/login' }
      }
    }
    return Promise.reject(error)
  }
)

export default api

export const authApi = {
  login:    (d) => api.post('/auth/login', d),
  register: (d) => api.post('/auth/register', d),
  me:       ()  => api.get('/auth/me'),
  refresh:  (d) => api.post('/auth/refresh', d),
}

export const documentsApi = {
  upload: (form) => api.post('/documents/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } }),
  list:   (ws)   => api.get('/documents/', { params: ws ? { workspace_id: ws } : {} }),
  get:    (id)   => api.get(`/documents/${id}`),
  status: (id)   => api.get(`/documents/${id}/status`),
  delete: (id)   => api.delete(`/documents/${id}`),
}

export const chatApi = {
  createSession: (d)    => api.post('/chat/sessions', d),
  listSessions:  ()     => api.get('/chat/sessions'),
  deleteSession: (id)   => api.delete(`/chat/sessions/${id}`),
  sendMessage:   (id,d) => api.post(`/chat/sessions/${id}/messages`, d),
  getMessages:   (id)   => api.get(`/chat/sessions/${id}/messages`),
}

export const searchApi = {
  semantic: (d) => api.post('/search/semantic', d),
}

export const workspacesApi = {
  create: (d)     => api.post('/workspaces/', d),
  list:   ()      => api.get('/workspaces/'),
  invite: (id, d) => api.post(`/workspaces/${id}/invite`, d),
  delete: (id)    => api.delete(`/workspaces/${id}`),
}

export const mlApi = {
  summarize:  (d) => api.post('/ml/summarize', d),
  classify:   (d) => api.post('/ml/classify', d),
  keywords:   (d) => api.post('/ml/keywords', d),
  sentiment:  (d) => api.post('/ml/sentiment', d),
  entities:   (d) => api.post('/ml/entities', d),
  stats:      (d) => api.post('/ml/stats', d),
  cluster:    (d) => api.post('/ml/cluster', d),
  enhanced:   (d) => api.post('/ml/chat/enhanced', d),
}

export const llmopsApi = {
  overview:      (hours=24) => api.get('/llmops/metrics/overview', { params: { hours } }),
  latency:       (hours=24) => api.get('/llmops/metrics/latency', { params: { hours } }),
  costByModel:   (hours=24) => api.get('/llmops/metrics/cost-by-model', { params: { hours } }),
  costTimeseries:(hours=24) => api.get('/llmops/metrics/cost-timeseries', { params: { hours } }),
  recentCalls:   (limit=50) => api.get('/llmops/calls/recent', { params: { limit } }),
  alerts:        ()         => api.get('/llmops/alerts'),
  prompts:       (name)     => api.get(`/llmops/prompts/${name}/versions`),
  createPrompt:  (d)        => api.post('/llmops/prompts', d),
  experiments:   ()         => api.get('/llmops/experiments'),
  createExp:     (d)        => api.post('/llmops/experiments', d),
}
