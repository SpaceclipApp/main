'use client'

import { useEffect, useState, useRef } from 'react'
import { motion } from 'framer-motion'
import { Loader2, Wand2, FileAudio, MessageSquare, Sparkles, AlertCircle, RefreshCw } from 'lucide-react'
import { useProjectStore } from '@/store/project'
import { transcribeMedia, analyzeHighlights, getProject } from '@/lib/api'
import { formatDuration } from '@/lib/utils'

const steps = [
  { id: 'transcribe', label: 'Transcribing audio', icon: FileAudio },
  { id: 'analyze', label: 'Finding highlights', icon: Sparkles },
  { id: 'complete', label: 'Ready to clip!', icon: Wand2 },
]

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
  const [elapsedTime, setElapsedTime] = useState(0)
  const [estimatedTime, setEstimatedTime] = useState<number | null>(null)
  const processingRef = useRef(false)
  const startTimeRef = useRef<number>(Date.now())
  
  // Update elapsed time
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedTime(Math.floor((Date.now() - startTimeRef.current) / 1000))
    }, 1000)
    return () => clearInterval(timer)
  }, [])
  
  // Estimate processing time based on media duration
  useEffect(() => {
    if (media?.duration) {
      // Rough estimate: ~1-2 minutes per minute of audio for transcription + analysis
      // For long content, estimate conservatively
      const estimatedSeconds = Math.ceil(media.duration * 1.5) + 60
      setEstimatedTime(estimatedSeconds)
    }
  }, [media?.duration])
  
  useEffect(() => {
    if (!media) return
    
    // Prevent double-invocation from React Strict Mode
    if (processingRef.current) return
    processingRef.current = true
    
    const process = async () => {
      try {
        // Step 1: Transcribe (skip if already done)
        setProcessing('Transcribing audio...', 0.2)
        setCurrentStep(0)
        
        let transcription = existingTranscription
        if (!transcription) {
          // Show estimate for long content
          if (media.duration > 600) { // > 10 minutes
            setProcessing('Transcribing long audio (this may take several minutes)...', 0.2)
          }
          
          transcription = await transcribeMedia(media.id)
          setTranscription(transcription)
        }
        
        // Step 2: Analyze highlights
        setProcessing('Finding highlights with AI...', 0.6)
        setCurrentStep(1)
        
        // Request more highlights for longer content
        const highlightCount = media.duration > 1800 ? 20 : media.duration > 600 ? 15 : 10
        
        const highlights = await analyzeHighlights(media.id, {
          max_highlights: highlightCount,
          min_duration: 15,
          max_duration: 90,
        })
        setHighlights(highlights)
        
        // Complete
        setProcessing('Complete!', 1)
        setCurrentStep(2)
        
        // Wait a moment before transitioning
        setTimeout(() => {
          setStep('highlights')
        }, 1500)
        
      } catch (err: any) {
        console.error('Processing error:', err)
        const errorMessage = err.response?.data?.detail || err.message || 'Processing failed'
        
        // Provide more helpful error messages
        let displayError = errorMessage
        if (errorMessage.includes('timeout') || err.code === 'ECONNABORTED') {
          displayError = 'Processing took too long. For very long videos (1+ hours), try uploading the audio file directly.'
        } else if (errorMessage.includes('network')) {
          displayError = 'Network error. Please check your connection and try again.'
        }
        
        setError(displayError)
        setProcessing('Error', 0)
        processingRef.current = false
      }
    }
    
    process()
  }, [media?.id])
  
  const handleRetry = () => {
    processingRef.current = false
    setError(null)
    setCurrentStep(0)
    startTimeRef.current = Date.now()
    setElapsedTime(0)
    // Re-trigger processing
    const currentMedia = media
    if (currentMedia) {
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
            {media?.duration && ` ${formatDuration(media.duration)}`}
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
                    <p className="text-star-white/40 text-xs mt-0.5">
                      {processingStatus}
                    </p>
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
        
        {/* Progress bar */}
        <div className="mt-8">
          <div className="h-2 bg-void-800 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-nebula-purple to-nebula-violet"
              initial={{ width: '0%' }}
              animate={{ width: `${progress * 100}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
          <div className="flex justify-between items-center mt-2 text-sm">
            <span className="text-star-white/40">
              {Math.round(progress * 100)}% complete
            </span>
            <span className="text-star-white/40 font-mono">
              {formatElapsed(elapsedTime)}
            </span>
          </div>
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
