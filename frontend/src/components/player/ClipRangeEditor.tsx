'use client'

import { useRef, useState, useCallback, useEffect } from 'react'
import { motion } from 'framer-motion'
import { GripVertical, Scissors } from 'lucide-react'
import { cn, formatTime } from '@/lib/utils'
import { TranscriptSegment } from '@/lib/api'

interface ClipRangeEditorProps {
  duration: number
  clipRange: { start: number; end: number }
  onRangeChange: (start: number, end: number) => void
  onRangeCommit?: (start: number, end: number) => void // Called when drag ends
  transcription?: TranscriptSegment[]
  minClipDuration?: number // Minimum clip length in seconds
  maxClipDuration?: number // Maximum clip length in seconds (undefined = no limit)
  className?: string
}

/**
 * ClipRangeEditor - A timeline component with draggable handles for adjusting clip boundaries.
 * 
 * Features:
 * - Drag handles at start and end of clip
 * - Word-boundary snapping (snaps to transcript segment boundaries)
 * - Visual feedback with highlighted region
 * - Duration constraints
 */
export function ClipRangeEditor({
  duration,
  clipRange,
  onRangeChange,
  onRangeCommit,
  transcription = [],
  minClipDuration = 5,
  maxClipDuration, // undefined = no maximum limit
  className,
}: ClipRangeEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [isDragging, setIsDragging] = useState<'start' | 'end' | null>(null)
  const [hoverHandle, setHoverHandle] = useState<'start' | 'end' | null>(null)
  const [snapIndicator, setSnapIndicator] = useState<{ time: number; text: string } | null>(null)
  
  // Find the nearest word/segment boundary for snapping
  const findNearestBoundary = useCallback((time: number, isStart: boolean): number => {
    if (transcription.length === 0) return time
    
    const SNAP_THRESHOLD = 0.5 // seconds
    let nearestBoundary = time
    let nearestDistance = Infinity
    let nearestText = ''
    
    for (const segment of transcription) {
      // Check segment start
      const startDist = Math.abs(segment.start - time)
      if (startDist < nearestDistance && startDist < SNAP_THRESHOLD) {
        nearestDistance = startDist
        nearestBoundary = segment.start
        nearestText = segment.text.slice(0, 30) + (segment.text.length > 30 ? '...' : '')
      }
      
      // Check segment end
      const endDist = Math.abs(segment.end - time)
      if (endDist < nearestDistance && endDist < SNAP_THRESHOLD) {
        nearestDistance = endDist
        nearestBoundary = segment.end
        nearestText = segment.text.slice(-30)
      }
    }
    
    // Update snap indicator
    if (nearestDistance < SNAP_THRESHOLD) {
      setSnapIndicator({ time: nearestBoundary, text: nearestText })
    } else {
      setSnapIndicator(null)
    }
    
    return nearestBoundary
  }, [transcription])
  
  // Convert pixel position to time
  const pixelToTime = useCallback((pixelX: number): number => {
    if (!containerRef.current) return 0
    const rect = containerRef.current.getBoundingClientRect()
    const percent = Math.max(0, Math.min(1, (pixelX - rect.left) / rect.width))
    return percent * duration
  }, [duration])
  
  // Handle drag start
  const handleDragStart = useCallback((handle: 'start' | 'end') => (e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault()
    setIsDragging(handle)
  }, [])
  
  // Handle drag move
  useEffect(() => {
    if (!isDragging) return
    
    const handleMove = (e: MouseEvent | TouchEvent) => {
      const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX
      let newTime = pixelToTime(clientX)
      
      // Snap to word boundary
      newTime = findNearestBoundary(newTime, isDragging === 'start')
      
      let newStart = clipRange.start
      let newEnd = clipRange.end
      
      if (isDragging === 'start') {
        newStart = Math.max(0, Math.min(newTime, clipRange.end - minClipDuration))
        // Enforce max duration if specified
        if (maxClipDuration !== undefined && newEnd - newStart > maxClipDuration) {
          newStart = newEnd - maxClipDuration
        }
      } else {
        newEnd = Math.min(duration, Math.max(newTime, clipRange.start + minClipDuration))
        // Enforce max duration if specified
        if (maxClipDuration !== undefined && newEnd - newStart > maxClipDuration) {
          newEnd = newStart + maxClipDuration
        }
      }
      
      onRangeChange(newStart, newEnd)
    }
    
    const handleEnd = () => {
      setIsDragging(null)
      setSnapIndicator(null)
      // Call commit callback when drag ends (for saving to backend)
      onRangeCommit?.(clipRange.start, clipRange.end)
    }
    
    document.addEventListener('mousemove', handleMove)
    document.addEventListener('mouseup', handleEnd)
    document.addEventListener('touchmove', handleMove)
    document.addEventListener('touchend', handleEnd)
    
    return () => {
      document.removeEventListener('mousemove', handleMove)
      document.removeEventListener('mouseup', handleEnd)
      document.removeEventListener('touchmove', handleMove)
      document.removeEventListener('touchend', handleEnd)
    }
  }, [isDragging, clipRange, duration, minClipDuration, maxClipDuration, pixelToTime, findNearestBoundary, onRangeChange])
  
  const clipDuration = clipRange.end - clipRange.start
  const startPercent = (clipRange.start / duration) * 100
  const widthPercent = (clipDuration / duration) * 100
  
  return (
    <div className={cn('space-y-2', className)}>
      {/* Header with instructions */}
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-2 text-star-white/60">
          <Scissors className="w-3 h-3" />
          <span>Drag handles to adjust clip boundaries</span>
        </div>
        <div className="flex items-center gap-3 font-mono">
          <span className="text-star-white/40">Duration:</span>
          <span className={cn(
            'font-medium',
            clipDuration < minClipDuration ? 'text-red-400' :
            (maxClipDuration !== undefined && clipDuration > maxClipDuration) ? 'text-amber-400' :
            'text-nebula-violet'
          )}>
            {formatTime(clipDuration)}
          </span>
        </div>
      </div>
      
      {/* Timeline */}
      <div 
        ref={containerRef}
        className="relative h-16 bg-void-900 rounded-lg overflow-hidden cursor-crosshair"
      >
        {/* Background track with tick marks */}
        <div className="absolute inset-0">
          {/* Time tick marks */}
          {Array.from({ length: Math.ceil(duration / 10) }).map((_, i) => {
            const time = i * 10
            const percent = (time / duration) * 100
            return (
              <div
                key={i}
                className="absolute top-0 h-2 w-px bg-void-600"
                style={{ left: `${percent}%` }}
              />
            )
          })}
        </div>
        
        {/* Transcript segments visualization */}
        {transcription.map((segment, i) => {
          const segStart = (segment.start / duration) * 100
          const segWidth = ((segment.end - segment.start) / duration) * 100
          return (
            <div
              key={i}
              className="absolute bottom-0 h-1 bg-void-600/50"
              style={{ left: `${segStart}%`, width: `${segWidth}%` }}
              title={segment.text}
            />
          )
        })}
        
        {/* Selected clip region */}
        <motion.div
          className={cn(
            'absolute top-0 h-full',
            isDragging ? 'bg-nebula-purple/30' : 'bg-nebula-purple/20'
          )}
          style={{ left: `${startPercent}%`, width: `${widthPercent}%` }}
          animate={{ 
            opacity: isDragging ? 1 : 0.8,
          }}
        >
          {/* Inner highlight bar */}
          <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 h-3 bg-nebula-purple/40 rounded-full mx-4" />
        </motion.div>
        
        {/* Start handle */}
        <motion.div
          className={cn(
            'absolute top-0 h-full w-3 cursor-ew-resize z-10',
            'flex items-center justify-center',
            'transition-colors duration-150',
            (isDragging === 'start' || hoverHandle === 'start') 
              ? 'bg-nebula-purple' 
              : 'bg-nebula-violet'
          )}
          style={{ left: `${startPercent}%`, transform: 'translateX(-50%)' }}
          onMouseDown={handleDragStart('start')}
          onTouchStart={handleDragStart('start')}
          onMouseEnter={() => setHoverHandle('start')}
          onMouseLeave={() => setHoverHandle(null)}
          whileHover={{ scale: 1.1 }}
        >
          <GripVertical className="w-2 h-4 text-white/80" />
          
          {/* Time tooltip */}
          {(isDragging === 'start' || hoverHandle === 'start') && (
            <motion.div
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              className="absolute -top-8 left-1/2 -translate-x-1/2 px-2 py-1 rounded bg-void-800 text-xs font-mono text-star-white whitespace-nowrap"
            >
              {formatTime(clipRange.start)}
            </motion.div>
          )}
        </motion.div>
        
        {/* End handle */}
        <motion.div
          className={cn(
            'absolute top-0 h-full w-3 cursor-ew-resize z-10',
            'flex items-center justify-center',
            'transition-colors duration-150',
            (isDragging === 'end' || hoverHandle === 'end') 
              ? 'bg-nebula-purple' 
              : 'bg-nebula-violet'
          )}
          style={{ left: `${startPercent + widthPercent}%`, transform: 'translateX(-50%)' }}
          onMouseDown={handleDragStart('end')}
          onTouchStart={handleDragStart('end')}
          onMouseEnter={() => setHoverHandle('end')}
          onMouseLeave={() => setHoverHandle(null)}
          whileHover={{ scale: 1.1 }}
        >
          <GripVertical className="w-2 h-4 text-white/80" />
          
          {/* Time tooltip */}
          {(isDragging === 'end' || hoverHandle === 'end') && (
            <motion.div
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              className="absolute -top-8 left-1/2 -translate-x-1/2 px-2 py-1 rounded bg-void-800 text-xs font-mono text-star-white whitespace-nowrap"
            >
              {formatTime(clipRange.end)}
            </motion.div>
          )}
        </motion.div>
        
        {/* Snap indicator */}
        {snapIndicator && isDragging && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="absolute bottom-2 left-1/2 -translate-x-1/2 px-3 py-1.5 rounded-lg bg-aurora-green/90 text-xs text-white flex items-center gap-2"
          >
            <div className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
            Snapping to word boundary
          </motion.div>
        )}
      </div>
      
      {/* Time labels */}
      <div className="flex justify-between text-xs font-mono text-star-white/40">
        <span>0:00</span>
        <span>{formatTime(duration)}</span>
      </div>
      
      {/* Clip range display */}
      <div className="flex items-center justify-center gap-4 text-sm">
        <div className="flex items-center gap-2">
          <span className="text-star-white/60">Start:</span>
          <span className="font-mono text-nebula-violet">{formatTime(clipRange.start)}</span>
        </div>
        <div className="w-8 h-px bg-void-600" />
        <div className="flex items-center gap-2">
          <span className="text-star-white/60">End:</span>
          <span className="font-mono text-nebula-violet">{formatTime(clipRange.end)}</span>
        </div>
      </div>
    </div>
  )
}
