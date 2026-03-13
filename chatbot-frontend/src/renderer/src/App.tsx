import { useState } from 'react'
import { WelcomeGlowBox } from './components/WelcomeGlowBox'
import { QuickExitBar } from './components/QuickExitBar'
import { ResourcesSection } from './components/ResourcesSection'
import { AuthScreen } from './components/AuthScreen'

export default function App() {
  const [showAuth, setShowAuth] = useState(true)

  if (showAuth) {
    return (
      <div className="w-full bg-[#a1d7d6] font-sans text-teal-950">
        <AuthScreen
          onSignIn={async () => { setShowAuth(false); return { error: null }; }}
          onSignUp={async () => { setShowAuth(false); return { error: null }; }}
          onGuest={() => setShowAuth(false)}
        />
      </div>
    )
  }

  return (
    <div className="w-full bg-[#a1d7d6] font-sans text-teal-950">
      <QuickExitBar />
      <section className="pt-0 relative flex flex-col items-center justify-center min-h-screen w-full overflow-hidden">
        <WelcomeGlowBox />
      </section>
      <div className="flex justify-center -mt-20 mb-7 pointer-events-none">
        <div className="flex flex-col items-center animate-pulse text-teal-900/60 max-w-5xl w-full px-6 pointer-events-none">
          <span className="text-xs font-bold tracking-widest uppercase mb-2">Scroll for Resources</span>
          <div className="w-px h-12 bg-gradient-to-b from-teal-900/60 to-transparent"></div>
        </div>
      </div>
      <section className="w-full py-24 bg-white border-t border-gray-100">
        <div className="max-w-5xl mx-auto px-6">
          <ResourcesSection />
        </div>
      </section>
    </div>
  );
}
