import { waitForGenerationRun } from './missionService'

const API_BASE = import.meta.env.VITE_API_BASE || ''

function csrfToken() {
  const cookie = document.cookie.split('; ').find((item) => item.startsWith('csrftoken='))
  return cookie ? decodeURIComponent(cookie.split('=').slice(1).join('=')) : ''
}

async function trainingRequest(path, body) {
  const token = csrfToken()
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json', ...(token ? { 'X-CSRFToken': token } : {}) }, body: JSON.stringify(body),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.error || 'Training request failed')
  return data
}

async function startTrainingGeneration(path, body) {
  const started = await trainingRequest(path, body)
  const run = started.generation_run
  if (!run?.id) throw new Error('Training generation did not return a run ID')
  if (run.status !== 'completed') await waitForGenerationRun(run.id)
  return trainingRequest(`/api/auth/mission-generation-runs/${run.id}/consume/`, {}).then((data) => data.mission)
}

export const generateTrainingMission = (type) => startTrainingGeneration('/api/auth/training/generate/', { type })
export const generateTaskChallenge = (missionType) => startTrainingGeneration('/api/auth/training/task-challenge/generate/', { mission_type: missionType })
export const submitTrainingTaskChallenge = (challengeId, values, language) => trainingRequest('/api/auth/training/task-challenge/submit/', { challenge_id: challengeId, values, language }).then((data) => data.result)

export const generateChatChallenge = () => startTrainingGeneration('/api/auth/training/chat-challenge/generate/', {})
export const sendTrainingChatMessage = (challengeId, message, language) => trainingRequest('/api/auth/training/chat-challenge/message/', { challenge_id: challengeId, message, language })
export const submitTrainingChatChallenge = (challengeId, answers, language) => trainingRequest('/api/auth/training/chat-challenge/submit/', { challenge_id: challengeId, answers, language }).then((data) => data.result)
