'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, FolderOpen, Film, Mic, Play, Scissors, ChevronRight, Plus, Loader2, Trash2 } from 'lucide-react'
import { cn, formatDuration } from '@/lib/utils'
import { useProjectStore } from '@/store/project'
import { listProjects, ProjectSummary } from '@/lib/api'

interface ProjectsModalProps {
  isOpen: boolean
  onClose: () => void
}

export function ProjectsModal({ isOpen, onClose }: ProjectsModalProps) {
  const [projects, setProjects] = useState<ProjectSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadingId, setLoadingId] = useState<string | null>(null)
  
  const { loadProject } = useProjectStore()
  
  useEffect(() => {
    if (isOpen) {
      loadProjects()
    }
  }, [isOpen])
  
  const loadProjects = async () => {
    setIsLoading(true)
    try {
      const data = await listProjects()
      setProjects(data || [])
    } catch (error) {
      console.error('Failed to load projects:', error)
      setProjects([])
    } finally {
      setIsLoading(false)
    }
  }
  
  const handleLoadProject = async (mediaId: string) => {
    setLoadingId(mediaId)
    try {
      await loadProject(mediaId)
      onClose()
    } catch (error) {
      console.error('Failed to load project:', error)
    } finally {
      setLoadingId(null)
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
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-nebula-purple/20 flex items-center justify-center">
                      <FolderOpen className="w-5 h-5 text-nebula-violet" />
                    </div>
                    <div>
                      <h2 className="text-xl font-bold text-star-white">My Projects</h2>
                      <p className="text-star-white/60 text-sm">{projects.length} projects</p>
                    </div>
                  </div>
                  <button
                    onClick={onClose}
                    className="p-2 rounded-lg text-star-white/60 hover:text-star-white hover:bg-void-700 transition-colors"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
                
                {/* Content */}
                <div className="p-6 overflow-y-auto max-h-[60vh]">
                  {isLoading ? (
                    <div className="flex items-center justify-center py-12">
                      <Loader2 className="w-8 h-8 text-nebula-violet animate-spin" />
                    </div>
                  ) : projects.length === 0 ? (
                    <div className="text-center py-12">
                      <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-void-700 flex items-center justify-center">
                        <FolderOpen className="w-8 h-8 text-star-white/30" />
                      </div>
                      <p className="text-star-white/60">No projects yet</p>
                      <p className="text-star-white/40 text-sm mt-1">
                        Upload a video or audio to get started
                      </p>
                    </div>
                  ) : (
                    <div className="grid gap-3">
                      {projects.map((project) => (
                        <motion.div
                          key={project.media_id}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          onClick={() => handleLoadProject(project.media_id)}
                          className={cn(
                            'p-4 rounded-xl cursor-pointer',
                            'border border-void-600 hover:border-nebula-purple/50',
                            'bg-void-800/30 hover:bg-void-800/50 transition-all duration-200',
                            'flex items-center gap-4 group'
                          )}
                        >
                          <div className={cn(
                            'w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0',
                            project.media_type === 'video' 
                              ? 'bg-red-500/20 text-red-400'
                              : 'bg-nebula-purple/20 text-nebula-violet'
                          )}>
                            {project.media_type === 'video' 
                              ? <Film className="w-6 h-6" />
                              : <Mic className="w-6 h-6" />
                            }
                          </div>
                          
                          <div className="flex-1 min-w-0">
                            <h4 className="font-medium text-star-white truncate">
                              {project.title || 'Untitled Project'}
                            </h4>
                            <div className="flex items-center gap-3 text-sm text-star-white/40 mt-1">
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
                            
                            {loadingId === project.media_id ? (
                              <Loader2 className="w-5 h-5 text-nebula-violet animate-spin" />
                            ) : (
                              <ChevronRight className="w-5 h-5 text-star-white/30 group-hover:text-nebula-violet transition-colors" />
                            )}
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  )
}





