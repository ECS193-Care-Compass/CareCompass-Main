import { createContext, useContext, useState, useEffect, useRef, type ReactNode } from 'react'

export interface SessionMetrics {
  sessionStartTime: Date
  userMessageCount: number
  aiMessageCount: number
  voiceMessageCount: number
  /** Response time per request in milliseconds */
  responseTimes: number[]
  crisisDetections: number
  errorCount: number
  /** Map of scenario category → how many times used */
  categoriesUsed: Record<string, number>
}

// Stored in localStorage — no full arrays, just aggregated numbers
export interface AllTimeMetrics {
  totalSessions: number
  totalUserMessages: number
  totalAiMessages: number
  totalVoiceMessages: number
  totalCrisisDetections: number
  totalErrors: number
  responseTimes: {
    count: number
    sumMs: number
    minMs: number
    maxMs: number
  }
  categoryCountsAllTime: Record<string, number>
  firstRecordedAt: string  // ISO string
  lastUpdatedAt: string    // ISO string
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
    // Guard against stored Infinity (serialised as null by JSON)
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
    // Replace Infinity with a sentinal that survives JSON round-trip
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
  }
}

const MetricsContext = createContext<MetricsContextType | null>(null)

export function MetricsProvider({ children }: { children: ReactNode }) {
  const [metrics, setMetrics] = useState<SessionMetrics>(defaultMetrics)
  const [allTime, setAllTime] = useState<AllTimeMetrics>(() => {
    const loaded = loadAllTime()
    // Increment session count on mount
    const updated = { ...loaded, totalSessions: loaded.totalSessions + 1, lastUpdatedAt: new Date().toISOString() }
    saveAllTime(updated)
    return updated
  })

  // Keep a ref so the update functions always see the latest allTime without stale closures
  const allTimeRef = useRef(allTime)
  useEffect(() => { allTimeRef.current = allTime }, [allTime])

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

  const resetMetrics = () => setMetrics(defaultMetrics())

  const resetAllTime = () => {
    const fresh = defaultAllTime()
    saveAllTime(fresh)
    setAllTime(fresh)
  }

  return (
    <MetricsContext.Provider value={{ metrics, allTime, recordTextResponse, recordVoiceResponse, resetMetrics, resetAllTime }}>
      {children}
    </MetricsContext.Provider>
  )
}

export function useMetrics(): MetricsContextType {
  const ctx = useContext(MetricsContext)
  if (!ctx) throw new Error('useMetrics must be used within a MetricsProvider')
  return ctx
}
