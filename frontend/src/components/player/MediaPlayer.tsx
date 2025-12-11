'use client'

import { useRef, useState, useEffect, useCallback, forwardRef, useImperativeHandle } from 'react'
import { motion } from 'framer-motion'
import { Play, Pause, Volume2, VolumeX, SkipBack, SkipForward, Maximize, Minimize } from 'lucide-react'
import { cn, formatTime } from '@/lib/utils'
import { TranscriptSegment } from '@/lib/api'

export interface MediaPlayerRef {
  seekTo: (time: number) => void
  play: () => void
  pause: () => void
  getCurrentTime: () => number
}

interface MediaPlayerProps {
  src: string
  mediaType: 'audio' | 'video'
  poster?: string
  transcription?: TranscriptSegment[]
  clipRange?: { start: number; end: number } | null
  onTimeUpdate?: (time: number) => void
  onSegmentClick?: (segment: TranscriptSegment) => void
  className?: string
  autoSeekToClip?: boolean
}

export const MediaPlayer = forwardRef<MediaPlayerRef, MediaPlayerProps>(({
  src,
  mediaType,
  poster,
  transcription = [],
  clipRange,
  onTimeUpdate,
  onSegmentClick,
  className,
  autoSeekToClip = false
}, ref) => {
  const mediaRef = useRef<HTMLVideoElement | HTMLAudioElement>(null)
  const progressRef = useRef<HTMLDivElement>(null)
  
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [isMuted, setIsMuted] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [waveformData, setWaveformData] = useState<number[]>([])
  const [activeSegmentId, setActiveSegmentId] = useState<number | null>(null)
  const [isLoaded, setIsLoaded] = useState(false)
  
  // Expose methods via ref
  useImperativeHandle(ref, () => ({
    seekTo: (time: number) => {
      if (mediaRef.current) {
        mediaRef.current.currentTime = time
        setCurrentTime(time)
      }
    },
    play: () => {
      if (mediaRef.current) {
        mediaRef.current.play()
        setIsPlaying(true)
      }
    },
    pause: () => {
      if (mediaRef.current) {
        mediaRef.current.pause()
        setIsPlaying(false)
      }
    },
    getCurrentTime: () => mediaRef.current?.currentTime || 0
  }))
  
  // Generate waveform visualization for audio
  useEffect(() => {
    if (mediaType === 'audio') {
      const bars = 100
      const data = Array.from({ length: bars }, () => 
        0.2 + Math.random() * 0.8
      )
      setWaveformData(data)
    }
  }, [src, mediaType])
  
  // Auto-seek to clip range when it changes
  useEffect(() => {
    if (autoSeekToClip && clipRange && mediaRef.current && isLoaded) {
      mediaRef.current.currentTime = clipRange.start
      setCurrentTime(clipRange.start)
    }
  }, [clipRange, autoSeekToClip, isLoaded])
  
  // Handle time updates
  const handleTimeUpdate = useCallback(() => {
    if (!mediaRef.current) return
    
    const time = mediaRef.current.currentTime
    setCurrentTime(time)
    onTimeUpdate?.(time)
    
    // Find active transcript segment
    const activeSegment = transcription.find(
      seg => time >= seg.start && time <= seg.end
    )
    setActiveSegmentId(activeSegment?.id ?? null)
    
    // Stop at end of clip range if defined
    if (clipRange && time >= clipRange.end) {
      mediaRef.current.pause()
      setIsPlaying(false)
    }
  }, [transcription, onTimeUpdate, clipRange])
  
  // Handle loaded metadata
  const handleLoadedMetadata = () => {
    if (mediaRef.current) {
      setDuration(mediaRef.current.duration)
      setIsLoaded(true)
    }
  }
  
  // Play/pause toggle
  const togglePlay = () => {
    if (!mediaRef.current) return
    
    if (isPlaying) {
      mediaRef.current.pause()
    } else {
      // If at end of clip, restart from clip start
      if (clipRange && currentTime >= clipRange.end) {
        mediaRef.current.currentTime = clipRange.start
      }
      mediaRef.current.play()
    }
    setIsPlaying(!isPlaying)
  }
  
  // Seek to position
  const seekTo = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!mediaRef.current || !progressRef.current) return
    
    const rect = progressRef.current.getBoundingClientRect()
    const percent = (e.clientX - rect.left) / rect.width
    const newTime = percent * duration
    
    mediaRef.current.currentTime = newTime
    setCurrentTime(newTime)
  }
  
  // Skip forward/backward
  const skip = (seconds: number) => {
    if (!mediaRef.current) return
    mediaRef.current.currentTime = Math.max(0, Math.min(duration, currentTime + seconds))
  }
  
  // Toggle mute
  const toggleMute = () => {
    if (!mediaRef.current) return
    mediaRef.current.muted = !isMuted
    setIsMuted(!isMuted)
  }
  
  // Jump to segment
  const jumpToSegment = (segment: TranscriptSegment) => {
    if (!mediaRef.current) return
    mediaRef.current.currentTime = segment.start
    setCurrentTime(segment.start)
    onSegmentClick?.(segment)
  }
  
  const progress = duration > 0 ? (currentTime / duration) * 100 : 0
  
  return (
    <div className={cn('glass-card overflow-hidden', className)}>
      {/* Video element */}
      {mediaType === 'video' && (
        <div className="relative bg-black aspect-video">
          <video
            ref={mediaRef as React.RefObject<HTMLVideoElement>}
            src={src}
            poster={poster}
            onTimeUpdate={handleTimeUpdate}
            onLoadedMetadata={handleLoadedMetadata}
            onEnded={() => setIsPlaying(false)}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            preload="metadata"
            className="w-full h-full"
            playsInline
          />
          
          {/* Video overlay controls */}
          {!isPlaying && (
            <button
              onClick={togglePlay}
              className="absolute inset-0 flex items-center justify-center bg-black/30 transition-opacity hover:bg-black/40"
            >
              <div className="w-16 h-16 rounded-full bg-nebula-purple flex items-center justify-center">
                <Play className="w-8 h-8 text-white ml-1" fill="currentColor" />
              </div>
            </button>
          )}
        </div>
      )}
      
      {/* Audio element (hidden) */}
      {mediaType === 'audio' && (
        <audio
          ref={mediaRef as React.RefObject<HTMLAudioElement>}
          src={src}
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={handleLoadedMetadata}
          onEnded={() => setIsPlaying(false)}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          preload="metadata"
        />
      )}
      
      <div className="p-4">
        {/* Waveform / Progress visualization */}
        <div 
          ref={progressRef}
          className="relative h-12 mb-4 cursor-pointer group"
          onClick={seekTo}
        >
          {mediaType === 'audio' ? (
            // Waveform bars for audio
            <div className="absolute inset-0 flex items-center justify-center gap-0.5">
              {waveformData.map((height, i) => {
                const barProgress = (i / waveformData.length) * 100
                const isPlayed = barProgress <= progress
                const isInClipRange = clipRange && 
                  (i / waveformData.length) * duration >= clipRange.start &&
                  (i / waveformData.length) * duration <= clipRange.end
                
                return (
                  <div
                    key={i}
                    className={cn(
                      'w-1 rounded-full transition-all duration-150',
                      isInClipRange 
                        ? isPlayed 
                          ? 'bg-nebula-violet' 
                          : 'bg-nebula-purple/50'
                        : isPlayed 
                          ? 'bg-star-cyan' 
                          : 'bg-void-600'
                    )}
                    style={{ height: `${height * 100}%` }}
                  />
                )
              })}
            </div>
          ) : (
            // Simple progress bar for video
            <div className="absolute inset-y-0 left-0 right-0 flex items-center">
              <div className="w-full h-2 bg-void-700 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-nebula-purple to-nebula-violet transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}
          
          {/* Clip range highlight */}
          {clipRange && duration > 0 && (
            <div
              className="absolute top-0 h-full bg-nebula-purple/20 border-l-2 border-r-2 border-nebula-purple pointer-events-none"
              style={{
                left: `${(clipRange.start / duration) * 100}%`,
                width: `${((clipRange.end - clipRange.start) / duration) * 100}%`
              }}
            />
          )}
          
          {/* Playhead */}
          <div 
            className="absolute top-0 h-full w-0.5 bg-star-white shadow-lg transition-opacity group-hover:opacity-100"
            style={{ left: `${progress}%`, opacity: isPlaying ? 1 : 0.5 }}
          />
        </div>
        
        {/* Controls */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {/* Skip back */}
            <button
              onClick={() => skip(-10)}
              className="p-2 rounded-lg text-star-white/60 hover:text-star-white hover:bg-void-700 transition-colors"
              title="Skip back 10s"
            >
              <SkipBack className="w-4 h-4" />
            </button>
            
            {/* Play/Pause */}
            <button
              onClick={togglePlay}
              className="p-3 rounded-full bg-nebula-purple text-white hover:bg-nebula-violet transition-colors"
            >
              {isPlaying ? (
                <Pause className="w-5 h-5" fill="currentColor" />
              ) : (
                <Play className="w-5 h-5 ml-0.5" fill="currentColor" />
              )}
            </button>
            
            {/* Skip forward */}
            <button
              onClick={() => skip(10)}
              className="p-2 rounded-lg text-star-white/60 hover:text-star-white hover:bg-void-700 transition-colors"
              title="Skip forward 10s"
            >
              <SkipForward className="w-4 h-4" />
            </button>
          </div>
          
          {/* Time display */}
          <div className="flex items-center gap-3 font-mono text-sm">
            <span className="text-star-white">{formatTime(currentTime)}</span>
            <span className="text-star-white/40">/</span>
            <span className="text-star-white/60">{formatTime(duration)}</span>
          </div>
          
          {/* Volume */}
          <div className="flex items-center gap-2">
            <button
              onClick={toggleMute}
              className="p-2 rounded-lg text-star-white/60 hover:text-star-white hover:bg-void-700 transition-colors"
            >
              {isMuted ? (
                <VolumeX className="w-4 h-4" />
              ) : (
                <Volume2 className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>
        
        {/* Transcript with sync highlighting */}
        {transcription.length > 0 && (
          <div className="mt-4 max-h-32 overflow-y-auto space-y-1 p-2 bg-void-900/50 rounded-lg text-sm">
            {transcription.slice(0, 50).map((segment) => (
              <button
                key={segment.id}
                onClick={() => jumpToSegment(segment)}
                className={cn(
                  'block w-full text-left px-2 py-1 rounded transition-all',
                  activeSegmentId === segment.id
                    ? 'bg-nebula-purple/30 text-star-white'
                    : 'text-star-white/60 hover:bg-void-800 hover:text-star-white/80'
                )}
              >
                <span className="font-mono text-xs text-star-white/40 mr-2">
                  {formatTime(segment.start)}
                </span>
                {segment.speaker && (
                  <span className="text-star-cyan text-xs mr-2">{segment.speaker}:</span>
                )}
                <span className={cn(
                  'transition-colors',
                  activeSegmentId === segment.id && 'text-star-white font-medium'
                )}>
                  {segment.text}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
})

MediaPlayer.displayName = 'MediaPlayer'




