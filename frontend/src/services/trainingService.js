const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export async function generateTrainingMission(type) {
  const response = await fetch(`${API_BASE}/api/auth/training/generate/`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type }),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.error || 'Training generation failed')
  return data.mission
}
