import { createContext, useContext, useState, useEffect, useRef, type ReactNode } from 'react'
import { supabase } from '../lib/supabase'

export interface SessionMetrics {
  sessionStartTime: Date
  userMessageCount: number
  aiMessageCount: number
  quickExitClicks: number
  resourceClicks: Record<string, number>
  timeToFirstMessageMs: number | null
  voiceMessageCount: number
  responseTimes: number[]
  crisisDetections: number
  errorCount: number
  categoriesUsed: Record<string, number>
}

export interface AllTimeMetrics {
  totalSessions: number
  totalUserMessages: number
  totalAiMessages: number
  totalVoiceMessages: number
  totalCrisisDetections: number
  totalQuickExitClicks: number
  totalAbandonedSessions: number
  resourceClicksAllTime: Record<string, number>
  avgTimeToFirstMessageMs: number
  timeToFirstMessageCount: number
  totalErrors: number
  responseTimes: {
    count: number
    sumMs: number
    minMs: number
    maxMs: number
  }
  categoryCountsAllTime: Record<string, number>
  firstRecordedAt: string
  lastUpdatedAt: string
}

const STORAGE_KEY = 'care-compass-metrics-alltime'

function defaultAllTime(): AllTimeMetrics {
  const now = new Date().toISOString()
  return {
    totalSessions: 0,
    totalUserMessages: 0,
    totalAiMessages: 0,
    totalVoiceMessages: 0,
    totalCrisisDetections: 0,
    totalErrors: 0,
    totalQuickExitClicks: 0,
    totalAbandonedSessions: 0,
    resourceClicksAllTime: {},
    avgTimeToFirstMessageMs: 0,
    timeToFirstMessageCount: 0,
    responseTimes: { count: 0, sumMs: 0, minMs: Infinity, maxMs: 0 },
    categoryCountsAllTime: {},
    firstRecordedAt: now,
    lastUpdatedAt: now,
  }
}

function loadAllTime(): AllTimeMetrics {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return defaultAllTime()
    const parsed = JSON.parse(raw) as AllTimeMetrics
    if (parsed.responseTimes.minMs === null || parsed.responseTimes.minMs === undefined) {
      parsed.responseTimes.minMs = Infinity
    }
    return parsed
  } catch {
    return defaultAllTime()
  }
}

function saveAllTime(m: AllTimeMetrics) {
  try {
    const copy = { ...m, responseTimes: { ...m.responseTimes } }
    if (!isFinite(copy.responseTimes.minMs)) copy.responseTimes.minMs = 0
    localStorage.setItem(STORAGE_KEY, JSON.stringify(copy))
  } catch {
    // storage quota exceeded — silently ignore
  }
}

interface MetricsContextType {
  metrics: SessionMetrics
  allTime: AllTimeMetrics
  recordTextResponse: (responseTimeMs: number, isCrisis: boolean, scenario?: string, isError?: boolean) => void
  recordVoiceResponse: (responseTimeMs: number, isCrisis: boolean) => void
  recordQuickExit: () => void
  recordResourceClick: (resourceName: string) => void
  recordTimeToFirstMessage: (ms: number) => void
  resetMetrics: () => void
  resetAllTime: () => void
}

function defaultMetrics(): SessionMetrics {
  return {
    sessionStartTime: new Date(),
    userMessageCount: 0,
    aiMessageCount: 0,
    voiceMessageCount: 0,
    responseTimes: [],
    crisisDetections: 0,
    errorCount: 0,
    categoriesUsed: {},
    quickExitClicks: 0,
    resourceClicks: {},
    timeToFirstMessageMs: null,
  }
}

const MetricsContext = createContext<MetricsContextType | null>(null)

interface MetricsProviderProps {
  children: ReactNode
  sessionId: string
  userType: 'guest' | 'email'
  userEmail?: string
}

