import { useMemo } from 'react'
import { demoUsers } from '../data/demoUsers'
import { getLevel, getRole, getUserDisplayName } from '../utils/progressUtils'

export function useLeaderboard(user, stats) {
  return useMemo(() => {
    const currentUser = {
      id: `current-${user?.id || user?.username || 'guest'}`,
      name: getUserDisplayName(user),
      role: getRole(user),
      points: stats.points,
      completedMissions: stats.completedMissions,
      level: stats.level,
      isCurrentUser: true,
    }

    return [...demoUsers, currentUser]
      .map((entry) => ({
        ...entry,
        level: entry.level || getLevel(entry.points),
      }))
      .sort((a, b) => b.points - a.points || b.completedMissions - a.completedMissions)
      .map((entry, index) => ({ ...entry, rank: index + 1 }))
  }, [stats, user])
}
