import { createContext, useContext, useEffect, useState, ReactNode } from 'react'

type ContrastMode = 'normal' | 'high'

interface ContrastContextValue {
  mode: ContrastMode
  isHighContrast: boolean
  toggleContrast: () => void
  setContrast: (mode: ContrastMode) => void
}

const STORAGE_KEY = 'care_bot_contrast_mode'

const ContrastContext = createContext<ContrastContextValue | undefined>(undefined)

function readStoredMode(): ContrastMode {
  if (typeof window === 'undefined') return 'normal'
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    return stored === 'high' ? 'high' : 'normal'
  } catch {
    return 'normal'
  }
}

function applyModeToDocument(mode: ContrastMode): void {
  if (typeof document === 'undefined') return
  const root = document.documentElement
  root.setAttribute('data-contrast', mode)
  if (mode === 'high') {
    root.classList.add('high-contrast')
  } else {
    root.classList.remove('high-contrast')
  }
}

interface ContrastProviderProps {
  children: ReactNode
}

export function ContrastProvider({ children }: ContrastProviderProps) {
  const [mode, setMode] = useState<ContrastMode>(() => readStoredMode())

  useEffect(() => {
    applyModeToDocument(mode)
    try {
      window.localStorage.setItem(STORAGE_KEY, mode)
    } catch {
      /* ignore storage errors (e.g. private browsing) */
    }
  }, [mode])

  const toggleContrast = () => {
    setMode((prev) => (prev === 'high' ? 'normal' : 'high'))
  }

  const setContrast = (next: ContrastMode) => {
    setMode(next)
  }

  const value: ContrastContextValue = {
    mode,
    isHighContrast: mode === 'high',
    toggleContrast,
    setContrast,
  }

  return <ContrastContext.Provider value={value}>{children}</ContrastContext.Provider>
}

export function useContrast(): ContrastContextValue {
  const ctx = useContext(ContrastContext)
  if (!ctx) {
    throw new Error('useContrast must be used inside a <ContrastProvider>')
  }
  return ctx
}
