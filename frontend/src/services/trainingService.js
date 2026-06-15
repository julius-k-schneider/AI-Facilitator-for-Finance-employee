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

async function trainingRequest(path, body) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.error || 'Training request failed')
  return data
}

export const generateChatChallenge = () => trainingRequest('/api/auth/training/chat-challenge/generate/', {}).then((data) => data.mission)
export const sendTrainingChatMessage = (challengeId, message, language) => trainingRequest('/api/auth/training/chat-challenge/message/', { challenge_id: challengeId, message, language })
export const submitTrainingChatChallenge = (challengeId, answers, language) => trainingRequest('/api/auth/training/chat-challenge/submit/', { challenge_id: challengeId, answers, language }).then((data) => data.result)
