'use client'

import { useEffect, useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, Loader2, X, Play } from 'lucide-react'
import { listProjects, getProjectStatus, ProjectSummary, ProjectStatusResponse } from '@/lib/api'
import { useProjectStore } from '@/store/project'
import { useAuthStore } from '@/store/auth'
import { cn } from '@/lib/utils'

/**
 * Parse status message to extract chunk progress
 */
function parseChunkProgress(message: string | null): { current: number; total: number; percentage?: number } | null {
  if (!message) return null
  
  const match = message.match(/(?:chunk|clip)\s+(\d+)\s*\/\s*(\d+)(?:\s*\((\d+)%\))?/i)
  if (match) {
    return {
      current: parseInt(match[1], 10),
      total: parseInt(match[2], 10),
      percentage: match[3] ? parseInt(match[3], 10) : undefined,
    }
  }
  
  return null
}

interface ProcessingItem {
  media_id: string
  title: string
  status: string
  status_message: string | null
  chunkProgress: { current: number; total: number; percentage?: number } | null
}

const POLL_INTERVAL = 3000 // 3 seconds for queue polling (less frequent than active processing)

export function ProcessingQueue() {
  const { isAuthenticated } = useAuthStore()
  const { loadProject, setStep } = useProjectStore()
  const [isOpen, setIsOpen] = useState(false)
  const [items, setItems] = useState<ProcessingItem[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const pollingRefs = useRef<Map<string, NodeJS.Timeout>>(new Map())
  // Track auth state to prevent polling after logout
  const isAuthenticatedRef = useRef(isAuthenticated)
  
  // Keep ref in sync with state
  useEffect(() => {
    isAuthenticatedRef.current = isAuthenticated
  }, [isAuthenticated])
  
  /**
   * Determine if a project status is active (should be in queue)
   */
  const isActiveStatus = (status: string): boolean => {
    const statusLower = status.toLowerCase()
    return statusLower === 'pending' || 
           statusLower === 'downloading' || 
           statusLower === 'transcribing' || 
           statusLower === 'analyzing'
  }
  
  /**
   * Fetch projects and populate queue with active ones
   */
  const rehydrateQueue = async () => {
    if (!isAuthenticated) {
      setItems([])
      return
    }
    
    setIsLoading(true)
    try {
      const projects = await listProjects(false)
      const activeProjects = projects.filter(p => isActiveStatus(p.status))
      
      // Fetch initial status for each active project
      const queueItemsPromises = activeProjects.map(async (p) => {
        try {
          const status = await getProjectStatus(p.media_id)
          
          // Double-check status is still active (might have completed between list and status fetch)
          if (!isActiveStatus(status.status)) {
            return null
          }
          
          const chunkProgress = parseChunkProgress(status.status_message)
          
          return {
            media_id: p.media_id,
            title: p.title || 'Untitled Project',
            status: status.status,
            status_message: status.status_message,
            chunkProgress,
          } as ProcessingItem
        } catch (error) {
          // If status fetch fails, still add to queue but without status_message
          return {
            media_id: p.media_id,
            title: p.title || 'Untitled Project',
            status: p.status,
            status_message: null,
            chunkProgress: null,
          } as ProcessingItem
        }
      })
      
      const queueItems = (await Promise.all(queueItemsPromises)).filter(
        (item): item is ProcessingItem => item !== null
      )
      
      setItems(queueItems)
      
      // Start polling for each active project
      queueItems.forEach(item => {
        startPolling(item.media_id)
      })
    } catch (error) {
      console.error('Failed to rehydrate processing queue:', error)
    } finally {
      setIsLoading(false)
    }
  }
  
  /**
   * Poll a single project's status
   * Auth-aware: stops immediately if user is no longer authenticated
   */
  const pollProjectStatus = async (mediaId: string) => {
    // Auth guard: don't poll if logged out
    if (!isAuthenticatedRef.current) {
      stopPolling(mediaId)
      return
    }
    
    try {
      const status: ProjectStatusResponse = await getProjectStatus(mediaId)
      
      // Double-check auth after async call (user might have logged out)
      if (!isAuthenticatedRef.current) {
        stopPolling(mediaId)
        return
      }
      
      // Check if still active
      if (!isActiveStatus(status.status)) {
        // Remove from queue if completed or errored
        setItems(prev => prev.filter(item => item.media_id !== mediaId))
        stopPolling(mediaId)
        return
      }
      
      // Update item with latest status
      const chunkProgress = parseChunkProgress(status.status_message)
      
      setItems(prev => prev.map(item => 
        item.media_id === mediaId
          ? {
              ...item,
              status: status.status,
              status_message: status.status_message,
              chunkProgress,
            }
          : item
      ))
    } catch (error) {
      // Silent failure: log to console, don't surface to UI
      console.error(`Failed to poll status for ${mediaId}:`, error)
      // On error, remove from queue (project might be deleted)
      setItems(prev => prev.filter(item => item.media_id !== mediaId))
      stopPolling(mediaId)
    }
  }
  
  /**
   * Start polling a project
   */
  const startPolling = (mediaId: string) => {
    // Stop any existing polling for this project
    stopPolling(mediaId)
    
    // Initial poll
    pollProjectStatus(mediaId)
    
    // Set up interval
    const interval = setInterval(() => {
      pollProjectStatus(mediaId)
    }, POLL_INTERVAL)
    
    pollingRefs.current.set(mediaId, interval)
  }
  
  /**
   * Stop polling a project
   */
  const stopPolling = (mediaId: string) => {
    const interval = pollingRefs.current.get(mediaId)
    if (interval) {
      clearInterval(interval)
      pollingRefs.current.delete(mediaId)
    }
  }
  
  /**
   * Stop all polling - used on logout
   */
  const stopAllPolling = () => {
    pollingRefs.current.forEach((interval) => clearInterval(interval))
    pollingRefs.current.clear()
  }
  
  /**
   * Handle clicking on a queue item - navigate to project
   */
  const handleItemClick = async (mediaId: string) => {
    try {
      await loadProject(mediaId)
      setStep('processing')
      setIsOpen(false)
    } catch (error) {
      console.error('Failed to load project:', error)
    }
  }
  
  // Rehydrate on mount and when auth state changes
  useEffect(() => {
    if (isAuthenticated) {
      rehydrateQueue()
    } else {
      // Explicit teardown on logout: stop all polling immediately
      stopAllPolling()
      setItems([])
    }
    
    return () => {
      // Clean up all polling intervals on unmount
      stopAllPolling()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated])
  
  if (!isAuthenticated) {
    return null
  }
  
  // Don't render if no items and not loading
  if (items.length === 0 && !isLoading) {
    return null
  }
  
  return (
    <div className="fixed bottom-4 right-4 z-50">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card border border-void-600 shadow-xl w-80"
      >
        {/* Header */}
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-full flex items-center justify-between p-3 hover:bg-void-800/50 transition-colors rounded-t-lg"
        >
          <div className="flex items-center gap-2">
            {isLoading ? (
              <Loader2 className="w-4 h-4 text-nebula-violet animate-spin" />
            ) : items.length > 0 ? (
              <div className="w-2 h-2 rounded-full bg-nebula-violet animate-pulse" />
            ) : null}
            <span className="text-sm font-medium text-star-white">
              Processing {items.length > 0 && `(${items.length})`}
            </span>
          </div>
          {items.length > 0 && (
            <ChevronDown
              className={cn(
                "w-4 h-4 text-star-white/60 transition-transform",
                isOpen && "rotate-180"
              )}
            />
          )}
        </button>
        
        {/* Queue items */}
        <AnimatePresence>
          {isOpen && items.length > 0 && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden"
            >
              <div className="max-h-96 overflow-y-auto">
                {items.map((item, index) => (
                  <motion.div
                    key={item.media_id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="border-t border-void-700/50 p-3 hover:bg-void-800/30 transition-colors cursor-pointer"
                    onClick={() => handleItemClick(item.media_id)}
                  >
                    <div className="flex items-start gap-2">
                      <Loader2 className="w-3 h-3 text-nebula-violet animate-spin mt-0.5 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-star-white truncate">
                          {item.title}
                        </p>
                        {item.status_message && (
                          <p className="text-xs text-star-white/60 mt-0.5 line-clamp-1">
                            {item.status_message}
                          </p>
                        )}
                        {item.chunkProgress && (
                          <p className="text-xs text-nebula-violet font-mono mt-0.5">
                            Chunk {item.chunkProgress.current}/{item.chunkProgress.total}
                            {item.chunkProgress.percentage !== undefined && ` (${item.chunkProgress.percentage}%)`}
                          </p>
                        )}
                      </div>
                      <Play className="w-3 h-3 text-star-white/40 flex-shrink-0 mt-0.5" />
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  )
}
