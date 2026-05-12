import { Eye, EyeOff } from 'lucide-react'
import { useContrast } from '../contexts/ContrastContext'

interface HighContrastToggleProps {
  variant?: 'compact' | 'full'
  className?: string
}

export function HighContrastToggle({ variant = 'compact', className = '' }: HighContrastToggleProps) {
  const { isHighContrast, toggleContrast } = useContrast()

  const baseClasses =
    'flex items-center gap-2 rounded transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-yellow-300'

  const compactClasses = isHighContrast
    ? 'bg-yellow-300 hover:bg-yellow-200 text-black border border-black px-3 py-2 text-xs lg:text-sm font-bold whitespace-nowrap'
    : 'bg-teal-800 hover:bg-teal-900 text-teal-50 px-3 py-2 text-xs lg:text-sm whitespace-nowrap'

  const fullClasses = isHighContrast
    ? 'bg-yellow-300 hover:bg-yellow-200 text-black border-2 border-black px-4 py-2 font-bold'
    : 'bg-teal-700 hover:bg-teal-800 text-white px-4 py-2'

  const classes =
    variant === 'compact'
      ? `${baseClasses} ${compactClasses} ${className}`
      : `${baseClasses} ${fullClasses} ${className}`

  const label = isHighContrast ? 'High contrast on' : 'High contrast off'

  return (
    <button
      type="button"
      onClick={toggleContrast}
      className={classes}
      aria-pressed={isHighContrast}
      aria-label={`Toggle high contrast mode. Currently ${isHighContrast ? 'on' : 'off'}.`}
      title={`High Contrast Mode: ${isHighContrast ? 'On' : 'Off'}`}
    >
      {isHighContrast ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
      <span className="hidden sm:inline">{label}</span>
      <span className="sm:hidden">{isHighContrast ? 'HC' : 'HC'}</span>
    </button>
  )
}
