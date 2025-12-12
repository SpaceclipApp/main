'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Rocket, RefreshCw, User, LogIn, ChevronDown, Settings, LogOut, FolderOpen } from 'lucide-react'
import { useProjectStore } from '@/store/project'
import { useAuthStore } from '@/store/auth'
import { SignInModal } from '@/components/auth/SignInModal'
import { SettingsModal } from '@/components/settings/SettingsModal'
import { ProjectsModal } from '@/components/projects/ProjectsModal'
import { cn } from '@/lib/utils'

export function Header() {
  const { step, reset, clearAll, media } = useProjectStore()
  const { user, isAuthenticated, logout } = useAuthStore()
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [showSignIn, setShowSignIn] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [showProjects, setShowProjects] = useState(false)
  
  const handleLogout = () => {
    logout() // Clear auth store
    clearAll() // Clear all project store data including recent projects
    setShowUserMenu(false)
    // Redirect to upload view
    window.location.href = '/'
  }
  
  const handleOpenSettings = () => {
    setShowUserMenu(false)
    setShowSettings(true)
  }
  
  const handleOpenProjects = () => {
    setShowUserMenu(false)
    setShowProjects(true)
  }
  
  return (
    <>
      {/* Main Header */}
      <header className="relative z-20 border-b border-void-700/50 backdrop-blur-xl bg-void-950/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <motion.div 
              className="flex items-center gap-3 cursor-pointer"
              onClick={() => {
                // Go back to upload view but preserve recent projects
                reset()
              }}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <div className="relative">
                <div className="absolute inset-0 bg-nebula-purple rounded-xl blur-lg opacity-50" />
                <div className="relative w-10 h-10 bg-gradient-to-br from-nebula-purple to-nebula-violet rounded-xl flex items-center justify-center">
                  <Rocket className="w-5 h-5 text-white" />
                </div>
              </div>
              <div>
                <h1 className="text-xl font-bold text-star-white">
                  Space<span className="text-gradient">Clip</span>
                </h1>
              </div>
            </motion.div>
            
            {/* Right side - Auth controls */}
            <div className="flex items-center gap-3">
              {media && (
                <motion.button
                  onClick={reset}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm text-star-white/60 hover:text-star-white hover:bg-void-800 transition-all"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <RefreshCw className="w-4 h-4" />
                  <span className="hidden sm:inline">New</span>
                </motion.button>
              )}
              
              {isAuthenticated && user ? (
                <div className="relative">
                  <button
                    onClick={() => setShowUserMenu(!showUserMenu)}
                    className="flex items-center gap-2 px-3 py-2 rounded-xl bg-void-800/50 hover:bg-void-700/50 transition-colors"
                  >
                    <div className="w-8 h-8 rounded-full bg-nebula-purple/30 flex items-center justify-center">
                      {user.avatar_url ? (
                        <img src={user.avatar_url} alt="" className="w-8 h-8 rounded-full" />
                      ) : (
                        <User className="w-4 h-4 text-nebula-violet" />
                      )}
                    </div>
                    <span className="hidden sm:block text-star-white text-sm max-w-[120px] truncate">
                      {user.name || user.email?.split('@')[0]}
                    </span>
                    <ChevronDown className={cn(
                      "w-4 h-4 text-star-white/60 transition-transform",
                      showUserMenu && "rotate-180"
                    )} />
                  </button>
                  
                  <AnimatePresence>
                    {showUserMenu && (
                      <>
                        {/* Backdrop */}
                        <div 
                          className="fixed inset-0 z-[100]" 
                          onClick={() => setShowUserMenu(false)}
                          style={{ pointerEvents: 'auto' }}
                        />
                        
                        <motion.div
                          initial={{ opacity: 0, y: 10, scale: 0.95 }}
                          animate={{ opacity: 1, y: 0, scale: 1 }}
                          exit={{ opacity: 0, y: 10, scale: 0.95 }}
                          className="absolute right-0 mt-2 w-56 py-2 rounded-xl bg-void-800 border border-void-600 shadow-xl z-[101]"
                          style={{ pointerEvents: 'auto' }}
                        >
                          {/* User info */}
                          <div className="px-4 py-3 border-b border-void-600">
                            <p className="text-star-white font-medium truncate">
                              {user.name || 'User'}
                            </p>
                            <p className="text-star-white/60 text-sm truncate">
                              {user.email}
                            </p>
                          </div>
                          
                          <div className="py-1">
                            <button 
                              onClick={handleOpenProjects}
                              className="flex items-center gap-3 px-4 py-2 text-sm text-star-white/80 hover:bg-void-700 w-full text-left"
                            >
                              <FolderOpen className="w-4 h-4" />
                              My Projects
                            </button>
                            <button 
                              onClick={handleOpenSettings}
                              className="flex items-center gap-3 px-4 py-2 text-sm text-star-white/80 hover:bg-void-700 w-full text-left"
                            >
                              <Settings className="w-4 h-4" />
                              Settings
                            </button>
                          </div>
                          
                          <div className="border-t border-void-600 pt-1">
                            <button 
                              onClick={handleLogout}
                              className="flex items-center gap-3 px-4 py-2 text-sm text-red-400 hover:bg-void-700 w-full"
                            >
                              <LogOut className="w-4 h-4" />
                              Sign Out
                            </button>
                          </div>
                        </motion.div>
                      </>
                    )}
                  </AnimatePresence>
                </div>
              ) : (
                <button 
                  onClick={() => setShowSignIn(true)}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl bg-nebula-purple hover:bg-nebula-violet text-white text-sm font-medium transition-colors"
                >
                  <LogIn className="w-4 h-4" />
                  <span>Sign In</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </header>
      
      {/* Secondary Nav - Progress Steps (only show when working on a project) */}
      {media && (
        <nav className="relative z-10 border-b border-void-700/30 backdrop-blur-sm bg-void-900/50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-center h-12 gap-1">
              {['upload', 'processing', 'highlights', 'export'].map((s, i) => {
                const steps = ['Upload', 'Process', 'Select', 'Export']
                const isActive = step === s
                const isPast = ['upload', 'processing', 'highlights', 'export'].indexOf(step) > i
                
                return (
                  <div key={s} className="flex items-center">
                    <div
                      className={cn(
                        'px-3 py-1 rounded-full text-xs font-medium transition-all duration-300',
                        isActive 
                          ? 'bg-nebula-purple text-white' 
                          : isPast 
                          ? 'bg-aurora-green/20 text-aurora-green'
                          : 'bg-void-800/50 text-star-white/40'
                      )}
                    >
                      {steps[i]}
                    </div>
                    {i < 3 && (
                      <div className={cn(
                        'w-6 h-0.5 mx-1',
                        isPast ? 'bg-aurora-green/50' : 'bg-void-700'
                      )} />
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </nav>
      )}
      
      {/* Modals */}
      <SignInModal isOpen={showSignIn} onClose={() => setShowSignIn(false)} />
      <SettingsModal isOpen={showSettings} onClose={() => setShowSettings(false)} />
      <ProjectsModal isOpen={showProjects} onClose={() => setShowProjects(false)} />
    </>
  )
}
