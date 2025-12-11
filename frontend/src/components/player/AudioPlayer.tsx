'use client'

import { useRef, useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Play, Pause, Volume2, VolumeX, SkipBack, SkipForward } from 'lucide-react'
import { cn, formatTime } from '@/lib/utils'
import { TranscriptSegment } from '@/lib/api'

interface AudioPlayerProps {
  src: string
  transcription?: TranscriptSegment[]
  clipRange?: { start: number; end: number } | null
  onTimeUpdate?: (time: number) => void
  onSegmentClick?: (segment: TranscriptSegment) => void
  className?: string
}

export function AudioPlayer({
  src,
  transcription = [],
  clipRange,
  onTimeUpdate,
  onSegmentClick,
  className
}: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const progressRef = useRef<HTMLDivElement>(null)
  
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [isMuted, setIsMuted] = useState(false)
  const [volume, setVolume] = useState(1)
  const [waveformData, setWaveformData] = useState<number[]>([])
  const [activeSegmentId, setActiveSegmentId] = useState<number | null>(null)
  
  // Generate waveform visualization
  useEffect(() => {
    // Create fake waveform data for visualization
    // In production, you'd analyze the actual audio
    const bars = 100
    const data = Array.from({ length: bars }, () => 
      0.2 + Math.random() * 0.8
    )
    setWaveformData(data)
  }, [src])
  
  // Handle time updates
  const handleTimeUpdate = useCallback(() => {
    if (!audioRef.current) return
    
    const time = audioRef.current.currentTime
    setCurrentTime(time)
    onTimeUpdate?.(time)
    
    // Find active transcript segment
    const activeSegment = transcription.find(
      seg => time >= seg.start && time <= seg.end
    )
    setActiveSegmentId(activeSegment?.id ?? null)
  }, [transcription, onTimeUpdate])
  
  // Handle loaded metadata
  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration)
    }
  }
  
  // Play/pause toggle
  const togglePlay = () => {
    if (!audioRef.current) return
    
    if (isPlaying) {
      audioRef.current.pause()
    } else {
      audioRef.current.play()
    }
    setIsPlaying(!isPlaying)
  }
  
  // Seek to position
  const seekTo = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!audioRef.current || !progressRef.current) return
    
    const rect = progressRef.current.getBoundingClientRect()
    const percent = (e.clientX - rect.left) / rect.width
    const newTime = percent * duration
    
    audioRef.current.currentTime = newTime
    setCurrentTime(newTime)
  }
  
  // Skip forward/backward
  const skip = (seconds: number) => {
    if (!audioRef.current) return
    audioRef.current.currentTime = Math.max(0, Math.min(duration, currentTime + seconds))
  }
  
  // Toggle mute
  const toggleMute = () => {
    if (!audioRef.current) return
    audioRef.current.muted = !isMuted
    setIsMuted(!isMuted)
  }
  
  // Jump to segment
  const jumpToSegment = (segment: TranscriptSegment) => {
    if (!audioRef.current) return
    audioRef.current.currentTime = segment.start
    setCurrentTime(segment.start)
    onSegmentClick?.(segment)
  }
  
  const progress = duration > 0 ? (currentTime / duration) * 100 : 0
  
  return (
    <div className={cn('glass-card p-4', className)}>
      {/* Hidden audio element */}
      <audio
        ref={audioRef}
        src={src}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={() => setIsPlaying(false)}
        preload="metadata"
      />
      
      {/* Waveform visualization */}
      <div 
        ref={progressRef}
        className="relative h-16 mb-4 cursor-pointer group"
        onClick={seekTo}
      >
        {/* Waveform bars */}
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
        
        {/* Progress overlay */}
        <div 
          className="absolute top-0 left-0 h-full bg-gradient-to-r from-nebula-purple/20 to-transparent pointer-events-none"
          style={{ width: `${progress}%` }}
        />
        
        {/* Playhead */}
        <div 
          className="absolute top-0 h-full w-0.5 bg-star-white shadow-lg transition-opacity group-hover:opacity-100"
          style={{ left: `${progress}%`, opacity: isPlaying ? 1 : 0.5 }}
        />
        
        {/* Clip range highlight */}
        {clipRange && (
          <div
            className="absolute top-0 h-full bg-nebula-purple/20 border-l-2 border-r-2 border-nebula-purple pointer-events-none"
            style={{
              left: `${(clipRange.start / duration) * 100}%`,
              width: `${((clipRange.end - clipRange.start) / duration) * 100}%`
            }}
          />
        )}
      </div>
      
      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {/* Skip back */}
          <button
            onClick={() => skip(-10)}
            className="p-2 rounded-lg text-star-white/60 hover:text-star-white hover:bg-void-700 transition-colors"
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
              <Play className="w-5 h-5" fill="currentColor" />
            )}
          </button>
          
          {/* Skip forward */}
          <button
            onClick={() => skip(10)}
            className="p-2 rounded-lg text-star-white/60 hover:text-star-white hover:bg-void-700 transition-colors"
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
        <div className="mt-4 max-h-40 overflow-y-auto space-y-1 p-2 bg-void-900/50 rounded-lg">
          {transcription.map((segment) => (
            <button
              key={segment.id}
              onClick={() => jumpToSegment(segment)}
              className={cn(
                'block w-full text-left px-2 py-1 rounded text-sm transition-all',
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
  )
}






