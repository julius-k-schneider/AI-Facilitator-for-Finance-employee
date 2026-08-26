const API_BASE = import.meta.env.VITE_API_BASE || ''

function csrfToken() {
  const cookie = document.cookie.split('; ').find((item) => item.startsWith('csrftoken='))
  return cookie ? decodeURIComponent(cookie.split('=').slice(1).join('=')) : ''
}

async function request(path, options = {}) {
  const token = csrfToken()
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'X-CSRFToken': token } : {}),
      ...(options.headers || {}),
    },
    ...options,
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const error = new Error(data.error || 'Research request failed')
    error.status = response.status
    throw error
  }
  return data
}

export const getResearch = (params = {}) => {
  const query = new URLSearchParams(params).toString()
  return request(`/api/auth/research/${query ? `?${query}` : ''}`)
}

export const updateResearchItem = (id, payload) => request(`/api/auth/research/items/${id}/`, {
  method: 'PATCH',
  body: JSON.stringify(payload),
})

export const deleteResearchItem = (id) => request(`/api/auth/research/items/${id}/`, {
  method: 'DELETE',
})

export const updateResearchSchedule = (payload) => request('/api/auth/research/schedule/', {
  method: 'PATCH',
  body: JSON.stringify(payload),
})

export const startResearchRun = () => request('/api/auth/research/run/', {
  method: 'POST',
  body: JSON.stringify({ force_refresh: false }),
})

export const getLatestResearchRun = () => request('/api/auth/research/run/')
