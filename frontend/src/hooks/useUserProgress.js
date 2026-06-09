import { useEffect, useMemo, useState } from 'react'
import {
  PROGRESS_EVENT,
  getNextMission,
  getUserId,
  getUserProgress,
} from '../services/progressService'

export function useUserProgress(user) {
  const userId = useMemo(() => getUserId(user), [user])
  const [progress, setProgress] = useState(() => getUserProgress(userId))

  useEffect(() => {
    const refresh = () => setProgress(getUserProgress(userId))
    refresh()
    window.addEventListener(PROGRESS_EVENT, refresh)
    window.addEventListener('storage', refresh)

    return () => {
      window.removeEventListener(PROGRESS_EVENT, refresh)
      window.removeEventListener('storage', refresh)
    }
  }, [userId])

  return {
    userId,
    progress,
    nextMission: getNextMission(userId),
  }
}
