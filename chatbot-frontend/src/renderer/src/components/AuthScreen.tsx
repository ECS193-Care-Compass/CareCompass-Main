import { useState } from 'react'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Mail, Lock, ArrowRight, UserCircle } from 'lucide-react'

interface AuthScreenProps {
  onSignIn: (email: string, password: string) => Promise<{ error: any }>
  onSignUp: (email: string, password: string) => Promise<{ error: any }>
  onGuest: () => void
}

export function AuthScreen({ onSignIn, onSignUp, onGuest }: AuthScreenProps) {
  const [mode, setMode] = useState<'welcome' | 'signin' | 'signup'>('welcome')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [signUpSuccess, setSignUpSuccess] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    const result = mode === 'signin'
      ? await onSignIn(email, password)
      : await onSignUp(email, password)

    if (result.error) {
      setError(result.error.message)
    } else if (mode === 'signup') {
      setSignUpSuccess(true)
    }

    setIsLoading(false)
  }

  // Welcome screen, choose sign in or guest
  if (mode === 'welcome') {
    return (
      <div className="flex items-center justify-center min-h-screen w-full">
        <div className="flex flex-col items-center w-full max-w-md mx-5 px-8 py-10 border border-teal-700/20 rounded-3xl bg-white/5 hover:bg-white/10 hover:border-teal-700/40 transition-all">
          <h1 className="text-2xl font-medium text-teal-900/90 text-center mb-2">
            Welcome to CARE Bot
          </h1>
          <p className="text-sm text-teal-800/70 text-center mb-8">
            You're safe here. Choose how you'd like to continue.
          </p>

          <button
            onClick={() => setMode('signin')}
            className="w-full flex items-center justify-center gap-2 px-5 py-3 mb-3 text-sm font-medium text-white bg-teal-700 rounded-xl hover:bg-teal-800 transition-colors"
          >
            <Mail size={16} />
            Sign in with email
          </button>

          <button
            onClick={() => setMode('signup')}
            className="w-full flex items-center justify-center gap-2 px-5 py-3 mb-6 text-sm font-medium text-teal-900 border border-teal-700/30 bg-white/30 rounded-xl hover:bg-white/50 hover:border-teal-700/50 transition-all"
          >
            Create an account
          </button>

          <div className="flex items-center w-full gap-3 mb-6">
            <div className="flex-1 h-px bg-teal-700/20" />
            <span className="text-xs text-teal-800/50 uppercase tracking-wider">or</span>
            <div className="flex-1 h-px bg-teal-700/20" />
          </div>

          <button
            onClick={onGuest}
            className="w-full flex items-center justify-center gap-2 px-5 py-3 text-sm font-medium text-teal-800/80 hover:text-teal-900 transition-colors"
          >
            <UserCircle size={16} />
            Continue as guest
          </button>

          <p className="text-xs text-teal-800/50 text-center mt-6 leading-relaxed">
            Guest sessions expire after 30 minutes of inactivity.
            <br />
            Sign in to save your conversation history.
          </p>
        </div>
      </div>
    )
  }

  // Sign up success
  if (signUpSuccess) {
    return (
      <div className="flex items-center justify-center min-h-screen w-full">
        <div className="flex flex-col items-center w-full max-w-md mx-5 px-8 py-10 border border-teal-700/20 rounded-3xl bg-white/5">
          <h2 className="text-xl font-medium text-teal-900/90 text-center mb-3">
            Check your email
          </h2>
          <p className="text-sm text-teal-800/70 text-center mb-6">
            We sent a confirmation link to <strong>{email}</strong>.
            <br />
            Click the link to activate your account.
          </p>
          <button
            onClick={() => { setMode('signin'); setSignUpSuccess(false); }}
            className="px-5 py-2 text-sm font-medium text-teal-900 border border-teal-700/30 bg-white/30 rounded-xl hover:bg-white/50 hover:border-teal-700/50 transition-all"
          >
            Back to sign in
          </button>
        </div>
      </div>
    )
  }

  // Sign in / Sign up form
  return (
    <div className="flex items-center justify-center min-h-screen w-full">
      <div className="flex flex-col w-full max-w-md mx-5 px-8 py-10 border border-teal-700/20 rounded-3xl bg-white/5 hover:bg-white/10 hover:border-teal-700/40 transition-all">
        <h2 className="text-xl font-medium text-teal-900/90 text-center mb-6">
          {mode === 'signin' ? 'Sign in' : 'Create account'}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label className="text-teal-900/80">Email</Label>
            <div className="relative">
              <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-teal-700/40" />
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                className="pl-9 bg-white/80 border-teal-700/20 text-teal-950 placeholder-teal-700/40 rounded-xl py-3 text-sm focus:ring-2 focus:ring-teal-700/40 focus:border-transparent"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-teal-900/80">Password</Label>
            <div className="relative">
              <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-teal-700/40" />
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={mode === 'signup' ? 'At least 6 characters' : 'Your password'}
                required
                minLength={mode === 'signup' ? 6 : undefined}
                className="pl-9 bg-white/80 border-teal-700/20 text-teal-950 placeholder-teal-700/40 rounded-xl py-3 text-sm focus:ring-2 focus:ring-teal-700/40 focus:border-transparent"
              />
            </div>
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-100/50 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-2 px-5 py-3 text-sm font-medium text-white bg-teal-700 rounded-xl hover:bg-teal-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <span className="animate-pulse">Please wait...</span>
            ) : (
              <>
                {mode === 'signin' ? 'Sign in' : 'Create account'}
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </form>

        <div className="flex items-center justify-between mt-6">
          <button
            onClick={() => setMode(mode === 'signin' ? 'signup' : 'signin')}
            className="text-xs text-teal-800/60 hover:text-teal-900 transition-colors"
          >
            {mode === 'signin' ? "Don't have an account? Sign up" : 'Already have an account? Sign in'}
          </button>

          <button
            onClick={() => setMode('welcome')}
            className="text-xs text-teal-800/60 hover:text-teal-900 transition-colors"
          >
            Back
          </button>
        </div>
      </div>
    </div>
  )
}
