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

  dailyChallenge: () => request('/daily-challenge'),
  startTest: (testId) => request(`/tests/${testId}/start`, { method: 'POST' }),
  saveResponse: (testId, payload) => request(`/tests/${testId}/response`, { method: 'POST', body: payload }),
  submitTest: (testId) => request(`/tests/${testId}/submit`, { method: 'POST' }),
  getResult: (testId) => request(`/tests/${testId}/result`),
  history: (limit = 30) => request(`/tests/history?limit=${limit}`),

  progress: () => request('/progress'),
  topicProgress: () => request('/progress/topics'),

  report: (testId) => request(`/reports/${testId}`),
}
