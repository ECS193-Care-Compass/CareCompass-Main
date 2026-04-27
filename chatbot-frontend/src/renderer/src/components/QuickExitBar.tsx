import { useEffect } from 'react';
import { LogOut, UserX, Clock } from 'lucide-react';
import { useMetrics } from '../context/MetricsContext'

interface QuickExitBarProps {
  onSignOut?: () => void
  showSignOut?: boolean
  guestTimeLeft?: number | null
  showWarning?: boolean
  formatTime?: (ms: number) => string
}

export function QuickExitBar({ onSignOut, showSignOut, guestTimeLeft, showWarning, formatTime }: QuickExitBarProps) {
  const {recordQuickExit} = useMetrics()
  const handleQuickExit = () => {
    recordQuickExit()
    const overlay = document.createElement('div')
    overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:#a1d7d6;display:flex;align-items:center;justify-content:center;z-index:9999;font-family:sans-serif;color:#134e4a;font-size:1.2rem;'
    overlay.innerText = 'You took a brave step today. Be well. 💙'
    document.body.appendChild(overlay)
    setTimeout(() => {
      window.location.replace('https://www.google.com')
    }, 1500)
  };

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        handleQuickExit();
      }
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, []);

  const isWarning = showWarning && guestTimeLeft !== null && guestTimeLeft !== undefined
  const hasTimer = guestTimeLeft !== null && guestTimeLeft !== undefined && formatTime

  return (
    <div className={`fixed top-0 left-0 w-full z-50 border-b px-4 lg:px-8 py-3 transition-colors duration-500 ${isWarning ? 'bg-rose-300 border-rose-200' : 'bg-teal-700 border-teal-600'}`}>
      <div className="flex items-center gap-3 lg:gap-4 lg:justify-between">

        {/* Left text */}
        {isWarning && formatTime && guestTimeLeft !== null && guestTimeLeft !== undefined ? (
          <div className="flex items-center gap-2 text-rose-900 text-xs md:text-sm">
            <Clock className="w-4 h-4 shrink-0 animate-pulse" />
            <span>
              Your safe space closes in{' '}
              <span className="font-bold">{formatTime(guestTimeLeft)}</span>
              {' '}— <a href="#" onClick={(e) => { e.preventDefault(); onSignOut?.() }} className="underline hover:no-underline">create a free account to stay</a>
            </span>
          </div>
        ) : hasTimer && guestTimeLeft !== null && guestTimeLeft !== undefined && formatTime ? (
          <div className="flex items-center gap-2 text-teal-200 text-xs md:text-sm">
            <Clock className="w-4 h-4 shrink-0" />
            <span>Guest session: <span className="font-bold">{formatTime(guestTimeLeft)}</span> remaining</span>
          </div>
        ) : (
          <>
            <p className="text-xs md:text-sm leading-tight text-teal-50 whitespace-nowrap block lg:hidden">
              Tap the exit button to quickly leave
            </p>
            <p className="text-sm text-teal-50 hidden lg:block whitespace-nowrap">
              Press <kbd className="px-2 py-1 bg-teal-600 rounded text-xs mx-1 text-teal-50">ESC</kbd> or click the button to quickly leave this site
            </p>
          </>
        )}

        {/* Right buttons */}
        <div className="flex items-center gap-2 ml-auto lg:ml-0">
          {showSignOut && onSignOut && (
            <button
              onClick={onSignOut}
              className={`px-4 py-2 rounded flex items-center gap-2 transition-colors text-xs lg:text-sm whitespace-nowrap ${isWarning ? 'bg-rose-400 hover:bg-rose-500 text-rose-900' : 'bg-teal-800 hover:bg-teal-900 text-teal-50'}`}
            >
              <UserX className="w-4 h-4" />
              Sign Out
            </button>
          )}
          <button
            onClick={handleQuickExit}
            className={`px-4 py-2 rounded flex items-center gap-2 transition-colors text-xs lg:text-sm whitespace-nowrap ${isWarning ? 'bg-rose-400 hover:bg-rose-500 text-rose-900' : 'bg-teal-600 hover:bg-teal-500 text-teal-50'}`}
          >
            <LogOut className="w-4 h-4" />
            Quick Exit
          </button>
        </div>
      </div>
    </div>
  );
}