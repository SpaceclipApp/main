'use client'

import { useEffect, useState, useRef, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Loader2, Wand2, FileAudio, MessageSquare, Sparkles, AlertCircle, RefreshCw } from 'lucide-react'
import { useProjectStore } from '@/store/project'
import { transcribeMedia, analyzeHighlights, getProject, getProjectStatus } from '@/lib/api'
import { formatDuration } from '@/lib/utils'

const POLL_INTERVAL = 2000 // 2 seconds

const steps = [
  { id: 'transcribe', label: 'Transcribing audio', icon: FileAudio },
  { id: 'analyze', label: 'Finding highlights', icon: Sparkles },
  { id: 'complete', label: 'Ready to clip!', icon: Wand2 },
]

/**
 * Parse status message to extract chunk progress (e.g., "Transcribing chunk 2/5 (40%)")
 * Returns { current: number, total: number, percentage: number } or null if not found
 */
function parseChunkProgress(message: string | null): { current: number; total: number; percentage?: number } | null {
  if (!message) return null
  
  // Match patterns like "chunk 2/5" or "clip 3/6" with optional percentage
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

/**
 * Parse status message for detected language (e.g., "Language: English" or "Detected language: en")
 */
function parseLanguage(message: string | null): string | null {
  if (!message) return null
  
  const match = message.match(/(?:language|detected language):\s*([a-z]+(?:\s+[a-z]+)?)/i)
  if (match) {
    return match[1]
  }
  
  return null
}

/**
 * Parse status message for time range (e.g., "Time range: 0:00 to 10:00")
 */
function parseTimeRange(message: string | null): { start: string; end: string } | null {
  if (!message) return null
  
  const match = message.match(/time\s+range:\s*([\d:]+)\s+to\s+([\d:]+)/i)
  if (match) {
    return {
      start: match[1],
      end: match[2],
    }
  }
  
  return null
}

/**
 * Determine processing stage from status
 */
function getStageFromStatus(status: string): {
  stage: 'downloading' | 'chunking' | 'transcribing' | 'analyzing' | 'highlighting' | 'generating' | 'complete' | 'error' | 'unknown'
  isIndeterminate: boolean
} {
  const statusLower = status.toLowerCase()
  
  if (statusLower === 'pending' || statusLower === 'downloading') {
    return { stage: 'downloading', isIndeterminate: true }
  }
  if (statusLower === 'transcribing') {
    // Check if chunking is mentioned
    if (statusLower.includes('chunk')) {
      return { stage: 'chunking', isIndeterminate: false }
    }
    return { stage: 'transcribing', isIndeterminate: true }
  }
  if (statusLower === 'analyzing') {
    if (statusLower.includes('highlight')) {
      return { stage: 'highlighting', isIndeterminate: true }
    }
    return { stage: 'analyzing', isIndeterminate: true }
  }
  if (statusLower.includes('generating') || statusLower.includes('clip')) {
    return { stage: 'generating', isIndeterminate: false }
  }
  if (statusLower === 'complete') {
    return { stage: 'complete', isIndeterminate: false }
  }
  if (statusLower === 'error') {
    return { stage: 'error', isIndeterminate: false }
  }
  
  return { stage: 'unknown', isIndeterminate: true }
}

export function ProcessingView() {
  const { 
    media, 
    transcription: existingTranscription,
    setTranscription, 
    setHighlights, 
    setStep, 
    processingStatus,
    setProcessing,
    progress,
    reset
  } = useProjectStore()
  
  const [currentStep, setCurrentStep] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [statusMessage, setStatusMessage] = useState<string | null>(null)
  const [chunkProgress, setChunkProgress] = useState<{ current: number; total: number; percentage?: number } | null>(null)
  const [detectedLanguage, setDetectedLanguage] = useState<string | null>(null)
  const [chunkTimeRange, setChunkTimeRange] = useState<{ start: string; end: string } | null>(null)
  const [currentStage, setCurrentStage] = useState<'downloading' | 'chunking' | 'transcribing' | 'analyzing' | 'highlighting' | 'generating' | 'complete' | 'error' | 'unknown'>('unknown')
  const [isIndeterminate, setIsIndeterminate] = useState(true)
  const [elapsedTime, setElapsedTime] = useState(0)
  const processingRef = useRef(false)
  const pollingRef = useRef<NodeJS.Timeout | null>(null)
  const startTimeRef = useRef<number>(Date.now())
  
  // Update elapsed time
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedTime(Math.floor((Date.now() - startTimeRef.current) / 1000))
    }, 1000)
    return () => clearInterval(timer)
  }, [])
  
  // Status polling function
  const pollStatus = useCallback(async () => {
    if (!media) return
    
    try {
      const status = await getProjectStatus(media.id)
      
      // Parse status message for chunk progress
      const chunkInfo = parseChunkProgress(status.status_message)
      if (chunkInfo) {
        setChunkProgress(chunkInfo)
      } else {
        setChunkProgress(null)
      }
      
      // Parse detected language from status message
      const language = parseLanguage(status.status_message)
      if (language) {
        setDetectedLanguage(language)
      }
      
      // Parse time range from status message
      const timeRange = parseTimeRange(status.status_message)
      if (timeRange) {
        setChunkTimeRange(timeRange)
      }
      
      // Determine stage and whether progress is quantifiable
      const stageInfo = getStageFromStatus(status.status)
      setCurrentStage(stageInfo.stage)
      setIsIndeterminate(stageInfo.isIndeterminate && !chunkInfo)
      
      // Use backend status_message as single source of truth
      // Only fall back to derived message if status_message is completely missing
      const displayMessage = status.status_message || 
        (status.status === 'complete' ? 'Processing complete!' :
         status.status === 'error' ? 'Processing failed' :
         'Processing...')
      setStatusMessage(displayMessage)
      
      // Update store with status (but don't use fake progress values)
      // Only use backend progress if it's meaningful (not 0 or 1 when indeterminate)
      const meaningfulProgress = (!stageInfo.isIndeterminate || chunkInfo) ? status.progress : undefined
      setProcessing(displayMessage, meaningfulProgress ?? 0)
      
      // Update current step based on status
      if (status.status === 'transcribing' || status.status === 'downloading') {
        setCurrentStep(0)
      } else if (status.status === 'analyzing') {
        setCurrentStep(1)
      } else if (status.status === 'complete') {
        setCurrentStep(2)
      }
      
      // Handle completion
      if (status.status === 'complete') {
        // Stop polling
        if (pollingRef.current) {
          clearInterval(pollingRef.current)
          pollingRef.current = null
        }
        
        // Fetch full project data
        const fullProject = await getProject(media.id)
        if (fullProject.transcription) {
          setTranscription(fullProject.transcription)
        }
        if (fullProject.highlights) {
          setHighlights(fullProject.highlights)
        }
        
        // Transition after a moment
        setTimeout(() => {
          setStep('highlights')
        }, 1500)
      }
      
      // Handle error
      if (status.status === 'error') {
        if (pollingRef.current) {
          clearInterval(pollingRef.current)
          pollingRef.current = null
        }
        setError(status.error || 'Processing failed')
        processingRef.current = false
      }
      
    } catch (err) {
      console.error('Status polling error:', err)
      // Don't stop polling on transient errors
    }
  }, [media, setProcessing, setTranscription, setHighlights, setStep])
  
  // Clean up polling on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
      }
    }
  }, [])
  
  useEffect(() => {
    if (!media) return
    
    // Prevent double-invocation from React Strict Mode
    if (processingRef.current) return
    processingRef.current = true
    
    const process = async () => {
      try {
        // Step 1: Transcribe (skip if already done)
        setCurrentStep(0)
        setCurrentStage('transcribing')
        setIsIndeterminate(true)
        
        let transcription = existingTranscription
        if (!transcription) {
          // Start polling for status updates immediately
          // This will show real backend status messages
          pollingRef.current = setInterval(pollStatus, POLL_INTERVAL)
          
          // Initial status message (will be overridden by polling)
          setStatusMessage('Starting transcription...')
          setProcessing('Starting transcription...', 0)
          
          transcription = await transcribeMedia(media.id)
          setTranscription(transcription)
          
          // Stop polling after transcription completes
          if (pollingRef.current) {
            clearInterval(pollingRef.current)
            pollingRef.current = null
          }
        }
        
        // Step 2: Analyze highlights
        setCurrentStep(1)
        setCurrentStage('analyzing')
        setIsIndeterminate(true)
        setStatusMessage('Finding highlights with AI...')
        setProcessing('Finding highlights with AI...', 0)
        
        // Request more highlights for longer content
        const highlightCount = media.duration > 1800 ? 20 : media.duration > 600 ? 15 : 10
        
        const highlights = await analyzeHighlights(media.id, {
          max_highlights: highlightCount,
          min_duration: 15,
          max_duration: 90,
        })
        setHighlights(highlights)
        
        // Complete
        setCurrentStep(2)
        setCurrentStage('complete')
        setIsIndeterminate(false)
        setStatusMessage('Processing complete!')
        setProcessing('Processing complete!', 1)
        
        // Wait a moment before transitioning
        setTimeout(() => {
          setStep('highlights')
        }, 1500)
        
      } catch (err: any) {
        console.error('Processing error:', err)
        
        // Stop polling on error
        if (pollingRef.current) {
          clearInterval(pollingRef.current)
          pollingRef.current = null
        }
        
        const errorMessage = err.response?.data?.detail || err.message || 'Processing failed'
        
        // Provide more helpful error messages
        let displayError = errorMessage
        if (errorMessage.includes('timeout') || err.code === 'ECONNABORTED') {
          displayError = 'Processing took too long. For very long videos (1+ hours), try uploading the audio file directly.'
        } else if (errorMessage.includes('network')) {
          displayError = 'Network error. Please check your connection and try again.'
        } else if (errorMessage.includes('retry') || errorMessage.includes('attempts')) {
          displayError = 'Processing failed after multiple attempts. Please try again or use a shorter clip.'
        }
        
        setError(displayError)
        setCurrentStage('error')
        setIsIndeterminate(false)
        setProcessing('Error', 0)
        processingRef.current = false
      }
    }
    
    process()
  }, [media?.id, pollStatus])
  
  const handleRetry = () => {
    processingRef.current = false
    setError(null)
    setCurrentStep(0)
    setCurrentStage('unknown')
    setIsIndeterminate(true)
        setChunkProgress(null)
        setDetectedLanguage(null)
        setChunkTimeRange(null)
        startTimeRef.current = Date.now()
        setElapsedTime(0)
        // Re-trigger processing
        const currentMedia = media
        if (currentMedia) {
          setStatusMessage('Retrying...')
          setProcessing('Retrying...', 0)
          window.location.reload()
        }
  }
  
  const formatElapsed = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }
  
  return (
    <div className="w-full max-w-xl mx-auto">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="glass-card p-8"
      >
        {/* Media info */}
        <div className="text-center mb-8">
          <h2 className="text-xl font-semibold text-star-white mb-2">
            {media?.original_filename || 'Processing Media'}
          </h2>
          <p className="text-star-white/60 text-sm">
            {media?.media_type === 'video' ? 'Video' : 'Audio'} • 
            {media?.duration && media.duration > 0 
              ? ` ${formatDuration(media.duration)}`
              : ' Duration unknown (source does not provide length)'}
          </p>
          
          {/* Long content warning */}
          {media?.duration && media.duration > 1800 && currentStep === 0 && !error && (
            <p className="text-amber-400 text-xs mt-2 px-4">
              ⚠️ Long content detected ({formatDuration(media.duration)}). Processing may take 10-20 minutes.
            </p>
          )}
        </div>
        
        {/* Animated waveform */}
        <div className="flex items-center justify-center gap-1 h-20 mb-8">
          {Array.from({ length: 40 }).map((_, i) => (
            <motion.div
              key={i}
              className="w-1.5 bg-gradient-to-t from-nebula-purple to-nebula-violet rounded-full"
              animate={{
                height: error ? 4 : [8, 32, 8],
              }}
              transition={{
                duration: 0.8,
                repeat: error ? 0 : Infinity,
                delay: i * 0.05,
                ease: 'easeInOut',
              }}
            />
          ))}
        </div>
        
        {/* Progress steps */}
        <div className="space-y-4">
          {steps.map((step, index) => {
            const Icon = step.icon
            const isActive = index === currentStep
            const isComplete = index < currentStep
            
            return (
              <motion.div
                key={step.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className={`flex items-center gap-4 p-3 rounded-xl transition-all duration-300 ${
                  isActive
                    ? 'bg-nebula-purple/20 border border-nebula-purple/30'
                    : isComplete
                    ? 'bg-aurora-green/10 border border-aurora-green/20'
                    : 'opacity-40'
                }`}
              >
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center ${
                    isActive
                      ? 'bg-nebula-purple text-white'
                      : isComplete
                      ? 'bg-aurora-green text-white'
                      : 'bg-void-700 text-star-white/40'
                  }`}
                >
                  {isActive && !error ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <Icon className="w-5 h-5" />
                  )}
                </div>
                
                <div className="flex-1">
                  <p className={`font-medium ${
                    isActive ? 'text-star-white' : 'text-star-white/60'
                  }`}>
                    {step.label}
                  </p>
                  {isActive && !error && (
                    <div className="text-star-white/80 text-sm mt-1 space-y-1">
                      {/* Status message - verbatim from backend (single source of truth) */}
                      {statusMessage && (
                        <p className="font-medium text-star-white/90">
                          {statusMessage}
                        </p>
                      )}
                      
                      {/* Chunk progress when available - always render if present */}
                      {chunkProgress && (
                        <div className="flex items-center gap-2 mt-1">
                          <span className="font-mono text-nebula-violet text-xs">
                            Chunk {chunkProgress.current} / {chunkProgress.total}
                          </span>
                          {chunkProgress.percentage !== undefined && (
                            <>
                              <span className="text-star-white/40">•</span>
                              <span className="font-semibold text-nebula-purple text-xs">
                                {chunkProgress.percentage}%
                              </span>
                            </>
                          )}
                        </div>
                      )}
                      
                      {/* Chunk time range when available */}
                      {chunkTimeRange && (
                        <div className="text-xs text-star-white/60 mt-1">
                          Time range: {chunkTimeRange.start} to {chunkTimeRange.end}
                        </div>
                      )}
                      
                      {/* Detected language when available */}
                      {detectedLanguage && (
                        <div className="text-xs text-star-white/60 mt-1">
                          Language: {detectedLanguage}
                        </div>
                      )}
                      
                      {/* Soft ETA messaging (non-binding, text-only) */}
                      {currentStage === 'transcribing' && media?.duration && media.duration > 600 && (
                        <div className="text-xs text-star-white/50 mt-1 italic">
                          This usually takes a few minutes for long audio
                        </div>
                      )}
                    </div>
                  )}
                </div>
                
                {isComplete && (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="w-6 h-6 rounded-full bg-aurora-green flex items-center justify-center"
                  >
                    <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </motion.div>
                )}
              </motion.div>
            )
          })}
        </div>
        
        {/* Stage indicator and progress */}
        <div className="mt-8">
          {/* Stage label - visual scaffolding only, not semantic */}
          <div className="flex justify-between items-center mb-2 text-sm">
            <div className="flex items-center gap-2">
              {/* Visual stage indicator (not duplicating status_message) */}
              <span className="text-star-white/60 capitalize text-xs">
                {currentStage === 'chunking' ? 'Preparing' :
                 currentStage === 'highlighting' ? 'Analyzing' :
                 currentStage === 'generating' ? 'Generating' :
                 currentStage === 'downloading' ? 'Downloading' :
                 currentStage === 'transcribing' ? 'Transcribing' :
                 currentStage === 'analyzing' ? 'Analyzing' :
                 currentStage === 'complete' ? 'Complete' :
                 currentStage === 'error' ? 'Error' :
                 'Working'}
              </span>
              {/* Chunk progress - always show when available */}
              {chunkProgress && (
                <span className="text-nebula-violet font-mono text-xs">
                  {chunkProgress.current}/{chunkProgress.total}
                  {chunkProgress.percentage !== undefined && ` (${chunkProgress.percentage}%)`}
                </span>
              )}
            </div>
            <span className="text-star-white/40 font-mono text-xs">
              {formatElapsed(elapsedTime)}
            </span>
          </div>
          
          {/* Progress bar - only show if progress is quantifiable */}
          {!isIndeterminate && chunkProgress ? (
            <div className="space-y-1">
              <div className="h-2 bg-void-800 rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-nebula-purple to-nebula-violet"
                  initial={{ width: '0%' }}
                  animate={{ 
                    width: chunkProgress.percentage !== undefined 
                      ? `${chunkProgress.percentage}%`
                      : `${(chunkProgress.current / chunkProgress.total) * 100}%`
                  }}
                  transition={{ duration: 0.3 }}
                />
              </div>
              {chunkProgress.percentage !== undefined && (
                <div className="text-right text-xs text-star-white/40 font-mono">
                  {chunkProgress.percentage}% complete
                </div>
              )}
            </div>
          ) : isIndeterminate ? (
            <div className="h-2 bg-void-800 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-nebula-purple to-nebula-violet"
                animate={{
                  x: ['-100%', '100%'],
                }}
                transition={{
                  duration: 1.5,
                  repeat: Infinity,
                  ease: 'easeInOut',
                }}
                style={{ width: '30%' }}
              />
            </div>
          ) : currentStage === 'complete' ? (
            <div className="h-2 bg-void-800 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-aurora-green to-aurora-green/80 w-full" />
            </div>
          ) : null}
        </div>
        
        {/* Error state */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-6 p-4 rounded-xl bg-red-900/20 border border-red-500/30"
          >
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-red-400 text-sm">{error}</p>
              </div>
            </div>
            
            <div className="flex gap-3 mt-4">
              <button
                onClick={handleRetry}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-void-700 hover:bg-void-600 text-star-white text-sm transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Retry
              </button>
              <button
                onClick={reset}
                className="flex-1 px-4 py-2 rounded-lg border border-void-600 hover:bg-void-700 text-star-white/70 text-sm transition-colors"
              >
                Start Over
              </button>
            </div>
          </motion.div>
        )}
      </motion.div>
    </div>
  )
}
