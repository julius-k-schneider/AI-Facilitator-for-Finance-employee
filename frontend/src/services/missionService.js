import { PROGRESS_EVENT } from './progressService'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const error = new Error(data.error || 'Mission request failed')
    error.status = response.status
    throw error
  }
  return data
}

export const getDailyMissions = (language) => request(`/api/auth/missions/today/?lang=${language}`)

export async function submitMission(missionId, answer) {
  const data = await request('/api/auth/progress/complete/', {
    method: 'POST',
    body: JSON.stringify({ mission_id: missionId, answer }),
  })
  const progress = data.progress
  window.dispatchEvent(new CustomEvent(PROGRESS_EVENT, { detail: {
    missionScores: progress.mission_scores || {},
    completedMissions: progress.completed_missions || [],
    completedMissionCount: progress.completed_mission_count || 0,
    totalPoints: progress.total_points || 0,
    level: progress.level || 'Starter',
    updatedAt: progress.updated_at || null,
  } }))
  return data
}

export const getMissionSchedule = (from, to) => request(`/api/auth/missions/schedule/?from=${from}&to=${to}`)

export const createMission = (payload) => request('/api/auth/missions/schedule/', {
  method: 'POST',
  body: JSON.stringify(payload),
})

export const deleteMission = (missionId) => request(`/api/auth/missions/${missionId}/`, {
  method: 'DELETE',
})
