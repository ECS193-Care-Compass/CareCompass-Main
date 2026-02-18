import { useEffect } from 'react';
import { LogOut } from 'lucide-react';

export function QuickExitBar() {
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
    <div className="bg-teal-700 border-b border-teal-600 px-8 py-3">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-teal-50">
          Press <kbd className="px-2 py-1 bg-teal-600 rounded text-xs mx-1 text-teal-50">ESC</kbd> or click the button to quickly leave this site
        </p>
        <button
          onClick={handleQuickExit}
          className="px-4 py-2 bg-teal-600 text-teal-50 hover:bg-teal-500 rounded flex items-center gap-2 transition-colors text-sm whitespace-nowrap"
        >
          <LogOut className="w-4 h-4" />
          Quick Exit
        </button>
      </div>
    </div>
  );
}
