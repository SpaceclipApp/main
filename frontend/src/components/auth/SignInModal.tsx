'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Mail, Lock, Loader2, ArrowRight, KeyRound } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/store/auth'

interface SignInModalProps {
  isOpen: boolean
  onClose: () => void
}

type AuthStep = 'email' | 'password' | 'new-password'

function validatePassword(password: string): string | null {
  if (password.length < 8) {
    return "Password must be at least 8 characters and include a letter and a number."
  }
  
  const hasLetter = /[a-zA-Z]/.test(password)
  const hasDigit = /[0-9]/.test(password)
  
  if (!hasLetter || !hasDigit) {
    return "Password must be at least 8 characters and include a letter and a number."
  }
  
  return null
}

export function SignInModal({ isOpen, onClose }: SignInModalProps) {
  const [step, setStep] = useState<AuthStep>('email')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [passwordError, setPasswordError] = useState<string | null>(null)
  const [isNewUser, setIsNewUser] = useState(false)
  
  const { login } = useAuthStore()
  
  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email) {
      setError('Please enter your email')
      return
    }
    
    setIsLoading(true)
    setError('')
    
    try {
      // Check if user exists
      const response = await fetch(`http://localhost:8000/api/auth/check-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      })
      
      const data = await response.json()
      
      if (data.exists) {
        // Existing user - ask for password
        setIsNewUser(false)
        setStep('password')
      } else {
        // New user - create password
        setIsNewUser(true)
        setStep('new-password')
      }
    } catch (err) {
      // If API not available, assume new user for demo
      setIsNewUser(true)
      setStep('new-password')
    } finally {
      setIsLoading(false)
    }
  }
  
  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!password) {
      setError('Please enter your password')
      return
    }
    
    setIsLoading(true)
    setError('')
    
    try {
      const response = await fetch(`http://localhost:8000/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })
      
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Invalid credentials')
      }
      
      const data = await response.json()
      login(data.user, data.token)
      onClose()
      resetForm()
    } catch (err: any) {
      setError(err.message || 'Invalid email or password')
    } finally {
      setIsLoading(false)
    }
  }
  
  const handleNewPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!password) {
      setError('Please create a password')
      return
    }
    
    const validationError = validatePassword(password)
    if (validationError) {
      setPasswordError(validationError)
      return
    }
    
    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }
    
    setIsLoading(true)
    setError('')
    setPasswordError(null)
    
    try {
      const response = await fetch(`http://localhost:8000/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })
      
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to create account')
      }
      
      const data = await response.json()
      login(data.user, data.token)
      onClose()
      resetForm()
    } catch (err: any) {
      setError(err.message || 'Failed to create account')
    } finally {
      setIsLoading(false)
    }
  }
  
  // OAuth handlers removed from UI (Task 2.5.9 - Auth surface cleanup)
  // Backend OAuth providers remain available in code but are hidden from UI
  // Email-only authentication for improved trust and simplified onboarding
  
  const resetForm = () => {
    setStep('email')
    setEmail('')
    setPassword('')
    setConfirmPassword('')
    setError('')
    setPasswordError(null)
    setIsNewUser(false)
  }
  
  const handleClose = () => {
    resetForm()
    onClose()
  }
  
  const goBackToEmail = () => {
    setStep('email')
    setPassword('')
    setConfirmPassword('')
    setError('')
    setPasswordError(null)
  }
  
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={handleClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
          />
          
          {/* Modal Container - ensures proper centering */}
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="glass-card p-6 relative mx-auto">
                {/* Close button */}
                <button
                  onClick={handleClose}
                  className="absolute top-4 right-4 p-2 rounded-lg text-star-white/60 hover:text-star-white hover:bg-void-700 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
                
                {/* Header */}
                <div className="text-center mb-6">
                  <h2 className="text-2xl font-bold text-star-white mb-2">
                    {step === 'email' && 'Welcome to SpaceClip'}
                    {step === 'password' && 'Welcome Back'}
                    {step === 'new-password' && 'Create Your Account'}
                  </h2>
                  <p className="text-star-white/60 text-sm">
                    {step === 'email' && 'Enter your email to continue'}
                    {step === 'password' && `Sign in as ${email}`}
                    {step === 'new-password' && `Set a password for ${email}`}
                  </p>
                </div>
                
                {/* Email Step */}
                {step === 'email' && (
                  <>
                    {/* Email Form - Email-only authentication */}
                    <form onSubmit={handleEmailSubmit} className="space-y-4">
                      <div>
                        <label className="block text-star-white/60 text-sm mb-2">Email</label>
                        <div className="relative">
                          <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-star-white/40" />
                          <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="you@example.com"
                            autoFocus
                            className="w-full pl-11 pr-4 py-3 rounded-xl bg-void-800 border border-void-600 text-star-white placeholder:text-star-white/40 focus:outline-none focus:border-nebula-purple transition-colors"
                          />
                        </div>
                      </div>
                      
                      {error && (
                        <p className="text-amber-400 text-sm bg-amber-400/10 px-4 py-2 rounded-lg">
                          {error}
                        </p>
                      )}
                      
                      <button
                        type="submit"
                        disabled={isLoading}
                        className="w-full py-3 rounded-xl bg-nebula-purple hover:bg-nebula-violet text-white font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                      >
                        {isLoading ? (
                          <Loader2 className="w-5 h-5 animate-spin" />
                        ) : (
                          <>
                            Continue
                            <ArrowRight className="w-5 h-5" />
                          </>
                        )}
                      </button>
                    </form>
                  </>
                )}
                
                {/* Password Step (existing user) */}
                {step === 'password' && (
                  <form onSubmit={handlePasswordSubmit} className="space-y-4">
                    <div>
                      <label className="block text-star-white/60 text-sm mb-2">Password</label>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-star-white/40" />
                        <input
                          type="password"
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          placeholder="Enter your password"
                          autoFocus
                          className="w-full pl-11 pr-4 py-3 rounded-xl bg-void-800 border border-void-600 text-star-white placeholder:text-star-white/40 focus:outline-none focus:border-nebula-purple transition-colors"
                        />
                      </div>
                    </div>
                    
                    {error && (
                      <p className="text-amber-400 text-sm bg-amber-400/10 px-4 py-2 rounded-lg">
                        {error}
                      </p>
                    )}
                    
                    <button
                      type="submit"
                      disabled={isLoading}
                      className="w-full py-3 rounded-xl bg-nebula-purple hover:bg-nebula-violet text-white font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                      {isLoading ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        'Sign In'
                      )}
                    </button>
                    
                    <div className="flex items-center justify-between text-sm">
                      <button
                        type="button"
                        onClick={goBackToEmail}
                        className="text-star-white/60 hover:text-star-white transition-colors"
                      >
                        ← Use different email
                      </button>
                      <button
                        type="button"
                        onClick={() => setError('Password reset coming soon!')}
                        className="text-nebula-violet hover:text-nebula-pink transition-colors"
                      >
                        Forgot password?
                      </button>
                    </div>
                  </form>
                )}
                
                {/* New Password Step (new user) */}
                {step === 'new-password' && (
                  <form onSubmit={handleNewPasswordSubmit} className="space-y-4">
                    <div>
                      <label className="block text-star-white/60 text-sm mb-2">Create Password</label>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-star-white/40" />
                        <input
                          type="password"
                          value={password}
                          onChange={(e) => {
                            const newPassword = e.target.value
                            setPassword(newPassword)
                            setPasswordError(validatePassword(newPassword))
                          }}
                          placeholder="At least 8 characters with a letter and number"
                          autoFocus
                          className="w-full pl-11 pr-4 py-3 rounded-xl bg-void-800 border border-void-600 text-star-white placeholder:text-star-white/40 focus:outline-none focus:border-nebula-purple transition-colors"
                        />
                      </div>
                      {passwordError && (
                        <p className="text-amber-400 text-sm mt-2">
                          {passwordError}
                        </p>
                      )}
                    </div>
                    
                    <div>
                      <label className="block text-star-white/60 text-sm mb-2">Confirm Password</label>
                      <div className="relative">
                        <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-star-white/40" />
                        <input
                          type="password"
                          value={confirmPassword}
                          onChange={(e) => setConfirmPassword(e.target.value)}
                          placeholder="Confirm your password"
                          className="w-full pl-11 pr-4 py-3 rounded-xl bg-void-800 border border-void-600 text-star-white placeholder:text-star-white/40 focus:outline-none focus:border-nebula-purple transition-colors"
                        />
                      </div>
                    </div>
                    
                    {error && (
                      <p className="text-amber-400 text-sm bg-amber-400/10 px-4 py-2 rounded-lg">
                        {error}
                      </p>
                    )}
                    
                    <button
                      type="submit"
                      disabled={isLoading || !password || validatePassword(password) !== null}
                      className="w-full py-3 rounded-xl bg-nebula-purple hover:bg-nebula-violet text-white font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                      {isLoading ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        'Create Account'
                      )}
                    </button>
                    
                    <button
                      type="button"
                      onClick={goBackToEmail}
                      className="w-full text-center text-star-white/60 hover:text-star-white text-sm transition-colors"
                    >
                      ← Use different email
                    </button>
                  </form>
                )}
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  )
}
