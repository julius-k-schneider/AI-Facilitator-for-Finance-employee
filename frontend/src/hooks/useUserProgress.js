import { useEffect, useMemo, useState } from 'react'
import {
  EMPTY_PROGRESS,
  PROGRESS_EVENT,
  getUserId,
  getUserProgress,
} from '../services/progressService'

export function useUserProgress(user) {
  const userId = useMemo(() => getUserId(user), [user])
  const [progress, setProgress] = useState(EMPTY_PROGRESS)
  const [loading, setLoading] = useState(Boolean(userId))
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    const refresh = (event) => {
      if (event?.detail) {
        setProgress(event.detail)
        return
      }
      if (!userId) return
      setLoading(true)
      getUserProgress()
        .then((nextProgress) => {
          if (active) {
            setProgress(nextProgress)
            setError('')
          }
        })
        .catch((nextError) => {
          if (active) setError(nextError.message)
        })
        .finally(() => {
          if (active) setLoading(false)
        })
    }

    refresh()
    window.addEventListener(PROGRESS_EVENT, refresh)
    return () => {
      active = false
      window.removeEventListener(PROGRESS_EVENT, refresh)
    }
  }, [userId])

  return { userId, progress, loading, error }
}
