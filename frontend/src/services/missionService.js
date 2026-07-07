import { PROGRESS_EVENT } from './progressService'

const API_BASE = import.meta.env.VITE_API_BASE || ''

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

export const getAvailableMissions = (language) => request(`/api/auth/missions/available/?lang=${language}`)

export const getArchivedMissions = (params = {}) => request(`/api/auth/missions/archive/?${new URLSearchParams(params)}`)

export async function submitMission(missionId, answer, language) {
  const data = await request('/api/auth/progress/complete/', {
    method: 'POST',
    body: JSON.stringify({ mission_id: missionId, answer, language }),
  })
  const progress = data.progress
  window.dispatchEvent(new CustomEvent(PROGRESS_EVENT, { detail: {
    missionScores: progress.mission_scores || {},
    completedMissions: progress.completed_missions || [],
    completedMissionCount: progress.completed_mission_count || 0,
    currentStreak: progress.current_streak || 0,
    maxStreak: progress.max_streak || 0,
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

export const updateMission = (missionId, payload) => request(`/api/auth/missions/${missionId}/`, {
  method: 'PATCH',
  body: JSON.stringify(payload),
})

export const getReviewMissions = (weekStart) => request(`/api/auth/missions/review/?week_start=${weekStart}`)

export const approveAllReviewMissions = (weekStart) => request('/api/auth/missions/review/approve-all/', {
  method: 'POST',
  body: JSON.stringify({ week_start: weekStart }),
})

export const rejectAllReviewMissions = (weekStart) => request('/api/auth/missions/review/reject-all/', {
  method: 'POST',
  body: JSON.stringify({ week_start: weekStart }),
})

export const generateNextWeekMissions = (weekStart, force = false) => request('/api/auth/missions/generate-next-week/', {
  method: 'POST',
  body: JSON.stringify({ force, week_start: weekStart }),
})

export const approveMission = (missionId) => request(`/api/auth/missions/${missionId}/approve/`, {
  method: 'POST',
})

export const regenerateMission = (missionId) => request(`/api/auth/missions/${missionId}/regenerate/`, {
  method: 'POST',
})

export const rejectMission = (missionId) => request(`/api/auth/missions/${missionId}/reject/`, {
  method: 'POST',
})
