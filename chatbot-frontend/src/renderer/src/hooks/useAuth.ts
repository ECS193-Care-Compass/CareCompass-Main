import { useState, useEffect, useRef } from 'react'
import { supabase } from '../lib/supabase'
import type { User, Session } from '@supabase/supabase-js'

interface AuthState {
  user: User | null
  session: Session | null
  sessionId: string
  isGuest: boolean
  isLoading: boolean
  isAdmin: boolean
}

function generateGuestId(): string {
  return `guest-${crypto.randomUUID()}`
}

const GUEST_SESSION_KEY = 'care-compass-guest-id'

// Timer of 30 minutes for guest trials
const GUEST_SESSION_DURATION = 30 * 60 * 1000 // 30 minutes
const WARNING_THRESHOLD = 5 * 60 * 1000        // 5 minutes

function getOrCreateGuestId(): string {
  const existing = sessionStorage.getItem(GUEST_SESSION_KEY)
  if (existing) return existing
  const id = generateGuestId()
  sessionStorage.setItem(GUEST_SESSION_KEY, id)
  return id
}

async function fetchIsAdmin(userId: string): Promise<boolean> {
  try {
    const { data, error } = await supabase
      .from('profiles')
      .select('role')
      .eq('id', userId)
      .single()
    if (error) return false
    return data?.role === 'admin'
  } catch {
    return false
  }
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    user: null,
    session: null,
    sessionId: getOrCreateGuestId(),
    isGuest: false,
    isLoading: true,
    isAdmin: false,
  })

  const [guestTimeLeft, setGuestTimeLeft] = useState<number | null>(null)
  const [showWarning, setShowWarning] = useState(false)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const startTimeRef = useRef<number | null>(null)

  useEffect(() => {
    supabase.auth.getSession().then(async ({ data: { session } }) => {
      if (session?.user) {
        const isAdmin = await fetchIsAdmin(session.user.id)
        setState({
          user: session.user,
          session,
          sessionId: session.user.id,
          isGuest: false,
          isLoading: false,
          isAdmin,
        })
      } else {
        setState(prev => ({ ...prev, isLoading: false }))
      }
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (event === 'INITIAL_SESSION') return undefined
      if (session?.user) {
        // Clear guest timer if user signs in
        if (timerRef.current) clearInterval(timerRef.current)
        setGuestTimeLeft(null)
        setShowWarning(false)
        const isAdmin = await fetchIsAdmin(session.user.id)
        setState({
          user: session.user,
          session,
          sessionId: session.user.id,
          isGuest: false,
          isLoading: false,
          isAdmin,
        })
      } else {
        setState({
          user: null,
          session: null,
          sessionId: getOrCreateGuestId(),
          isGuest: false,
          isLoading: false,
          isAdmin: false,
        })
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  // Guest session countdown
  useEffect(() => {
    if (!state.isGuest) {
      if (timerRef.current) clearInterval(timerRef.current)
      setGuestTimeLeft(null)
      setShowWarning(false)
      return undefined
    }

    startTimeRef.current = Date.now()
    setGuestTimeLeft(GUEST_SESSION_DURATION)

    timerRef.current = setInterval(() => {
      const elapsed = Date.now() - (startTimeRef.current ?? Date.now())
      const remaining = GUEST_SESSION_DURATION - elapsed

      if (remaining <= 0) {
        clearInterval(timerRef.current!)
        setGuestTimeLeft(0)
        sessionStorage.removeItem(GUEST_SESSION_KEY)
        setState({
          user: null,
          session: null,
          sessionId: getOrCreateGuestId(),
          isGuest: false,
          isLoading: false,
          isAdmin: false,
        })
        return
      }

      setGuestTimeLeft(remaining)

      if (remaining <= WARNING_THRESHOLD) {
        setShowWarning(true)
      }
    }, 1000)

    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [state.isGuest])

  const formatTime = (ms: number): string => {
    const minutes = Math.floor(ms / 60000)
    const seconds = Math.floor((ms % 60000) / 1000)
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  }

  const signInWithEmail = async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    return { error }
  }

  const signUpWithEmail = async (email: string, password: string) => {
    const { error } = await supabase.auth.signUp({ email, password })
    return { error }
  }

  const signOut = async () => {
    if (timerRef.current) clearInterval(timerRef.current)
    setGuestTimeLeft(null)
    setShowWarning(false)
    await supabase.auth.signOut()
  }

  const continueAsGuest = () => {
    setState({
      user: null,
      session: null,
      sessionId: getOrCreateGuestId(),
      isGuest: true,
      isLoading: false,
      isAdmin: false,
    })
  }

  const getAuthHeader = (): string | undefined => {
    if (state.session?.access_token) {
      return `Bearer ${state.session.access_token}`
    }
    return undefined
  }

  return {
    ...state,
    signInWithEmail,
    signUpWithEmail,
    signOut,
    continueAsGuest,
    getAuthHeader,
    guestTimeLeft,
    showWarning,
    setShowWarning,
    formatTime,
  }
}