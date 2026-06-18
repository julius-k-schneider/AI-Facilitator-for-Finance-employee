const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
export const PROGRESS_EVENT = 'ai-facilitator-progress-updated'

export const EMPTY_PROGRESS = {
  missionScores: {},
  completedMissions: [],
  totalPoints: 0,
  completedMissionCount: 0,
  currentStreak: 0,
  maxStreak: 0,
  level: 'Starter',
  updatedAt: null,
}

function normalizeProgress(progress = {}) {
  return {
    missionScores: progress.mission_scores || progress.missionScores || {},
    completedMissions: progress.completed_missions || progress.completedMissions || [],
    totalPoints: progress.total_points ?? progress.totalPoints ?? 0,
    completedMissionCount: progress.completed_mission_count ?? progress.completedMissionCount ?? 0,
    currentStreak: progress.current_streak ?? progress.currentStreak ?? 0,
    maxStreak: progress.max_streak ?? progress.maxStreak ?? 0,
    level: progress.level || 'Starter',
    updatedAt: progress.updated_at || progress.updatedAt || null,
  }
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.error || 'Progress request failed')
  return data
}

export function getUserId(user) {
  return String(user?.id || '')
}

export async function getUserProgress() {
  const data = await request('/api/auth/progress/')
  return normalizeProgress(data.progress)
}

export function getLevel(totalPoints) {
  if (totalPoints >= 180) return 'Advanced'
  if (totalPoints >= 90) return 'Practitioner'
  return 'Starter'
}
