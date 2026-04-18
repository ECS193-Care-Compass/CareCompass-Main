import { useEffect } from 'react';
import { LogOut, UserX } from 'lucide-react';

interface QuickExitBarProps {
  onSignOut?: () => void
  showSignOut?: boolean
}

export function QuickExitBar({ onSignOut, showSignOut }: QuickExitBarProps) {
  const handleQuickExit = () => {
    window.location.replace('https://www.google.com');
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

  return (
    <div className="fixed top-0 left-0 w-full z-50 bg-teal-700 border-b border-teal-600 px-4 lg:px-8 py-3">
      <div className="flex items-center gap-3 lg:gap-4 lg:justify-between">
        <p className="text-xs md:text-sm leading-tight text-teal-50 whitespace-nowrap block lg:hidden">
          Tap the exit button to quickly leave
        </p>
        <p className="text-sm text-teal-50 hidden lg:block whitespace-nowrap">
          Press <kbd className="px-2 py-1 bg-teal-600 rounded text-xs mx-1 text-teal-50">ESC</kbd> or click the button to quickly leave this site
        </p>
        <div className="flex items-center gap-2 ml-auto lg:ml-0">
          {showSignOut && onSignOut && (
            <button
              onClick={onSignOut}
              className="px-4 py-2 bg-teal-800 text-teal-50 hover:bg-teal-900 rounded flex items-center gap-2 transition-colors text-xs lg:text-sm whitespace-nowrap"
            >
              <UserX className="w-4 h-4" />
              Sign Out
            </button>
          )}
          <button
            onClick={handleQuickExit}
            className="px-4 py-2 bg-teal-600 text-teal-50 hover:bg-teal-500 rounded flex items-center gap-2 transition-colors text-xs lg:text-sm whitespace-nowrap"
          >
            <LogOut className="w-4 h-4" />
            Quick Exit
          </button>
        </div>
      </div>
    </div>
  );
}
