const BASE = '/api'
const TOKEN_KEY = 'pp_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

async function request(path, { method = 'GET', body, auth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (auth) {
    const token = getToken()
    if (token) headers.Authorization = `Bearer ${token}`
  }

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (res.status === 204) return null

  const text = await res.text()
  const data = text ? JSON.parse(text) : null

  if (!res.ok) {
    const message = data?.detail || res.statusText || 'Something went wrong'
    throw new ApiError(res.status, typeof message === 'string' ? message : JSON.stringify(message))
  }
  return data
}

export const api = {
  register: (payload) => request('/auth/register', { method: 'POST', body: payload, auth: false }),
  login: (payload) => request('/auth/login', { method: 'POST', body: payload, auth: false }),

  me: () => request('/me'),
  updateMe: (payload) => request('/me', { method: 'PATCH', body: payload }),
  theme: () => request('/preferences/theme'),
  updateTheme: (theme) => request('/preferences/theme', { method: 'PATCH', body: { theme } }),

  dailyChallenge: () => request('/daily-challenge'),
  startTest: (testId) => request(`/tests/${testId}/start`, { method: 'POST' }),
  saveResponse: (testId, payload) => request(`/tests/${testId}/response`, { method: 'POST', body: payload }),
  submitTest: (testId) => request(`/tests/${testId}/submit`, { method: 'POST' }),
  getResult: (testId) => request(`/tests/${testId}/result`),
  history: (limit = 30) => request(`/tests/history?limit=${limit}`),

  progress: () => request('/progress'),
  topicProgress: () => request('/progress/topics'),

  report: (testId) => request(`/reports/${testId}`),

  currentStudyPlan: () => request('/study-plans/current'),
  createStudyPlan: (payload) => request('/study-plans', { method: 'POST', body: payload }),
  updateStudyPlan: (id, payload) => request(`/study-plans/${id}`, { method: 'PATCH', body: payload }),
  regenerateStudyPlan: (id) => request(`/study-plans/${id}/regenerate`, { method: 'POST' }),
  completeStudyTask: (id) => request(`/study-plans/tasks/${id}/complete`, { method: 'POST' }),

  dueReviews: () => request('/reviews/due'),
  reviewStats: () => request('/reviews/stats'),
  submitReview: (id, payload) => request(`/reviews/${id}/submit`, { method: 'POST', body: payload }),

  companies: (query = '') => request(`/companies?q=${encodeURIComponent(query)}`),
  company: (slug) => request(`/companies/${encodeURIComponent(slug)}`),
  companyPacks: (slug) => request(`/companies/${encodeURIComponent(slug)}/packs`),
  startCompanyPack: (id) => request(`/company-packs/${id}/start`, { method: 'POST' }),
  answerCompanyPackQuestion: (id, payload) => request(`/company-packs/${id}/answer`, { method: 'POST', body: payload }),
  companyPackSources: (id) => request(`/company-packs/${id}/sources`),
  myCompanyPacks: () => request('/company-packs/my'),
}
