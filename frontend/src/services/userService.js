const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

async function parseResponse(response) {
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.error || 'request failed')
  }
  return data
}

export async function getCurrentUser() {
  const data = await parseResponse(await fetch(`${API_BASE}/api/auth/user/`, { credentials: 'include' }))
  return data.authenticated ? data.user : null
}

export async function getAllRegisteredUsers() {
  const data = await parseResponse(await fetch(`${API_BASE}/api/auth/users/`, { credentials: 'include' }))
  return data.users || []
}

export async function updateUserRole(userId, role) {
  const data = await parseResponse(
    await fetch(`${API_BASE}/api/auth/users/${userId}/role/`, {
      method: 'PATCH',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role }),
    }),
  )
  return data.user
}

export async function deleteUser(userId) {
  return parseResponse(
    await fetch(`${API_BASE}/api/auth/users/${userId}/`, {
      method: 'DELETE',
      credentials: 'include',
    }),
  )
}
