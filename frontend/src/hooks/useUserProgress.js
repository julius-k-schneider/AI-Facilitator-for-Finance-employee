import { useCallback, useEffect, useMemo, useState } from 'react'
import { games, getGameById } from '../data/games'
import { getBadges, getStats } from '../utils/progressUtils'

function createDefaultProgress() {
  return {
    games: {},
    activity: [],
    lastActivity: null,
  }
}

function getStorageKey(user) {
  return `ai-facilitator-progress:${user?.id || user?.username || 'guest'}`
}

function readStoredProgress(storageKey, user) {
  if (!user) return createDefaultProgress()

  try {
    const stored = window.localStorage.getItem(storageKey)
    return stored ? { ...createDefaultProgress(), ...JSON.parse(stored) } : createDefaultProgress()
  } catch {
    return createDefaultProgress()
  }
}

export function useUserProgress(user) {
  const storageKey = useMemo(() => getStorageKey(user), [user])
  const [progressByKey, setProgressByKey] = useState({})
  const progress = progressByKey[storageKey] || readStoredProgress(storageKey, user)

  useEffect(() => {
    if (!user) return
    window.localStorage.setItem(storageKey, JSON.stringify(progress))
  }, [progress, storageKey, user])

  const completeGame = useCallback((gameId, score) => {
    const game = getGameById(gameId)
    if (!game) return

    setProgressByKey((currentByKey) => {
      const current = currentByKey[storageKey] || readStoredProgress(storageKey, user)
      const previous = current.games?.[gameId] || {}
      const maxScore = game.maxScore || 1
      const normalizedScore = Math.max(0, Math.min(score, maxScore))
      const bestScore = Math.max(previous.bestScore || 0, normalizedScore)
      const completed = previous.completed || normalizedScore >= game.passScore

      // Total points are derived from the best saved score per game, so replays never duplicate points.
      return {
        ...currentByKey,
        [storageKey]: {
        ...current,
        games: {
          ...current.games,
          [gameId]: {
            completed,
            bestScore,
            maxScore,
            attempts: (previous.attempts || 0) + 1,
            lastScore: normalizedScore,
            completedAt: completed ? previous.completedAt || new Date().toISOString() : previous.completedAt,
            lastPlayedAt: new Date().toISOString(),
          },
        },
        activity: [
          ...(current.activity || []),
          {
            gameId,
            score: normalizedScore,
            points: completed ? Math.round(game.points * (bestScore / maxScore)) : 0,
            date: new Date().toISOString(),
          },
        ].slice(-20),
        lastActivity: new Date().toISOString(),
        },
      }
    })
  }, [storageKey, user])

  const resetProgress = useCallback(() => {
    setProgressByKey((currentByKey) => ({
      ...currentByKey,
      [storageKey]: createDefaultProgress(),
    }))
  }, [storageKey])

  const stats = useMemo(() => getStats(progress), [progress])
  const badges = useMemo(() => getBadges(progress), [progress])
  const completedGames = useMemo(
    () => games.filter((game) => progress.games?.[game.id]?.completed),
    [progress],
  )

  return {
    progress,
    stats,
    badges,
    completedGames,
    completeGame,
    resetProgress,
  }
}
