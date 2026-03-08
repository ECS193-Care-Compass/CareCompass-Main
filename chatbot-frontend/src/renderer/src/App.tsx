import { useState } from 'react'
import { WelcomeGlowBox } from './components/WelcomeGlowBox'
import { QuickExitBar } from './components/QuickExitBar'
import { ResourcesSection } from './components/ResourcesSection'
import { AuthScreen } from './components/AuthScreen'
import { useAuth } from './hooks/useAuth'

export default function App() {
  const auth = useAuth()
  const [showAuth, setShowAuth] = useState(true)

  // Show loading while checking for existing session
  if (auth.isLoading) {
    return (
      <div className="w-full bg-[#a1d7d6] font-sans text-teal-950 flex items-center justify-center min-h-screen">
        <p className="text-sm text-teal-800/60 animate-pulse">Loading...</p>
      </div>
    )
  }

  // Show auth screen if not authenticated and hasn't chosen guest
  if (showAuth && !auth.user && auth.isGuest) {
    return (
      <div className="w-full bg-[#a1d7d6] font-sans text-teal-950">
        <QuickExitBar />
        <AuthScreen
          onSignIn={auth.signInWithEmail}
          onSignUp={auth.signUpWithEmail}
          onGuest={() => {
            auth.continueAsGuest()
            setShowAuth(false)
          }}
        />
      </div>
    )
  }

  return (
    <div className="w-full bg-[#a1d7d6] font-sans text-teal-950">
      <QuickExitBar />

      <section className="pt-0 relative flex flex-col items-center justify-center min-h-screen w-full overflow-hidden">
        <WelcomeGlowBox
          sessionId={auth.sessionId}
          authToken={auth.getAuthHeader()}
          isGuest={auth.isGuest}
          userEmail={auth.user?.email}
          onSignOut={auth.signOut}
        />
      </section>

      {/* Scroll Indicator */}
      <div className="flex justify-center -mt-20 mb-7">
        <div className="flex flex-col items-center animate-pulse text-teal-900/60 max-w-5xl w-full px-6">
          <span className="text-xs font-bold tracking-widest uppercase mb-2">Scroll for Resources</span>
          <div className="w-px h-12 bg-gradient-to-b from-teal-900/60 to-transparent"></div>
        </div>
      </div>

      {/* Resources */}
      <section className="w-full py-24 bg-white border-t border-gray-100">
        <div className="max-w-5xl mx-auto px-6">
          <ResourcesSection />
        </div>
      </section>
    </div>
  );
}
