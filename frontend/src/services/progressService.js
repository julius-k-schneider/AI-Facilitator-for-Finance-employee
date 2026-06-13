import { MISSIONS } from '../data/missions'

const STORAGE_KEY = 'ai-facilitator:user-progress:v1'
export const PROGRESS_EVENT = 'ai-facilitator-progress-updated'

function readStore() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
  } catch {
    return {}
  }
}

function writeStore(store) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(store))
  window.dispatchEvent(new CustomEvent(PROGRESS_EVENT))
}

export function deleteUserProgress(userId) {
  if (!userId) return

  const store = readStore()
  delete store[String(userId)]
  writeStore(store)
}

export function getUserId(user) {
  return String(user?.id || user?.email || user?.username || '')
}

function normalizeProgress(userId, progress = {}) {
  const missionScores = progress.missionScores || {}
  const completedMissions = Object.keys(missionScores).filter((missionId) => missionScores[missionId] > 0)
  const totalPoints = Object.values(missionScores).reduce((sum, value) => sum + Number(value || 0), 0)

  return {
    userId,
    totalPoints,
    completedMissions,
    missionScores,
    updatedAt: progress.updatedAt || null,
  }
}

export function getUserProgress(userId) {
  if (!userId) {
    return normalizeProgress('')
  }

  const store = readStore()
  return normalizeProgress(userId, store[userId])
}

export function completeMission(userId, missionId, score) {
  const mission = MISSIONS.find((item) => item.id === missionId)
  if (!userId || !mission) {
    return getUserProgress(userId)
  }

  const store = readStore()
  const current = normalizeProgress(userId, store[userId])
  const safeScore = Math.max(0, Math.min(Number(score || 0), mission.maxPoints))
  const previousBest = Number(current.missionScores[missionId] || 0)
  const nextBest = Math.max(previousBest, safeScore)

  store[userId] = normalizeProgress(userId, {
    ...current,
    missionScores: {
      ...current.missionScores,
      [missionId]: nextBest,
    },
    updatedAt: new Date().toISOString(),
  })

  writeStore(store)
  return store[userId]
}

export function getTotalPoints(userId) {
  return getUserProgress(userId).totalPoints
}

export function getCompletedMissionCount(userId) {
  return getUserProgress(userId).completedMissions.length
}

export function getNextMission(userId) {
  const progress = getUserProgress(userId)
  return MISSIONS.find((mission) => !progress.completedMissions.includes(mission.id)) || null
}

export function getLevel(totalPoints) {
  if (totalPoints >= 180) return 'Advanced'
  if (totalPoints >= 90) return 'Practitioner'
  return 'Starter'
}

export function getLeaderboard(users) {
  return users
    .map((user) => {
      const userId = getUserId(user)
      const progress = getUserProgress(userId)
      const name = `${user.first_name || ''} ${user.last_name || ''}`.trim()

      return {
        user,
        userId,
        name: name || user.username || user.email,
        email: user.email,
        totalPoints: progress.totalPoints,
        completedMissions: progress.completedMissions.length,
        level: getLevel(progress.totalPoints),
      }
    })
    .sort((a, b) => {
      if (b.totalPoints !== a.totalPoints) return b.totalPoints - a.totalPoints
      if (b.completedMissions !== a.completedMissions) return b.completedMissions - a.completedMissions
      return a.name.localeCompare(b.name)
    })
    .map((entry, index) => ({ ...entry, rank: index + 1 }))
}
export function markResourceRead(userId, resourceId) {
  if (!userId || !resourceId) return
  const store = readStore()
  const current = store[userId] || {}
  const readResources = current.readResources || []
  if (!readResources.includes(resourceId)) {
    readResources.push(resourceId)
  }
  store[userId] = { ...current, readResources }
  writeStore(store)
}

export function hasReadResource(userId, resourceId) {
  if (!userId || !resourceId) return false
  const store = readStore()
  const current = store[userId] || {}
  return (current.readResources || []).includes(resourceId)
}

