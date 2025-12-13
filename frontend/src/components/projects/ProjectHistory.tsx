'use client'

import { useEffect, useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Clock, Film, Mic, Play, Scissors, ChevronRight, Loader2, Lock, MoreVertical, Archive, Trash2, CheckSquare, Square, X } from 'lucide-react'
import { useProjectStore } from '@/store/project'
import { useAuthStore } from '@/store/auth'
import { listProjects, deleteProject, archiveProject, deleteProjects, archiveProjects, ProjectSummary } from '@/lib/api'
import { formatDuration, cn } from '@/lib/utils'

export function ProjectHistory() {
  const [projects, setProjects] = useState<ProjectSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadingId, setLoadingId] = useState<string | null>(null)
  const [showAll, setShowAll] = useState(false)
  const [menuOpen, setMenuOpen] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)
  const [selectMode, setSelectMode] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [bulkAction, setBulkAction] = useState<'archive' | 'delete' | null>(null)
  const [confirmBulkDelete, setConfirmBulkDelete] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  
  const { loadProject } = useProjectStore()
  const { isAuthenticated } = useAuthStore()
  
  const fetchProjects = () => {
    if (!isAuthenticated) {
      setIsLoading(false)
      setProjects([])
      return
    }
    
    listProjects()
      .then(data => {
        setProjects(data || [])
        setIsLoading(false)
      })
      .catch(() => {
        setProjects([])
        setIsLoading(false)
      })
  }
  
  useEffect(() => {
    fetchProjects()
  }, [isAuthenticated])
  
  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(null)
        setConfirmDelete(null)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])
  
  // Exit select mode when no projects selected
  useEffect(() => {
    if (selectMode && selectedIds.size === 0) {
      setSelectMode(false)
    }
  }, [selectedIds.size, selectMode])
  
  const handleLoadProject = async (mediaId: string) => {
    if (menuOpen || confirmDelete || selectMode) return // Don't load if menu is open or in select mode
    setLoadingId(mediaId)
    try {
      await loadProject(mediaId)
    } catch (error) {
      console.error('Failed to load project:', error)
    } finally {
      setLoadingId(null)
    }
  }
  
  const handleArchive = async (e: React.MouseEvent, mediaId: string) => {
    e.stopPropagation()
    // Optimistic update
    const previousProjects = [...projects]
    setProjects(prev => prev.filter(p => p.media_id !== mediaId))
    setMenuOpen(null)
    
    try {
      await archiveProject(mediaId)
      // Refetch to ensure sync with backend
      fetchProjects()
    } catch (error) {
      console.error('Failed to archive project:', error)
      // Revert optimistic update on failure
      setProjects(previousProjects)
      // Refetch to get correct state
      fetchProjects()
    }
  }
  
  const handleDelete = async (e: React.MouseEvent, mediaId: string) => {
    e.stopPropagation()
    if (confirmDelete !== mediaId) {
      setConfirmDelete(mediaId)
      return
    }
    
    // Optimistic update
    const previousProjects = [...projects]
    setProjects(prev => prev.filter(p => p.media_id !== mediaId))
    setMenuOpen(null)
    setConfirmDelete(null)
    
    try {
      await deleteProject(mediaId)
      // Refetch to ensure sync with backend
      fetchProjects()
    } catch (error) {
      console.error('Failed to delete project:', error)
      // Revert optimistic update on failure
      setProjects(previousProjects)
      // Refetch to get correct state
      fetchProjects()
    }
  }
  
  const toggleMenu = (e: React.MouseEvent, mediaId: string) => {
    e.stopPropagation()
    setMenuOpen(menuOpen === mediaId ? null : mediaId)
    setConfirmDelete(null)
  }
  
  const toggleSelect = (e: React.MouseEvent, mediaId: string) => {
    e.stopPropagation()
    const newSelected = new Set(selectedIds)
    if (newSelected.has(mediaId)) {
      newSelected.delete(mediaId)
    } else {
      newSelected.add(mediaId)
    }
    setSelectedIds(newSelected)
    if (!selectMode && newSelected.size > 0) {
      setSelectMode(true)
    }
  }
  
  const selectAll = () => {
    const displayedProjects = showAll ? projects : projects.slice(0, 5)
    setSelectedIds(new Set(displayedProjects.map(p => p.media_id)))
    setSelectMode(true)
  }
  
  const clearSelection = () => {
    setSelectedIds(new Set())
    setSelectMode(false)
    setConfirmBulkDelete(false)
  }
  
  const handleBulkArchive = async () => {
    setBulkAction('archive')
    // Optimistic update
    const previousProjects = [...projects]
    const idsToArchive = Array.from(selectedIds)
    setProjects(prev => prev.filter(p => !selectedIds.has(p.media_id)))
    clearSelection()
    
    try {
      await archiveProjects(idsToArchive)
      // Refetch to ensure sync with backend
      fetchProjects()
    } catch (error) {
      console.error('Failed to archive projects:', error)
      // Revert optimistic update on failure
      setProjects(previousProjects)
      // Refetch to get correct state
      fetchProjects()
    } finally {
      setBulkAction(null)
    }
  }
  
  const handleBulkDelete = async () => {
    if (!confirmBulkDelete) {
      setConfirmBulkDelete(true)
      return
    }
    
    setBulkAction('delete')
    // Optimistic update
    const previousProjects = [...projects]
    const idsToDelete = Array.from(selectedIds)
    setProjects(prev => prev.filter(p => !selectedIds.has(p.media_id)))
    clearSelection()
    
    try {
      await deleteProjects(idsToDelete)
      // Refetch to ensure sync with backend
      fetchProjects()
    } catch (error) {
      console.error('Failed to delete projects:', error)
      // Revert optimistic update on failure
      setProjects(previousProjects)
      // Refetch to get correct state
      fetchProjects()
    } finally {
      setBulkAction(null)
      setConfirmBulkDelete(false)
    }
  }
  
  // Always render the container
  return (
    <div className="relative w-full max-w-2xl mx-auto mt-12">
      {!isAuthenticated ? (
        <div className="text-center py-6 px-4 rounded-xl bg-void-800/30 border border-void-700/50">
          <Lock className="w-6 h-6 text-star-white/30 mx-auto mb-3" />
          <p className="text-star-white/50 text-sm">
            Sign in to view your recent projects
          </p>
        </div>
      ) : isLoading ? (
        <div className="text-center text-star-white/60">
          <Loader2 className="w-6 h-6 animate-spin mx-auto" />
        </div>
      ) : projects.length === 0 ? (
        <div className="text-center text-star-white/40 text-sm">
          No recent projects yet
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-star-white/40" />
              <h3 className="text-sm font-medium text-star-white/60">Recent Projects</h3>
              <span className="text-xs text-star-white/30">({projects.length})</span>
            </div>
            
            <div className="flex items-center gap-2">
              {!selectMode ? (
                <button
                  onClick={selectAll}
                  className="text-xs text-star-white/50 hover:text-star-white transition-colors px-2 py-1 rounded hover:bg-void-700"
                >
                  Select All
                </button>
              ) : (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-nebula-violet">{selectedIds.size} selected</span>
                  <button
                    onClick={clearSelection}
                    className="p-1 rounded hover:bg-void-700 text-star-white/50 hover:text-star-white"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          </div>
          
          {/* Bulk Action Bar */}
          <AnimatePresence>
            {selectMode && selectedIds.size > 0 && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="mb-4 p-4 rounded-xl bg-void-800 border border-void-600 flex items-center justify-between"
              >
                <span className="text-sm text-star-white/70">
                  {selectedIds.size} project{selectedIds.size > 1 ? 's' : ''} selected
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleBulkArchive}
                    disabled={bulkAction !== null}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-void-700 hover:bg-void-600 text-star-white/80 text-sm transition-colors disabled:opacity-50"
                  >
                    {bulkAction === 'archive' ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Archive className="w-4 h-4" />
                    )}
                    Archive All
                  </button>
                  <button
                    onClick={handleBulkDelete}
                    disabled={bulkAction !== null}
                    className={cn(
                      "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors disabled:opacity-50",
                      confirmBulkDelete
                        ? "bg-red-500/30 text-red-400 border border-red-500/50"
                        : "bg-red-500/20 hover:bg-red-500/30 text-red-400"
                    )}
                  >
                    {bulkAction === 'delete' ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                    {confirmBulkDelete ? 'Confirm Delete' : 'Delete All'}
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
          
          <div className="grid gap-3">
            <AnimatePresence>
              {(showAll ? projects : projects.slice(0, 5)).map((project, index) => (
                <motion.div
                  key={project.media_id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ delay: index * 0.05 }}
                  onClick={() => selectMode ? toggleSelect({ stopPropagation: () => {} } as React.MouseEvent, project.media_id) : handleLoadProject(project.media_id)}
                  className={cn(
                    'glass-card p-4 cursor-pointer',
                    'hover:border-nebula-purple/50 transition-all duration-200',
                    'flex items-center gap-4 group overflow-hidden',
                    selectedIds.has(project.media_id) && 'border-nebula-purple/60 bg-nebula-purple/5'
                  )}
                >
                  {/* Checkbox for select mode */}
                  {selectMode ? (
                    <button
                      onClick={(e) => toggleSelect(e, project.media_id)}
                      className="flex-shrink-0"
                    >
                      {selectedIds.has(project.media_id) ? (
                        <CheckSquare className="w-5 h-5 text-nebula-violet" />
                      ) : (
                        <Square className="w-5 h-5 text-star-white/30" />
                      )}
                    </button>
                  ) : (
                    <button
                      onClick={(e) => toggleSelect(e, project.media_id)}
                      className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <Square className="w-5 h-5 text-star-white/30 hover:text-star-white/50" />
                    </button>
                  )}
                  
                  <div className={cn(
                    'w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0',
                    project.media_type === 'video' 
                      ? 'bg-red-500/20 text-red-400'
                      : 'bg-nebula-purple/20 text-nebula-violet'
                  )}>
                    {project.media_type === 'video' 
                      ? <Film className="w-5 h-5" />
                      : <Mic className="w-5 h-5" />
                    }
                  </div>
                  
                  <div className="flex-1 min-w-0 overflow-hidden">
                    <h4 className="font-medium text-star-white truncate break-words">
                      {project.title || 'Untitled Project'}
                    </h4>
                    <div className="flex items-center gap-3 text-xs text-star-white/40 mt-1">
                      <span>{formatDuration(project.duration)}</span>
                      {project.highlights_count > 0 && (
                        <span className="flex items-center gap-1">
                          <Play className="w-3 h-3" />
                          {project.highlights_count} highlights
                        </span>
                      )}
                      {project.clips_count > 0 && (
                        <span className="flex items-center gap-1">
                          <Scissors className="w-3 h-3" />
                          {project.clips_count} clips
                        </span>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    {project.status === 'complete' && (
                      <span className="px-2 py-1 rounded text-xs bg-aurora-green/20 text-aurora-green">
                        Complete
                      </span>
                    )}
                    {project.status === 'error' && (
                      <span className="px-2 py-1 rounded text-xs bg-red-500/20 text-red-400">
                        Error
                      </span>
                    )}
                    
                    {/* Action Menu */}
                    <div className="relative" ref={menuOpen === project.media_id ? menuRef : null}>
                      <button
                        onClick={(e) => toggleMenu(e, project.media_id)}
                        className="p-1.5 rounded-lg hover:bg-void-700 transition-colors opacity-0 group-hover:opacity-100"
                      >
                        <MoreVertical className="w-4 h-4 text-star-white/50" />
                      </button>
                      
                      <AnimatePresence>
                        {menuOpen === project.media_id && (
                          <motion.div
                            initial={{ opacity: 0, scale: 0.95, y: -5 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.95, y: -5 }}
                            className="absolute right-0 top-full mt-1 z-50 bg-void-800 border border-void-600 rounded-lg shadow-xl overflow-hidden min-w-[140px]"
                          >
                            <button
                              onClick={(e) => handleArchive(e, project.media_id)}
                              className="w-full px-3 py-2 text-left text-sm text-star-white/80 hover:bg-void-700 flex items-center gap-2"
                            >
                              <Archive className="w-4 h-4" />
                              Archive
                            </button>
                            <button
                              onClick={(e) => handleDelete(e, project.media_id)}
                              className={cn(
                                "w-full px-3 py-2 text-left text-sm flex items-center gap-2",
                                confirmDelete === project.media_id
                                  ? "bg-red-500/20 text-red-400"
                                  : "text-red-400 hover:bg-red-500/10"
                              )}
                            >
                              <Trash2 className="w-4 h-4" />
                              {confirmDelete === project.media_id ? 'Confirm Delete' : 'Delete'}
                            </button>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                    
                    {loadingId === project.media_id ? (
                      <Loader2 className="w-5 h-5 text-nebula-violet animate-spin" />
                    ) : (
                      <ChevronRight className="w-5 h-5 text-star-white/30 group-hover:text-nebula-violet transition-colors" />
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
          
          {projects.length > 5 && !showAll && (
            <button 
              onClick={() => setShowAll(true)}
              className="w-full text-center text-nebula-violet hover:text-nebula-pink text-sm mt-4 py-2 rounded-lg hover:bg-void-800/50 transition-colors"
            >
              Show {projects.length - 5} more projects...
            </button>
          )}
          
          {showAll && projects.length > 5 && (
            <button 
              onClick={() => setShowAll(false)}
              className="w-full text-center text-star-white/40 hover:text-star-white text-sm mt-4 py-2 rounded-lg hover:bg-void-800/50 transition-colors"
            >
              Show less
            </button>
          )}
        </>
      )}
    </div>
  )
}
