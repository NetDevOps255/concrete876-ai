const BASE = '/api'

// ─── Token management ────────────────────────────────────────────────────────
// JWT stored in sessionStorage — cleared when browser tab closes

export const auth = {
  getToken: () => sessionStorage.getItem('pm_token'),
  setToken: (t) => sessionStorage.setItem('pm_token', t),
  clearToken: () => sessionStorage.removeItem('pm_token'),
  isLoggedIn: () => !!sessionStorage.getItem('pm_token'),
}

// ─── Core request ────────────────────────────────────────────────────────────

async function req(method, path, body = null, { public: isPublic = false } = {}) {
  const headers = { 'Content-Type': 'application/json' }

  if (!isPublic) {
    const token = auth.getToken()
    if (!token) {
      // Trigger logout/redirect by throwing a specific error
      const err = new Error('Unauthorized')
      err.status = 401
      throw err
    }
    headers['Authorization'] = `Bearer ${token}`
  }

  const opts = { method, headers }
  if (body) opts.body = JSON.stringify(body)

  const r = await fetch(BASE + path, opts)

  // Token expired or invalid — force re-login
  if (r.status === 401) {
    auth.clearToken()
    const err = new Error('Session expired. Please log in again.')
    err.status = 401
    throw err
  }

  if (!r.ok) {
    const errBody = await r.json().catch(() => ({ detail: r.statusText }))
    const err = new Error(errBody.detail || r.statusText)
    err.status = r.status
    throw err
  }

  if (r.status === 204) return null
  return r.json()
}

// ─── API surface ─────────────────────────────────────────────────────────────

export const api = {
  // Auth (public — no token needed)
  login: (username, password) =>
    req('POST', '/auth/login', { username, password }, { public: true }),
  health: () =>
    req('GET', '/health', null, { public: true }),

  // Stats
  stats: () => req('GET', '/stats'),

  // Hosts
  hosts: () => req('GET', '/hosts/'),
  addHost: (data) => req('POST', '/hosts/', data),
  deleteHost: (id) => req('DELETE', `/hosts/${id}`),
  hostPackages: (id) => req('GET', `/hosts/${id}/packages`),
  hostJobs: (id) => req('GET', `/hosts/${id}/jobs`),
  hostContainers: (id) => req('GET', `/hosts/${id}/containers`),
  checkHost: (id) => req('POST', `/hosts/${id}/check`),
  patchHost: (id, dry_run = false) =>
    req('POST', `/hosts/${id}/patch?dry_run=${dry_run}`),

  // Docker
  docker: () => req('GET', '/docker/'),
  dockerSummary: () => req('GET', '/docker/summary'),
  dockerScan: () => req('POST', '/docker/scan'),

  // Proxmox
  proxmoxStatus: () => req('GET', '/proxmox/status'),
  proxmoxGuests: () => req('GET', '/proxmox/guests'),
  proxmoxSync: () => req('POST', '/proxmox/sync'),

  // Alerts
  telegramStatus: () => req('GET', '/alerts/telegram/status'),
  connectTelegram: (data) => req('POST', '/alerts/telegram/connect', data),
  alertRules: () => req('GET', '/alerts/rules'),
  toggleRule: (id, enabled) =>
    req('PATCH', `/alerts/rules/${id}?enabled=${enabled}`),
  testAlert: (event_type) => req('POST', `/alerts/test/${event_type}`),

  // Logs
  logs: (limit = 100) => req('GET', `/logs/?limit=${limit}`),
  logSummary: () => req('GET', '/logs/summary'),
  exportLogs: () => {
    const token = auth.getToken()
    // Open in new tab with auth header injected via fetch + blob URL
    fetch(`${BASE}/logs/export/csv`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = 'patchmon-audit.csv'
        a.click()
        URL.revokeObjectURL(url)
      })
  },
}
