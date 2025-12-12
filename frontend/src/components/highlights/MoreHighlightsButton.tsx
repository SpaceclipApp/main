'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Plus, Loader2, Sparkles } from 'lucide-react'
import { useProjectStore } from '@/store/project'
import { analyzeHighlights } from '@/lib/api'
import { Button } from '@/components/ui/Button'

interface MoreHighlightsButtonProps {
  onComplete?: () => void
}

export function MoreHighlightsButton({ onComplete }: MoreHighlightsButtonProps) {
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [showOptions, setShowOptions] = useState(false)
  
  const { media, highlights, setHighlights } = useProjectStore()
  
  if (!media || !highlights) return null
  
  const totalDuration = media.duration
  const existingHighlights = highlights.highlights
  
  // Find gaps in coverage
  const getCoverageGaps = () => {
    if (!existingHighlights.length) {
      return [{ start: 0, end: totalDuration }]
    }
    
    const sorted = [...existingHighlights].sort((a, b) => a.start - b.start)
    const gaps: { start: number; end: number }[] = []
    
    // Check start
    if (sorted[0].start > 60) {
      gaps.push({ start: 0, end: sorted[0].start })
    }
    
    // Check middle gaps
    for (let i = 0; i < sorted.length - 1; i++) {
      const gap = sorted[i + 1].start - sorted[i].end
      if (gap > 120) { // 2+ minute gaps
        gaps.push({ start: sorted[i].end, end: sorted[i + 1].start })
      }
    }
    
    // Check end
    const lastEnd = sorted[sorted.length - 1].end
    if (totalDuration - lastEnd > 60) {
      gaps.push({ start: lastEnd, end: totalDuration })
    }
    
    return gaps
  }
  
  const gaps = getCoverageGaps()
  const hasUncoveredContent = gaps.length > 0
  
  const handleFindMore = async (startTime?: number, endTime?: number) => {
    setIsAnalyzing(true)
    
    try {
      const result = await analyzeHighlights(media.id, {
        max_highlights: 5,
        min_duration: 15,
        max_duration: 90,
        start_time: startTime,
        end_time: endTime,
        append: true // Append to existing highlights
      })
      
      setHighlights(result)
      setShowOptions(false)
      onComplete?.()
    } catch (error) {
      console.error('Failed to find more highlights:', error)
    } finally {
      setIsAnalyzing(false)
    }
  }
  
  const formatTimeRange = (start: number, end: number) => {
    const formatTime = (s: number) => {
      const mins = Math.floor(s / 60)
      return `${mins}m`
    }
    return `${formatTime(start)} - ${formatTime(end)}`
  }
  
  return (
    <div className="mt-6">
      {showOptions ? (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-4 space-y-3"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-star-white">Find more highlights in:</span>
            <button
              onClick={() => setShowOptions(false)}
              className="text-star-white/40 hover:text-star-white text-sm"
            >
              Cancel
            </button>
          </div>
          
          {/* Full scan option */}
          <button
            onClick={() => handleFindMore()}
            disabled={isAnalyzing}
            className="w-full p-3 rounded-lg bg-void-800/50 hover:bg-void-700/50 transition-colors text-left"
          >
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-nebula-violet" />
              <span className="text-star-white">Entire content</span>
            </div>
            <p className="text-xs text-star-white/40 mt-1">
              Re-analyze the full {Math.round(totalDuration / 60)} minutes
            </p>
          </button>
          
          {/* Gap-specific options */}
          {hasUncoveredContent && (
            <>
              <p className="text-xs text-star-white/40">Or focus on uncovered sections:</p>
              {gaps.slice(0, 3).map((gap, i) => (
                <button
                  key={i}
                  onClick={() => handleFindMore(gap.start, gap.end)}
                  disabled={isAnalyzing}
                  className="w-full p-2 rounded-lg bg-void-900/50 hover:bg-void-800/50 transition-colors text-left text-sm"
                >
                  <span className="text-star-white/80">
                    {formatTimeRange(gap.start, gap.end)}
                  </span>
                  <span className="text-star-white/40 ml-2">
                    ({Math.round((gap.end - gap.start) / 60)}m uncovered)
                  </span>
                </button>
              ))}
            </>
          )}
          
          {isAnalyzing && (
            <div className="flex items-center justify-center py-2">
              <Loader2 className="w-5 h-5 text-nebula-violet animate-spin mr-2" />
              <span className="text-sm text-star-white/60">Finding highlights...</span>
            </div>
          )}
        </motion.div>
      ) : (
        <Button
          onClick={() => setShowOptions(true)}
          variant="outline"
          className="w-full"
          disabled={isAnalyzing}
        >
          {isAnalyzing ? (
            <Loader2 className="w-4 h-4 animate-spin mr-2" />
          ) : (
            <Plus className="w-4 h-4 mr-2" />
          )}
          Find More Highlights
          {hasUncoveredContent && (
            <span className="ml-2 px-2 py-0.5 rounded-full text-xs bg-nebula-purple/20 text-nebula-violet">
              {gaps.length} uncovered section{gaps.length > 1 ? 's' : ''}
            </span>
          )}
        </Button>
      )}
    </div>
  )
}







