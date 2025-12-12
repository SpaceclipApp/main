'use client'

import { useRef, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { cn, formatTime } from '@/lib/utils'
import { TranscriptionResult } from '@/lib/api'

interface TranscriptViewerProps {
  transcription: TranscriptionResult
  clipRange: { start: number; end: number } | null
  onRangeSelect: (start: number, end: number) => void
  onSegmentClick?: (segment: { start: number; end: number }) => void
}

export function TranscriptViewer({ transcription, clipRange, onRangeSelect, onSegmentClick }: TranscriptViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [hasScrolled, setHasScrolled] = useState(false)
  
  // Auto-scroll to selected range when it changes (only if user hasn't manually scrolled)
  useEffect(() => {
    if (clipRange && containerRef.current && !hasScrolled) {
      // Find the first segment that overlaps with the clip range
      const firstMatchIndex = transcription.segments.findIndex(
        seg => seg.start < clipRange.end && seg.end > clipRange.start
      )
      
      if (firstMatchIndex !== -1) {
        // Small delay to ensure DOM is updated
        setTimeout(() => {
          const elements = containerRef.current?.querySelectorAll('[data-segment]')
          const targetElement = elements?.[firstMatchIndex]
          if (targetElement && containerRef.current) {
            // Only scroll if the target is not already visible
            const containerRect = containerRef.current.getBoundingClientRect()
            const targetRect = targetElement.getBoundingClientRect()
            const isVisible = targetRect.top >= containerRect.top && targetRect.bottom <= containerRect.bottom
            
            if (!isVisible) {
              targetElement.scrollIntoView({ behavior: 'smooth', block: 'center' })
            }
          }
        }, 100)
      }
    }
  }, [clipRange?.start, clipRange?.end, transcription.segments, hasScrolled])
  
  // Reset hasScrolled when clipRange is cleared
  useEffect(() => {
    if (!clipRange) {
      setHasScrolled(false)
    }
  }, [clipRange])
  
  // Check if segment overlaps with clip range (not fully contained)
  const isSegmentInRange = (start: number, end: number) => {
    if (!clipRange) return false
    // Check for overlap: segment overlaps if it starts before clip ends AND ends after clip starts
    return start < clipRange.end && end > clipRange.start
  }
  
  const handleSegmentClick = (start: number, end: number) => {
    // Seek player to segment start time
    onSegmentClick?.({ start, end })
    
    // If shift is held, extend the range
    // Otherwise, start a new selection
    if (clipRange) {
      const newStart = Math.min(clipRange.start, start)
      const newEnd = Math.max(clipRange.end, end)
      onRangeSelect(newStart, newEnd)
    } else {
      onRangeSelect(start, end)
    }
  }
  
  return (
    <div className="glass-card p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-star-white">Full Transcript</h3>
        <span className="text-xs text-star-white/40">
          Click segments to adjust clip range
        </span>
      </div>
      
      <div
        ref={containerRef}
        className="max-h-96 overflow-y-auto space-y-2 pr-2 scrollbar-thin"
      >
        {transcription.segments.map((segment, index) => {
          const inRange = isSegmentInRange(segment.start, segment.end)
          
          return (
            <motion.div
              key={segment.id}
              data-segment={index}
              data-selected={inRange}
              onClick={() => handleSegmentClick(segment.start, segment.end)}
              className={cn(
                'p-3 rounded-lg cursor-pointer transition-all duration-200',
                inRange
                  ? 'bg-nebula-purple/20 border border-nebula-purple/30'
                  : 'hover:bg-void-700/50'
              )}
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
            >
              <div className="flex items-start gap-3">
                <span className="flex-shrink-0 font-mono text-xs text-star-white/40 w-14">
                  {formatTime(segment.start)}
                </span>
                
                {segment.speaker && (
                  <span className="flex-shrink-0 px-2 py-0.5 rounded text-xs bg-void-700 text-star-cyan">
                    {segment.speaker}
                  </span>
                )}
                
                <p className={cn(
                  'flex-1 text-sm leading-relaxed',
                  inRange ? 'text-star-white' : 'text-star-white/70'
                )}>
                  {segment.text}
                </p>
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}


