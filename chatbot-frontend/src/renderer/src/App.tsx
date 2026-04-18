import { WelcomeGlowBox } from './components/WelcomeGlowBox'
import { QuickExitBar } from './components/QuickExitBar'
import { ResourcesSection } from './components/ResourcesSection'
import { AuthScreen } from './components/AuthScreen'
import { useAuth } from './hooks/useAuth'

export default function App() {
  const { user, sessionId, isGuest, isLoading, signInWithEmail, signUpWithEmail, signOut, continueAsGuest, getAuthHeader } = useAuth()

  if (isLoading) {
    return (
      <div className="w-full bg-[#a1d7d6] font-sans text-teal-950 flex items-center justify-center min-h-screen">
        <p className="text-teal-800/70 animate-pulse">Loading...</p>
      </div>
    )
  }

  if (!user && !isGuest) {
    return (
      <div className="w-full bg-[#a1d7d6] font-sans text-teal-950">
        <AuthScreen
          onSignIn={signInWithEmail}
          onSignUp={signUpWithEmail}
          onGuest={continueAsGuest}
        />
      </div>
    )
  }

  return (
    <div className="w-full bg-[#a1d7d6] font-sans text-teal-950">
      <QuickExitBar onSignOut={signOut} showSignOut={!isGuest} />
      <section className="pt-14 lg:pt-0 relative flex flex-col items-center justify-center h-[93vh] lg:min-h-screen w-full overflow-hidden pb-4 lg:pb-0 px-3 lg:px-0">
        <WelcomeGlowBox sessionId={sessionId} authToken={getAuthHeader()} />
      </section>
      <div className="hidden lg:flex justify-center -mt-20 mb-7 pointer-events-none">
        <div className="flex flex-col items-center animate-pulse text-teal-900/60 max-w-5xl w-full px-6 pointer-events-none">
          <span className="text-xs font-bold tracking-widest uppercase mb-2">Scroll for Resources</span>
          <div className="w-px h-12 bg-gradient-to-b from-teal-900/60 to-transparent"></div>
        </div>
      </div>
      <section className="w-full pt-2 lg:py-24 pb-24 bg-white border-t border-gray-100">
        <div className="max-w-5xl mx-auto px-6">
          <ResourcesSection />
        </div>
      </section>
    </div>
  );
}