export function MetricsProvider({ children, sessionId, userType, userEmail }: MetricsProviderProps) {
  const [metrics, setMetrics] = useState<SessionMetrics>(defaultMetrics)
  const [allTime, setAllTime] = useState<AllTimeMetrics>(() => {
    const loaded = loadAllTime()
    const updated = {
      ...loaded,
      totalSessions: loaded.totalSessions + 1,
      lastUpdatedAt: new Date().toISOString(),
    }
    saveAllTime(updated)
    return updated
  })

  // Refs so cleanup useEffect always sees latest values without stale closures
  const metricsRef = useRef(metrics)
  const sessionIdRef = useRef(sessionId)
  const userTypeRef = useRef(userType)
  const userEmailRef = useRef(userEmail)

  useEffect(() => { metricsRef.current = metrics }, [metrics])
  useEffect(() => { sessionIdRef.current = sessionId }, [sessionId])
  useEffect(() => { userTypeRef.current = userType }, [userType])
  useEffect(() => { userEmailRef.current = userEmail }, [userEmail])

  // Flush session to Supabase + update local allTime on unmount
  useEffect(() => {
    return () => {
      const m = metricsRef.current
      const endTime = new Date()
      const durationMs = endTime.getTime() - m.sessionStartTime.getTime()
      const wasAbandoned = m.userMessageCount === 0
      const avgResponseMs = m.responseTimes.length > 0
        ? Math.round(m.responseTimes.reduce((a, b) => a + b, 0) / m.responseTimes.length)
        : null

      // Push to Supabase — fire and forget, won't block UI
      supabase.from('session_analytics').insert({
        session_id: sessionIdRef.current,
        user_type: userTypeRef.current,
        user_email: userEmailRef.current ?? null,
        session_start: m.sessionStartTime.toISOString(),
        session_end: endTime.toISOString(),
        duration_ms: durationMs,
        message_count: m.userMessageCount,
        voice_message_count: m.voiceMessageCount,
        crisis_detections: m.crisisDetections,
        quick_exits: m.quickExitClicks,
        time_to_first_message_ms: m.timeToFirstMessageMs,
        abandoned: wasAbandoned,
        categories_used: m.categoriesUsed,
        resource_clicks: m.resourceClicks,
        avg_response_ms: avgResponseMs,
        error_count: m.errorCount,
      }).then(({ error }) => {
        if (error) {
          console.warn('[Metrics] Failed to flush to Supabase:', error.message)
        }
      })

      // Update local allTime storage
      setAllTime((prev) => {
        const next = {
          ...prev,
          totalAbandonedSessions: wasAbandoned
            ? (prev.totalAbandonedSessions ?? 0) + 1
            : prev.totalAbandonedSessions,
          lastUpdatedAt: new Date().toISOString(),
        }
        saveAllTime(next)
        return next
      })
    }
  }, [])

  function updateAllTime(updater: (prev: AllTimeMetrics) => AllTimeMetrics) {
    setAllTime((prev) => {
      const next = updater(prev)
      saveAllTime(next)
      return next
    })
  }

  const recordTextResponse = (
    responseTimeMs: number,
    isCrisis: boolean,
    scenario?: string,
    isError = false,
  ) => {
    setMetrics((prev) => ({
      ...prev,
      userMessageCount: prev.userMessageCount + 1,
      aiMessageCount: isError ? prev.aiMessageCount : prev.aiMessageCount + 1,
      errorCount: isError ? prev.errorCount + 1 : prev.errorCount,
      crisisDetections: isCrisis ? prev.crisisDetections + 1 : prev.crisisDetections,
      responseTimes: isError ? prev.responseTimes : [...prev.responseTimes, responseTimeMs],
      categoriesUsed: scenario
        ? { ...prev.categoriesUsed, [scenario]: (prev.categoriesUsed[scenario] ?? 0) + 1 }
        : prev.categoriesUsed,
    }))

    updateAllTime((prev) => ({
      ...prev,
      totalUserMessages: prev.totalUserMessages + 1,
      totalAiMessages: isError ? prev.totalAiMessages : prev.totalAiMessages + 1,
      totalErrors: isError ? prev.totalErrors + 1 : prev.totalErrors,
      totalCrisisDetections: isCrisis ? prev.totalCrisisDetections + 1 : prev.totalCrisisDetections,
      responseTimes: isError ? prev.responseTimes : {
        count: prev.responseTimes.count + 1,
        sumMs: prev.responseTimes.sumMs + responseTimeMs,
        minMs: Math.min(prev.responseTimes.minMs, responseTimeMs),
        maxMs: Math.max(prev.responseTimes.maxMs, responseTimeMs),
      },
      categoryCountsAllTime: scenario
        ? { ...prev.categoryCountsAllTime, [scenario]: (prev.categoryCountsAllTime[scenario] ?? 0) + 1 }
        : prev.categoryCountsAllTime,
      lastUpdatedAt: new Date().toISOString(),
    }))
  }

  const recordVoiceResponse = (responseTimeMs: number, isCrisis: boolean) => {
    setMetrics((prev) => ({
      ...prev,
      userMessageCount: prev.userMessageCount + 1,
      aiMessageCount: prev.aiMessageCount + 1,
      voiceMessageCount: prev.voiceMessageCount + 1,
      crisisDetections: isCrisis ? prev.crisisDetections + 1 : prev.crisisDetections,
      responseTimes: [...prev.responseTimes, responseTimeMs],
    }))

    updateAllTime((prev) => ({
      ...prev,
      totalUserMessages: prev.totalUserMessages + 1,
      totalAiMessages: prev.totalAiMessages + 1,
      totalVoiceMessages: prev.totalVoiceMessages + 1,
      totalCrisisDetections: isCrisis ? prev.totalCrisisDetections + 1 : prev.totalCrisisDetections,
      responseTimes: {
        count: prev.responseTimes.count + 1,
        sumMs: prev.responseTimes.sumMs + responseTimeMs,
        minMs: Math.min(prev.responseTimes.minMs, responseTimeMs),
        maxMs: Math.max(prev.responseTimes.maxMs, responseTimeMs),
      },
      lastUpdatedAt: new Date().toISOString(),
    }))
  }

  const recordQuickExit = () => {
    setMetrics(prev => ({ ...prev, quickExitClicks: prev.quickExitClicks + 1 }))
    updateAllTime(prev => ({
      ...prev,
      totalQuickExitClicks: (prev.totalQuickExitClicks ?? 0) + 1,
      lastUpdatedAt: new Date().toISOString(),
    }))
  }

  const recordResourceClick = (resourceName: string) => {
    setMetrics(prev => ({
      ...prev,
      resourceClicks: {
        ...prev.resourceClicks,
        [resourceName]: (prev.resourceClicks[resourceName] ?? 0) + 1,
      },
    }))
    updateAllTime(prev => ({
      ...prev,
      resourceClicksAllTime: {
        ...prev.resourceClicksAllTime,
        [resourceName]: (prev.resourceClicksAllTime[resourceName] ?? 0) + 1,
      },
      lastUpdatedAt: new Date().toISOString(),
    }))
  }

  const recordTimeToFirstMessage = (ms: number) => {
    setMetrics(prev => ({
      ...prev,
      timeToFirstMessageMs: prev.timeToFirstMessageMs ?? ms,
    }))
    updateAllTime(prev => {
      const count = prev.timeToFirstMessageCount + 1
      const avg = Math.round(
        (prev.avgTimeToFirstMessageMs * prev.timeToFirstMessageCount + ms) / count
      )
      return {
        ...prev,
        avgTimeToFirstMessageMs: avg,
        timeToFirstMessageCount: count,
        lastUpdatedAt: new Date().toISOString(),
      }
    })
  }

  const resetMetrics = () => setMetrics(defaultMetrics())

  const resetAllTime = () => {
    const fresh = defaultAllTime()
    saveAllTime(fresh)
    setAllTime(fresh)
  }

  return (
    <MetricsContext.Provider value={{
      metrics,
      allTime,
      recordTextResponse,
      recordVoiceResponse,
      recordQuickExit,
      recordResourceClick,
      recordTimeToFirstMessage,
      resetMetrics,
      resetAllTime,
    }}>
      {children}
    </MetricsContext.Provider>
  )
}

export function useMetrics(): MetricsContextType {
  const ctx = useContext(MetricsContext)
  if (!ctx) throw new Error('useMetrics must be used within a MetricsProvider')
  return ctx
}