import type { JSX } from 'react'
import { WelcomeGlowBox } from './components/WelcomeGlowBox'
import { QuickExitBar } from './components/QuickExitBar'
import { ResourcesSection } from './components/ResourcesSection'
<<<<<<< HEAD
=======
import { AuthScreen } from './components/AuthScreen'
import { useAuth } from './hooks/useAuth'

export default function App() {
  const { 
    user, sessionId, isGuest, isLoading, 
    signInWithEmail, signUpWithEmail, signOut, 
    continueAsGuest, getAuthHeader,
    guestTimeLeft, showWarning, setShowWarning, formatTime
  } = useAuth()

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
>>>>>>> 73606c4 (Guest session timer + privacy notes on UI)

export default function App(): JSX.Element {
  return (
<<<<<<< HEAD
    <div className="w-full bg-[#a1d7d6] font-sans text-teal-950">
      <QuickExitBar />

      <section className="pt-0 relative flex flex-col items-center justify-center min-h-screen w-full overflow-hidden">
        <WelcomeGlowBox />
      </section>

      {/* Scroll Indicator */}
      <div className="flex justify-center -mt-20 mb-7">
        <div className="flex flex-col items-center animate-pulse text-teal-900/60 max-w-5xl w-full px-6">
          <span className="text-xs font-bold tracking-widest uppercase mb-2">
            Scroll for Resources
          </span>
          <div className="w-px h-12 bg-gradient-to-b from-teal-900/60 to-transparent"></div>
        </div>
      </div>

      {/* Resources */}
      <section className="w-full py-24 bg-white border-t border-gray-100">
        <div className="max-w-5xl mx-auto px-6">
=======
    <div className="w-full bg-[#a1d7d6] font-sans text-teal-950 overflow-x-hidden">
      <QuickExitBar onSignOut={signOut} showSignOut={!isGuest} />

      {/* Guest session warning banner */}
      {isGuest && showWarning && guestTimeLeft !== null && (
        <div className="fixed top-14 sm:top-16 left-0 w-full z-40 bg-red-500 text-white px-4 py-2 flex items-center justify-between text-sm">
        <span>
          Your session ends in{' '}
          <span className="font-bold">{formatTime(guestTimeLeft)}</span>
          {' '}— sign up to keep your support going
        </span>
          <button
            onClick={() => setShowWarning(false)}
            className="text-white/80 hover:text-white text-xs shrink-0 ml-4"
          >
            Dismiss
          </button>
        </div>
      )}

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
>>>>>>> 73606c4 (Guest session timer + privacy notes on UI)
          <ResourcesSection />
        </div>
      </section>
    </div>
<<<<<<< HEAD
  )
=======
  );
>>>>>>> 73606c4 (Guest session timer + privacy notes on UI)
}