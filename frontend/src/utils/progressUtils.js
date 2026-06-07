import { games } from '../data/games'
import { learningModules } from '../data/learningPath'

export function getUserDisplayName(user) {
  const fullName = [user?.first_name, user?.last_name].filter(Boolean).join(' ').trim()
  return fullName || user?.username || 'Finance Learner'
}

export function getRole(user) {
  return user?.role || user?.profile?.role || 'Finance Employee'
}

export function getLevel(points) {
  if (points >= 500) return 5
  if (points >= 300) return 4
  if (points >= 150) return 3
  if (points >= 60) return 2
  return 1
}

export function getGamePoints(game, gameProgress) {
  if (!game || !gameProgress?.completed) return 0
  const maxScore = game.maxScore || 1
  const bestScore = Math.min(gameProgress.bestScore || 0, maxScore)
  return Math.round(game.points * (bestScore / maxScore))
}

export function getStats(progress) {
  const completedGameIds = Object.keys(progress?.games || {}).filter(
    (gameId) => progress.games[gameId]?.completed,
  )
  const points = games.reduce((total, game) => total + getGamePoints(game, progress?.games?.[game.id]), 0)
  const totalMissions = games.length
  const completedMissions = completedGameIds.length
  const learningProgress = totalMissions ? Math.round((completedMissions / totalMissions) * 100) : 0

  return {
    points,
    completedGameIds,
    completedMissions,
    totalMissions,
    level: getLevel(points),
    learningProgress,
  }
}

export function getModuleProgress(module, progress) {
  const moduleGames = module.gameIds
    .map((gameId) => games.find((game) => game.id === gameId))
    .filter(Boolean)
  const completed = moduleGames.filter((game) => progress?.games?.[game.id]?.completed).length
  const percent = moduleGames.length ? Math.round((completed / moduleGames.length) * 100) : 0
  const previousModules = learningModules.slice(0, learningModules.findIndex((item) => item.id === module.id))
  const isLocked = previousModules.some((previousModule) => getModuleProgress(previousModule, progress).percent < 100)

  return {
    games: moduleGames,
    completed,
    total: moduleGames.length,
    percent,
    status: isLocked ? 'Locked' : percent === 100 ? 'Completed' : percent > 0 ? 'In Progress' : 'Not started',
  }
}

export function getBadges(progress) {
  const stats = getStats(progress)
  const completed = new Set(stats.completedGameIds)
  const badges = []

  if (stats.completedMissions >= 1) badges.push({ id: 'first-mission', label: 'First Mission Completed' })
  if (completed.has('prompt-quality-quiz')) badges.push({ id: 'prompt-beginner', label: 'Prompt Beginner' })
  if (completed.has('compliance-check-challenge')) badges.push({ id: 'compliance-aware', label: 'Compliance Aware' })
  if (stats.completedMissions >= 2) badges.push({ id: 'finance-ai-explorer', label: 'Finance AI Explorer' })

  return badges
}

export function getNextMission(progress) {
  return games.find((game) => !progress?.games?.[game.id]?.completed) || games[0]
}
