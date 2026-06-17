const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export async function sendAgentMessage(messages, language) {
  const response = await fetch(`${API_BASE}/api/auth/agent/chat/`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages, language }),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.error || 'Agent request failed')
  return data.reply
}
