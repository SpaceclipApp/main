'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import { useAuthStore } from '@/store/auth'
import { getCurrentUser } from '@/lib/api'

/**
 * AuthRehydrator: Ensures user profile is fresh on app init
 * - If token exists, fetches current user from backend
 * - Updates store with fresh data (name, avatar_url, etc.)
 * - Logs out if token is invalid
 */
function AuthRehydrator({ children }: { children: React.ReactNode }) {
  const { token, isAuthenticated, updateUser, logout, _hasHydrated } = useAuthStore()
  const [isRehydrating, setIsRehydrating] = useState(false)
  
  useEffect(() => {
    // Wait for zustand to hydrate from localStorage
    if (!_hasHydrated) return
    
    // Only fetch if we have a token
    if (!token || !isAuthenticated) return
    
    // Prevent multiple fetches
    if (isRehydrating) return
    
    const rehydrateUser = async () => {
      setIsRehydrating(true)
      try {
        const user = await getCurrentUser()
        // Update store with fresh user data from backend
        updateUser({
          name: user.name,
          avatar_url: user.avatar_url,
        })
      } catch (error) {
        // Token is invalid - log out silently
        console.error('Failed to rehydrate user, logging out:', error)
        logout()
      } finally {
        setIsRehydrating(false)
      }
    }
    
    rehydrateUser()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [_hasHydrated, token])
  
  return <>{children}</>
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            refetchOnWindowFocus: false,
          },
        },
      })
  )

  return (
    <QueryClientProvider client={queryClient}>
      <AuthRehydrator>
        {children}
      </AuthRehydrator>
    </QueryClientProvider>
  )
}







