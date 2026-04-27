import { useState, useEffect, useCallback } from 'react'
import { X, RefreshCw, AlertTriangle, Clock, MessageSquare, Mic, Zap, Server, BarChart2, History, LogOut } from 'lucide-react'
import { useMetrics, type AllTimeMetrics } from '../context/MetricsContext'
import { getDashboardStats, type DashboardResponse } from '../api'

interface AdminDashboardProps {
  onClose: () => void
}

// ── helpers ──────────────────────────────────────────────────────────────────

function avg(arr: number[]) {
  if (!arr.length) return 0
  return Math.round(arr.reduce((a, b) => a + b, 0) / arr.length)
}

function msToSecs(ms: number) {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`
}

function formatDuration(startDate: Date) {
  const diffMs = Date.now() - startDate.getTime()
  const totalSecs = Math.floor(diffMs / 1000)
  const mins = Math.floor(totalSecs / 60)
  const secs = totalSecs % 60
  return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`
}

function StatCard({
  icon,
  label,
  value,
  sub,
  accent = false,
}: {
  icon: React.ReactNode
  label: string
  value: string | number
  sub?: string
  accent?: boolean
}) {
  return (
    <div className={`rounded-xl p-4 flex items-start gap-3 ${accent ? 'bg-red-50 border border-red-200' : 'bg-white/60 border border-teal-100'}`}>
      <span className={`mt-0.5 ${accent ? 'text-red-500' : 'text-teal-600'}`}>{icon}</span>
      <div>
        <p className="text-xs text-teal-700/60 font-medium uppercase tracking-wide">{label}</p>
        <p className={`text-xl font-bold ${accent ? 'text-red-600' : 'text-teal-900'}`}>{value}</p>
        {sub && <p className="text-xs text-teal-700/50 mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}

function MiniBar({ label, value, max, color = 'bg-teal-500' }: { label: string; value: number; max: number; color?: string }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0
  return (
    <div className="flex items-center gap-2 text-xs text-teal-800">
      <span className="w-32 truncate">{label}</span>
      <div className="flex-1 h-2 bg-teal-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-8 text-right font-mono font-semibold">{value}</span>
    </div>
  )
}

// ── All Sessions panel ────────────────────────────────────────────────────────

function AllSessionsPanel({ allTime, onReset }: { allTime: AllTimeMetrics; onReset: () => void }) {
  const rt = allTime.responseTimes
  const avgMs = rt.count > 0 ? Math.round(rt.sumMs / rt.count) : 0
  const catEntries = Object.entries(allTime.categoryCountsAllTime).sort((a, b) => b[1] - a[1])
  const maxCat = catEntries.length ? catEntries[0][1] : 1
  const firstDate = new Date(allTime.firstRecordedAt)
  const lastDate = new Date(allTime.lastUpdatedAt)
  const resourceEntries = Object.entries(allTime.resourceClicksAllTime ?? {}).sort((a, b) => b[1] - a[1])
  const maxResourceCount = resourceEntries.length ? resourceEntries[0][1] : 1

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold text-teal-800 uppercase tracking-widest flex items-center gap-1.5">
          <History size={14} /> All Sessions
        </h3>
        <button
          onClick={onReset}
          className="text-xs text-red-400 hover:text-red-600 hover:underline"
        >
          Clear history
        </button>
      </div>

      {/* Core stats */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <StatCard icon={<MessageSquare size={18} />} label="Total Sessions" value={allTime.totalSessions} sub={`first: ${firstDate.toLocaleDateString()}`} />
        <StatCard icon={<MessageSquare size={18} />} label="Total Messages" value={allTime.totalUserMessages + allTime.totalAiMessages} sub={`${allTime.totalUserMessages} sent · ${allTime.totalAiMessages} received`} />
        <StatCard icon={<Mic size={18} />} label="Voice Messages" value={allTime.totalVoiceMessages} />
        <StatCard icon={<AlertTriangle size={18} />} label="Crisis Detections" value={allTime.totalCrisisDetections} accent={allTime.totalCrisisDetections > 0} sub={allTime.totalErrors > 0 ? `${allTime.totalErrors} error(s)` : undefined} />
      </div>

      {/* New metrics */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <StatCard
          icon={<LogOut size={18} />}
          label="Quick Exits"
          value={allTime.totalQuickExitClicks ?? 0}
          accent={(allTime.totalQuickExitClicks ?? 0) > 0}
        />
        <StatCard
          icon={<MessageSquare size={18} />}
          label="Abandoned Sessions"
          value={allTime.totalAbandonedSessions ?? 0}
          sub="left without messaging"
        />
        {allTime.avgTimeToFirstMessageMs > 0 && (
          <StatCard
            icon={<Clock size={18} />}
            label="Avg Time to First Msg"
            value={msToSecs(allTime.avgTimeToFirstMessageMs)}
            sub={`${allTime.timeToFirstMessageCount} samples`}
          />
        )}
      </div>

      {/* Response times */}
      <div className="bg-white/60 border border-teal-100 rounded-xl p-4 mb-4">
        <p className="text-xs font-bold text-teal-700 uppercase tracking-wide mb-3 flex items-center gap-1.5">
          <Zap size={12} /> Response Times (all sessions · {rt.count} samples)
        </p>
        {rt.count === 0 ? (
          <p className="text-xs text-teal-600/50">No responses recorded yet.</p>
        ) : (
          <div className="grid grid-cols-3 gap-3 text-center">
            {[['Avg', msToSecs(avgMs)], ['Min', msToSecs(rt.minMs)], ['Max', msToSecs(rt.maxMs)]].map(([lbl, val]) => (
              <div key={lbl}>
                <p className="text-lg font-bold text-teal-900">{val}</p>
                <p className="text-xs text-teal-600/60">{lbl}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Categories */}
      {catEntries.length > 0 && (
        <div className="bg-white/60 border border-teal-100 rounded-xl p-4 mb-4">
          <p className="text-xs font-bold text-teal-700 uppercase tracking-wide mb-3">Categories Used (all sessions)</p>
          <div className="space-y-2">
            {catEntries.map(([cat, count]) => (
              <MiniBar key={cat} label={cat.replace(/_/g, ' ')} value={count} max={maxCat} />
            ))}
          </div>
        </div>
      )}

      {/* Resource clicks all time */}
      {resourceEntries.length > 0 && (
        <div className="bg-white/60 border border-teal-100 rounded-xl p-4 mb-4">
          <p className="text-xs font-bold text-teal-700 uppercase tracking-wide mb-3">Resource Clicks (all time)</p>
          <div className="space-y-2">
            {resourceEntries.map(([name, count]) => (
              <MiniBar key={name} label={name} value={count} max={maxResourceCount} />
            ))}
          </div>
        </div>
      )}

      <p className="text-xs text-teal-600/40 text-right">Last updated: {lastDate.toLocaleString()}</p>
    </div>
  )
}

// ── main component ────────────────────────────────────────────────────────────

type Tab = 'session' | 'alltime' | 'backend'

export function AdminDashboard({ onClose }: AdminDashboardProps) {
  const { metrics, allTime, resetMetrics, resetAllTime } = useMetrics()
  const [tab, setTab] = useState<Tab>('session')
  const [backendData, setBackendData] = useState<DashboardResponse | null>(null)
  const [backendError, setBackendError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [, setNow] = useState(new Date())

  // Tick every second so duration stays live
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])

  const fetchBackend = useCallback(async () => {
    setLoading(true)
    setBackendError(null)
    try {
      const data = await getDashboardStats()
      setBackendData(data)
    } catch {
      setBackendError('Could not reach backend. Is the server running?')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchBackend() }, [fetchBackend])

  // ── session-level derived values ──────────────────────────────────────────
  const sessionDuration = formatDuration(metrics.sessionStartTime)
  const avgResponseMs = avg(metrics.responseTimes)
  const minResponseMs = metrics.responseTimes.length ? Math.min(...metrics.responseTimes) : 0
  const maxResponseMs = metrics.responseTimes.length ? Math.max(...metrics.responseTimes) : 0
  const totalSessionMsgs = metrics.userMessageCount + metrics.aiMessageCount
  const catEntries = Object.entries(metrics.categoriesUsed).sort((a, b) => b[1] - a[1])
  const maxCatCount = catEntries.length ? catEntries[0][1] : 1
  const resourceSessionEntries = Object.entries(metrics.resourceClicks).sort((a, b) => b[1] - a[1])
  const maxResourceSession = resourceSessionEntries.length ? resourceSessionEntries[0][1] : 1

  // ── backend derived values ────────────────────────────────────────────────
  const sm = backendData?.server_metrics
  const bs = backendData?.bot_stats
  const backendCatEntries = sm ? Object.entries(sm.category_counts).sort((a, b) => b[1] - a[1]) : []
  const backendMaxCat = backendCatEntries.length ? backendCatEntries[0][1] : 1

  const TAB_STYLES = (active: boolean) =>
    `px-4 py-2 text-xs font-semibold rounded-lg transition-colors ${
      active ? 'bg-teal-700 text-white' : 'text-teal-700 hover:bg-teal-100'
    }`

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-3xl max-h-[90vh] overflow-y-auto bg-[#e8f7f7] rounded-2xl shadow-2xl border border-teal-200">

        {/* Header */}
        <div className="sticky top-0 z-10 bg-[#e8f7f7]/95 backdrop-blur px-6 pt-4 pb-0 border-b border-teal-200">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <BarChart2 className="text-teal-600" size={20} />
              <h2 className="text-lg font-bold text-teal-900">Admin Dashboard</h2>
              <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-amber-100 text-amber-700 border border-amber-200 font-medium">ADMIN ONLY</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={fetchBackend}
                disabled={loading}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-teal-700 bg-teal-100 hover:bg-teal-200 rounded-lg transition-colors disabled:opacity-50"
              >
                <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
                Refresh
              </button>
              <button onClick={onClose} className="p-1.5 text-teal-600 hover:text-teal-900 hover:bg-teal-100 rounded-lg transition-colors">
                <X size={18} />
              </button>
            </div>
          </div>
          {/* Tabs */}
          <div className="flex gap-1 pb-3">
            <button className={TAB_STYLES(tab === 'session')} onClick={() => setTab('session')}>
              Current Session
            </button>
            <button className={TAB_STYLES(tab === 'alltime')} onClick={() => setTab('alltime')}>
              All Sessions
            </button>
            <button className={TAB_STYLES(tab === 'backend')} onClick={() => setTab('backend')}>
              Backend / Server
            </button>
          </div>
        </div>

        <div className="p-6">

          {/* ── Tab: Current Session ──────────────────────────────────── */}
          {tab === 'session' && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-bold text-teal-800 uppercase tracking-widest">Current Session</h3>
                <button onClick={resetMetrics} className="text-xs text-teal-500 hover:text-teal-700 hover:underline">Reset</button>
              </div>

              {/* Core stats */}
              <div className="grid grid-cols-2 gap-3 mb-4">
                <StatCard icon={<Clock size={18} />} label="Duration" value={sessionDuration} sub={`started ${metrics.sessionStartTime.toLocaleTimeString()}`} />
                <StatCard icon={<MessageSquare size={18} />} label="Total Messages" value={totalSessionMsgs} sub={`${metrics.userMessageCount} sent · ${metrics.aiMessageCount} received`} />
                <StatCard icon={<Mic size={18} />} label="Voice Messages" value={metrics.voiceMessageCount} />
                <StatCard icon={<AlertTriangle size={18} />} label="Crisis Detections" value={metrics.crisisDetections} accent={metrics.crisisDetections > 0} sub={metrics.errorCount > 0 ? `${metrics.errorCount} error(s)` : undefined} />
                <StatCard
                  icon={<LogOut size={18} />}
                  label="Quick Exits"
                  value={metrics.quickExitClicks}
                  accent={metrics.quickExitClicks > 0}
                />
                {metrics.timeToFirstMessageMs !== null && (
                  <StatCard
                    icon={<Clock size={18} />}
                    label="Time to First Msg"
                    value={msToSecs(metrics.timeToFirstMessageMs)}
                    sub="from session start"
                  />
                )}
              </div>

              {/* Response times */}
              <div className="bg-white/60 border border-teal-100 rounded-xl p-4 mb-4">
                <p className="text-xs font-bold text-teal-700 uppercase tracking-wide mb-3 flex items-center gap-1.5">
                  <Zap size={12} /> Response Times (this session)
                </p>
                {metrics.responseTimes.length === 0 ? (
                  <p className="text-xs text-teal-600/50">No responses recorded yet.</p>
                ) : (
                  <div className="grid grid-cols-3 gap-3 text-center">
                    {[['Avg', msToSecs(avgResponseMs)], ['Min', msToSecs(minResponseMs)], ['Max', msToSecs(maxResponseMs)]].map(([lbl, val]) => (
                      <div key={lbl}>
                        <p className="text-lg font-bold text-teal-900">{val}</p>
                        <p className="text-xs text-teal-600/60">{lbl}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Categories */}
              {catEntries.length > 0 && (
                <div className="bg-white/60 border border-teal-100 rounded-xl p-4 mb-4">
                  <p className="text-xs font-bold text-teal-700 uppercase tracking-wide mb-3">Categories Used (session)</p>
                  <div className="space-y-2">
                    {catEntries.map(([cat, count]) => (
                      <MiniBar key={cat} label={cat.replace(/_/g, ' ')} value={count} max={maxCatCount} />
                    ))}
                  </div>
                </div>
              )}

              {/* Resource clicks session */}
              {resourceSessionEntries.length > 0 && (
                <div className="bg-white/60 border border-teal-100 rounded-xl p-4">
                  <p className="text-xs font-bold text-teal-700 uppercase tracking-wide mb-3">Resource Clicks (session)</p>
                  <div className="space-y-2">
                    {resourceSessionEntries.map(([name, count]) => (
                      <MiniBar key={name} label={name} value={count} max={maxResourceSession} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ── Tab: All Sessions ─────────────────────────────────────── */}
          {tab === 'alltime' && (
            <AllSessionsPanel allTime={allTime} onReset={resetAllTime} />
          )}

          {/* ── Tab: Backend / Server ─────────────────────────────────── */}
          {tab === 'backend' && (
            <div>
              <h3 className="text-sm font-bold text-teal-800 uppercase tracking-widest mb-3">Backend / Server</h3>

              {backendError && (
                <div className="mb-4 px-4 py-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 flex items-start gap-2">
                  <AlertTriangle size={14} className="mt-0.5 shrink-0" />
                  {backendError}
                </div>
              )}

              {sm && (
                <>
                  <div className="grid grid-cols-2 gap-3 mb-4">
                    <StatCard icon={<Server size={18} />} label="Total Requests" value={sm.total_requests} sub={`since ${new Date(sm.server_start_time).toLocaleTimeString()}`} />
                    <StatCard icon={<AlertTriangle size={18} />} label="Crisis Rate" value={`${sm.crisis_rate}%`} accent={sm.crisis_rate > 10} sub={`${sm.total_crisis_events} event(s)`} />
                    <StatCard icon={<Mic size={18} />} label="Voice Requests" value={sm.voice_requests} />
                    <StatCard icon={<Zap size={18} />} label="Error Rate" value={`${sm.error_rate}%`} accent={sm.error_rate > 5} sub={`${sm.total_errors} error(s)`} />
                  </div>

                  <div className="bg-white/60 border border-teal-100 rounded-xl p-4 mb-4">
                    <p className="text-xs font-bold text-teal-700 uppercase tracking-wide mb-3 flex items-center gap-1.5">
                      <Zap size={12} /> Backend Response Times ({sm.response_times.count} samples)
                    </p>
                    {sm.response_times.count === 0 ? (
                      <p className="text-xs text-teal-600/50">No data yet.</p>
                    ) : (
                      <div className="grid grid-cols-4 gap-2 text-center">
                        {[
                          ['Avg', msToSecs(sm.response_times.avg_ms)],
                          ['Min', msToSecs(sm.response_times.min_ms)],
                          ['Max', msToSecs(sm.response_times.max_ms)],
                          ['p95', sm.response_times.p95_ms != null ? msToSecs(sm.response_times.p95_ms) : '—'],
                        ].map(([lbl, val]) => (
                          <div key={lbl}>
                            <p className="text-base font-bold text-teal-900">{val}</p>
                            <p className="text-xs text-teal-600/60">{lbl}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {backendCatEntries.length > 0 && (
                    <div className="bg-white/60 border border-teal-100 rounded-xl p-4 mb-4">
                      <p className="text-xs font-bold text-teal-700 uppercase tracking-wide mb-3">Category Distribution (server lifetime)</p>
                      <div className="space-y-2">
                        {backendCatEntries.map(([cat, count]) => (
                          <MiniBar key={cat} label={cat.replace(/_/g, ' ')} value={count} max={backendMaxCat} />
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}

              {bs && (
                <div className="bg-white/60 border border-teal-100 rounded-xl p-4">
                  <p className="text-xs font-bold text-teal-700 uppercase tracking-wide mb-3">Bot Configuration</p>
                  <div className="space-y-1.5 text-xs text-teal-800">
                    {[
                      ['LLM model', bs.llm_model],
                      ['Vector docs', bs.vector_store?.document_count ?? '—'],
                      ['Retriever top-k', bs.retriever_top_k],
                      ['Crisis keywords', bs.crisis_keywords],
                      ...(sm ? [['Avg docs retrieved', sm.docs_retrieved.avg]] : []),
                    ].map(([label, value]) => (
                      <div key={String(label)} className="flex justify-between">
                        <span className="text-teal-600">{label}</span>
                        <span className="font-mono font-semibold">{value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {!backendData && !backendError && loading && (
                <div className="flex items-center justify-center h-40 text-teal-500 text-sm animate-pulse">
                  Loading backend data…
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer note */}
        <div className="px-6 py-3 border-t border-teal-200 text-xs text-teal-600/50 text-center">
          Admin only — restrict access by role before production deployment.
        </div>
      </div>
    </div>
  )
}