const API_BASE = import.meta.env.VITE_API_BASE || ''

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

async function agentRequest(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.error || 'Agent request failed')
  return data
}

export const getAgentChats = () => agentRequest('/api/auth/agent/chats/').then((data) => data.chats || [])

export const createAgentChat = () => agentRequest('/api/auth/agent/chats/', {
  method: 'POST',
  body: JSON.stringify({}),
}).then((data) => data.chat)

export const getAgentChat = (chatId) => agentRequest(`/api/auth/agent/chats/${chatId}/`).then((data) => data.chat)

export const deleteAgentChat = (chatId) => agentRequest(`/api/auth/agent/chats/${chatId}/`, {
  method: 'DELETE',
})

export const sendAgentChatMessage = (chatId, message, language) => agentRequest(`/api/auth/agent/chats/${chatId}/message/`, {
  method: 'POST',
  body: JSON.stringify({ message, language }),
}).then((data) => data.chat)
