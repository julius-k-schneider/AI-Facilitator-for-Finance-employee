import { PROGRESS_EVENT } from './progressService'

const API_BASE = import.meta.env.VITE_API_BASE || ''

function csrfToken() {
  const cookie = document.cookie.split('; ').find((item) => item.startsWith('csrftoken='))
  return cookie ? decodeURIComponent(cookie.split('=').slice(1).join('=')) : ''
}

async function request(path, options = {}) {
  const token = csrfToken()
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'X-CSRFToken': token } : {}), ...(options.headers || {}) },
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

const wait = (milliseconds) => new Promise((resolve) => window.setTimeout(resolve, milliseconds))

export async function waitForGenerationRun(runId, timeoutMs = 10 * 60 * 1000, onStatus) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    const data = await getGenerationRun(runId)
    const run = data.generation_run
    onStatus?.(run)
    if (run?.status === 'completed') return run
    if (run?.status === 'failed') throw new Error(run.error_message || 'Mission generation failed')
    await wait(1500)
  }
  throw new Error('Mission generation is still running. Please check again later.')
}

export const getGenerationRun = (runId) => request(`/api/auth/mission-generation-runs/${runId}/`)

export const getCurrentWeeklyGenerationRun = () => request('/api/auth/mission-generation-runs/current-weekly/')

async function startAndWait(path, body, onStatus, timeoutMs) {
  const data = await request(path, { method: 'POST', body: JSON.stringify(body) })
  const run = data.generation_run
  if (!run?.id) throw new Error('Mission generation did not return a run ID')
  onStatus?.(run)
  return run.status === 'completed' ? run : waitForGenerationRun(run.id, timeoutMs, onStatus)
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
    skillLevel: progress.skill_level || 'beginner',
    difficulty: progress.difficulty || 'easy',
    skillProgression: progress.skill_progression || null,
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

export const generateNextWeekMissions = async (weekStart, force = false, onStatus) => {
  const generationRun = await startAndWait(
    '/api/auth/missions/generate-next-week/',
    { force, week_start: weekStart },
    onStatus,
    30 * 60 * 1000,
  )
  return { created_count: generationRun.created_count || 0, generation_run: generationRun }
}

export const startNextWeekMissionGeneration = (weekStart, force = false) => request(
  '/api/auth/missions/generate-next-week/',
  { method: 'POST', body: JSON.stringify({ force, week_start: weekStart }) },
)

export const approveMission = (missionId) => request(`/api/auth/missions/${missionId}/approve/`, {
  method: 'POST',
})

export const regenerateMission = (missionId) => startAndWait(`/api/auth/missions/${missionId}/regenerate/`, {})

export const rejectMission = (missionId) => request(`/api/auth/missions/${missionId}/reject/`, {
  method: 'POST',
})
