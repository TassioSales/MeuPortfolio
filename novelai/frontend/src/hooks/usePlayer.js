import { useEffect, useRef, useCallback } from 'react'
import { updateHistorico } from '../lib/api'
import { useAuthStore } from '../store/authStore'

export function usePlayer(episodeId) {
  const token = useAuthStore((s) => s.token)
  const saveIntervalRef = useRef(null)
  const lastPositionRef = useRef(0)

  const startSaving = useCallback(
    (getPosition) => {
      if (!token || !episodeId) return
      saveIntervalRef.current = setInterval(async () => {
        const pos = getPosition()
        if (pos !== lastPositionRef.current && pos > 0) {
          lastPositionRef.current = pos
          try {
            await updateHistorico(episodeId, Math.floor(pos))
          } catch {
            // silent
          }
        }
      }, 10000) // Salva a cada 10s
    },
    [token, episodeId]
  )

  const stopSaving = useCallback(() => {
    if (saveIntervalRef.current) {
      clearInterval(saveIntervalRef.current)
      saveIntervalRef.current = null
    }
  }, [])

  useEffect(() => {
    return () => stopSaving()
  }, [stopSaving])

  return { startSaving, stopSaving }
}
