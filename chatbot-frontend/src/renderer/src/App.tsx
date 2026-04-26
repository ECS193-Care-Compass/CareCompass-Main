import type { JSX } from 'react'
import { useState } from 'react'
import { WelcomeGlowBox } from './components/WelcomeGlowBox'
import { QuickExitBar } from './components/QuickExitBar'
import { ResourcesSection } from './components/ResourcesSection'
import { AuthScreen } from './components/AuthScreen'
import { AdminDashboard } from './components/AdminDashboard'
import { MetricsProvider } from './context/MetricsContext'
import { useAuth } from './hooks/useAuth'
import { BarChart2 } from 'lucide-react'

export default function App(): JSX.Element {
  const { 
    user, sessionId, isGuest, isLoading, 
    signInWithEmail, signUpWithEmail, signOut, 
    continueAsGuest, getAuthHeader,
    guestTimeLeft, showWarning, formatTime
  } = useAuth()
  const [showDashboard, setShowDashboard] = useState(false)

  if (isLoading) {
    return (
      <div className="w-full bg-[#a1d7d6] font-sans text-teal-950 flex items-center justify-center min-h-screen">
        <p className="text-teal-800/70 animate-pulse">Loading...</p>
      </div>
    )
  }

  if (!user && !isGuest) {
    return (
      <div className="w-full min-h-screen bg-[#a1d7d6] font-sans text-teal-950">
        <AuthScreen
          onSignIn={signInWithEmail}
          onSignUp={signUpWithEmail}
          onGuest={continueAsGuest}
        />
      </div>
    )
  }

  return (
    <MetricsProvider>
      <div className="w-full bg-[#a1d7d6] font-sans text-teal-950 overflow-x-hidden">
        <QuickExitBar
          onSignOut={signOut}
          showSignOut={!isGuest}
          guestTimeLeft={guestTimeLeft}
          showWarning={showWarning}
          formatTime={formatTime}
        />
        <section className="pt-12 sm:pt-14 relative flex flex-col items-center justify-center min-h-screen w-full overflow-hidden px-2 sm:px-4">
          <WelcomeGlowBox sessionId={sessionId} authToken={getAuthHeader()} />
        </section>
        <div className="flex justify-center -mt-8 sm:-mt-20 mb-7 pointer-events-none">
          <div className="flex flex-col items-center animate-pulse text-teal-900/60 max-w-5xl w-full px-6 pointer-events-none">
            <span className="text-xs font-bold tracking-widest uppercase mb-2">Scroll for Resources</span>
            <div className="w-px h-8 sm:h-12 bg-gradient-to-b from-teal-900/60 to-transparent"></div>
          </div>
        </div>
        <section className="w-full py-12 sm:py-24 bg-white border-t border-gray-100">
          <div className="max-w-5xl mx-auto px-4 sm:px-6">
            <ResourcesSection />
          </div>
        </section>

        {/* Debug dashboard toggle — bottom-right corner */}
        <button
          onClick={() => setShowDashboard(true)}
          className="fixed bottom-4 right-4 z-40 flex items-center gap-2 px-3 py-2 bg-teal-800/90 text-white text-xs font-medium rounded-full shadow-lg hover:bg-teal-700 transition-colors backdrop-blur-sm"
          title="Open admin dashboard"
        >
          <BarChart2 size={14} />
          Dashboard
        </button>

        {showDashboard && <AdminDashboard onClose={() => setShowDashboard(false)} />}
      </div>
    </MetricsProvider>
  )
}