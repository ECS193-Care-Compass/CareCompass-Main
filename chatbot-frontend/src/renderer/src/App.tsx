import { WelcomeGlowBox } from './components/WelcomeGlowBox'
import { QuickExitBar } from './components/QuickExitBar'
import { ResourcesSection } from './components/ResourcesSection'

export default function App() {
  return (
    <div className="w-full bg-[#a1d7d6] font-sans text-teal-950">
      
      {/*Full-Screen Chat Interface */}
      <section className="relative flex flex-col items-center justify-center min-h-screen w-full overflow-hidden">
        <div className="absolute top-0 left-0 w-full z-10">
          <QuickExitBar />
        </div>

        <WelcomeGlowBox />

        {/* Scroll Indicator */}
        <div className="absolute bottom-8 flex flex-col items-center animate-pulse text-teal-900/60">
          <span className="text-xs font-bold tracking-widest uppercase mb-2">Scroll for Resources</span>
          <div className="w-px h-12 bg-gradient-to-b from-teal-900/60 to-transparent"></div>
        </div>
      </section>

      {/* Resources (Appears when scrolling down) */}
      <section className="w-full py-24 bg-white/20 backdrop-blur-lg border-t border-white/30">
        <div className="max-w-6xl mx-auto px-6">
          <ResourcesSection />
        </div>
      </section>

    </div>
  );
}