import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface User {
  id: string
  email?: string
  wallet_address?: string
  name?: string
  avatar_url?: string
  created_at: string
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  // Hydration flag to prevent flash of wrong state
  _hasHydrated: boolean
  
  login: (user: User, token: string) => void
  logout: () => void
  updateUser: (user: Partial<User>) => void
  setHasHydrated: (state: boolean) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      _hasHydrated: false,
      
      login: (user, token) => {
        set({ user, token, isAuthenticated: true })
      },
      
      logout: () => {
        // Explicit teardown: clear everything immediately
        set({ user: null, token: null, isAuthenticated: false })
        
        // Also clear from localStorage explicitly to prevent any stale reads
        if (typeof window !== 'undefined') {
          localStorage.removeItem('spaceclip-auth')
        }
      },
      
      updateUser: (updates) => {
        const currentUser = get().user
        if (currentUser) {
          set({ user: { ...currentUser, ...updates } })
        }
      },
      
      setHasHydrated: (state) => {
        set({ _hasHydrated: state })
      },
    }),
    {
      name: 'spaceclip-auth',
      onRehydrateStorage: () => (state) => {
        // Mark hydration complete after rehydrating from localStorage
        state?.setHasHydrated(true)
      },
      // Only persist auth-related fields, not hydration flag
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)

