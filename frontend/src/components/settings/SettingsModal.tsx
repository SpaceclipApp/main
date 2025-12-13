'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, User, Palette, Bell, Shield, CreditCard } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/store/auth'
import { useProjectStore } from '@/store/project'
import { AvatarUpload } from './AvatarUpload'
import { updateUserProfile } from '@/lib/api'

interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
}

const tabs = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'preferences', label: 'Preferences', icon: Palette },
  { id: 'notifications', label: 'Notifications', icon: Bell },
]

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState('profile')
  const { user, updateUser, isAuthenticated } = useAuthStore()
  const { selectedPlatforms, togglePlatform, audiogramStyle, setAudiogramStyle } = useProjectStore()
  const [name, setName] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  
  // Sync local name state with user from store (prevents stale data)
  useEffect(() => {
    if (isOpen && user?.name !== undefined) {
      setName(user.name || '')
    }
  }, [isOpen, user?.name])
  
  // Close modal if user logs out while it's open
  useEffect(() => {
    if (!isAuthenticated && isOpen) {
      onClose()
    }
  }, [isAuthenticated, isOpen, onClose])
  
  const handleSaveProfile = async () => {
    setIsSaving(true)
    try {
      // Save to backend
      const updatedUser = await updateUserProfile({ name })
      // Update local store with backend response
      updateUser({ name: updatedUser.name })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (error) {
      console.error('Failed to save profile:', error)
    } finally {
      setIsSaving(false)
    }
  }
  
  const handleAvatarChange = async (avatarUrl: string) => {
    try {
      // Save to backend
      const updatedUser = await updateUserProfile({ avatar_url: avatarUrl })
      // Update local store with backend response
      updateUser({ avatar_url: updatedUser.avatar_url })
    } catch (error) {
      console.error('Failed to save avatar:', error)
      // Still update local store for optimistic UI
      updateUser({ avatar_url: avatarUrl })
    }
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
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
          />
          
          {/* Modal */}
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-2xl max-h-[80vh] overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="glass-card relative">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-void-700">
                  <h2 className="text-xl font-bold text-star-white">Settings</h2>
                  <button
                    onClick={onClose}
                    className="p-2 rounded-lg text-star-white/60 hover:text-star-white hover:bg-void-700 transition-colors"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
                
                <div className="flex">
                  {/* Sidebar */}
                  <div className="w-48 border-r border-void-700 p-4">
                    {tabs.map((tab) => {
                      const Icon = tab.icon
                      return (
                        <button
                          key={tab.id}
                          onClick={() => setActiveTab(tab.id)}
                          className={cn(
                            'w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors mb-1',
                            activeTab === tab.id
                              ? 'bg-nebula-purple/20 text-nebula-violet'
                              : 'text-star-white/60 hover:text-star-white hover:bg-void-700'
                          )}
                        >
                          <Icon className="w-4 h-4" />
                          {tab.label}
                        </button>
                      )
                    })}
                  </div>
                  
                  {/* Content */}
                  <div className="flex-1 p-6 overflow-y-auto max-h-[60vh]">
                    {activeTab === 'profile' && (
                      <div className="space-y-6">
                        {/* Avatar */}
                        <div>
                          <label className="block text-star-white/60 text-sm mb-3">Profile Picture</label>
                          <AvatarUpload 
                            currentAvatar={user?.avatar_url}
                            onAvatarChange={handleAvatarChange}
                          />
                          <p className="text-star-white/40 text-xs mt-2">
                            Click to upload an image{user?.wallet_address ? ' or choose from your NFTs' : ''}
                          </p>
                        </div>
                        
                        <div>
                          <label className="block text-star-white/60 text-sm mb-2">Display Name</label>
                          <input
                            type="text"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            className="w-full px-4 py-3 rounded-xl bg-void-800 border border-void-600 text-star-white focus:outline-none focus:border-nebula-purple transition-colors"
                          />
                        </div>
                        
                        <div>
                          <label className="block text-star-white/60 text-sm mb-2">Email</label>
                          <input
                            type="email"
                            value={user?.email || ''}
                            disabled
                            className="w-full px-4 py-3 rounded-xl bg-void-900 border border-void-700 text-star-white/50 cursor-not-allowed"
                          />
                          <p className="text-star-white/40 text-xs mt-1">Email cannot be changed</p>
                        </div>
                        
                        {user?.wallet_address && (
                          <div>
                            <label className="block text-star-white/60 text-sm mb-2">Wallet Address</label>
                            <div className="px-4 py-3 rounded-xl bg-void-900 border border-void-700 text-star-white/50 font-mono text-sm">
                              {user.wallet_address.slice(0, 6)}...{user.wallet_address.slice(-4)}
                            </div>
                          </div>
                        )}
                        
                        <button
                          onClick={handleSaveProfile}
                          disabled={isSaving}
                          className="px-4 py-2 rounded-lg bg-nebula-purple hover:bg-nebula-violet text-white text-sm transition-colors disabled:opacity-50"
                        >
                          {isSaving ? 'Saving...' : saved ? 'Saved!' : 'Save Changes'}
                        </button>
                      </div>
                    )}
                    
                    {activeTab === 'preferences' && (
                      <div className="space-y-6">
                        <div>
                          <h3 className="text-star-white font-medium mb-3">Default Export Platforms</h3>
                          <p className="text-star-white/40 text-sm mb-4">
                            Select which platforms are pre-selected when exporting clips
                          </p>
                          <div className="grid grid-cols-2 gap-2">
                            {['instagram_reels', 'tiktok', 'youtube_shorts', 'twitter'].map((platform) => (
                              <button
                                key={platform}
                                onClick={() => togglePlatform(platform as any)}
                                className={cn(
                                  'px-3 py-2 rounded-lg text-sm transition-colors border',
                                  selectedPlatforms.includes(platform as any)
                                    ? 'border-nebula-purple bg-nebula-purple/10 text-nebula-violet'
                                    : 'border-void-600 text-star-white/60 hover:border-void-500'
                                )}
                              >
                                {platform.replace('_', ' ')}
                              </button>
                            ))}
                          </div>
                        </div>
                        
                        <div>
                          <h3 className="text-star-white font-medium mb-3">Default Audiogram Style</h3>
                          <div className="grid grid-cols-2 gap-2">
                            {['cosmic', 'neon', 'sunset', 'minimal'].map((style) => (
                              <button
                                key={style}
                                onClick={() => setAudiogramStyle(style)}
                                className={cn(
                                  'px-3 py-2 rounded-lg text-sm transition-colors border capitalize',
                                  audiogramStyle === style
                                    ? 'border-nebula-purple bg-nebula-purple/10 text-nebula-violet'
                                    : 'border-void-600 text-star-white/60 hover:border-void-500'
                                )}
                              >
                                {style}
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                    
                    {activeTab === 'notifications' && (
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <h3 className="text-star-white font-medium">Email Notifications</h3>
                            <p className="text-star-white/40 text-sm">Receive updates about your clips</p>
                          </div>
                          <button className="w-12 h-6 rounded-full bg-nebula-purple relative">
                            <div className="absolute right-1 top-1 w-4 h-4 rounded-full bg-white" />
                          </button>
                        </div>
                        
                        <div className="flex items-center justify-between">
                          <div>
                            <h3 className="text-star-white font-medium">Processing Complete</h3>
                            <p className="text-star-white/40 text-sm">Notify when clips are ready</p>
                          </div>
                          <button className="w-12 h-6 rounded-full bg-nebula-purple relative">
                            <div className="absolute right-1 top-1 w-4 h-4 rounded-full bg-white" />
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  )
}

