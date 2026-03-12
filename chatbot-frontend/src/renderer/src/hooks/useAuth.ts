import { useState, useEffect } from 'react'
import { supabase } from '../lib/supabase'
import type { User, Session } from '@supabase/supabase-js'

interface AuthState {
  user: User | null
  session: Session | null
  sessionId: string
  isGuest: boolean
  isLoading: boolean
}

function generateGuestId(): string {
  return `guest-${crypto.randomUUID()}`
}

const GUEST_SESSION_KEY = 'care-compass-guest-id'

function getOrCreateGuestId(): string {
  const existing = sessionStorage.getItem(GUEST_SESSION_KEY)
  if (existing) return existing
  const id = generateGuestId()
  sessionStorage.setItem(GUEST_SESSION_KEY, id)
  return id
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    user: null,
    session: null,
    sessionId: getOrCreateGuestId(),
    isGuest: false,
    isLoading: true,
  })

  useEffect(() => {
    // Check for existing session
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user) {
        setState({
          user: session.user,
          session,
          sessionId: session.user.id,
          isGuest: false,
          isLoading: false,
        })
      } else {
        setState(prev => ({ ...prev, isLoading: false }))
      }
    })

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.user) {
        setState({
          user: session.user,
          session,
          sessionId: session.user.id,
          isGuest: false,
          isLoading: false,
        })
      } else {
        setState({
          user: null,
          session: null,
          sessionId: getOrCreateGuestId(),
          isGuest: true,
          isLoading: false,
        })
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  const signInWithEmail = async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    return { error }
  }

  const signUpWithEmail = async (email: string, password: string) => {
    const { error } = await supabase.auth.signUp({ email, password })
    return { error }
  }

  const signOut = async () => {
    await supabase.auth.signOut()
  }

  const continueAsGuest = () => {
    setState({
      user: null,
      session: null,
      sessionId: getOrCreateGuestId(),
      isGuest: true,
      isLoading: false,
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
  }
}
