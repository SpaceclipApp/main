'use client'

import { motion } from 'framer-motion'
import { Play, Clock, Tag, Star } from 'lucide-react'
import { cn, formatTime, truncateText } from '@/lib/utils'
import { Highlight } from '@/lib/api'

interface HighlightCardProps {
  highlight: Highlight
  isSelected: boolean
  onSelect: () => void
  onPlay?: () => void
  index: number
}

export function HighlightCard({ highlight, isSelected, onSelect, onPlay, index }: HighlightCardProps) {
  const duration = highlight.end - highlight.start
  
  const handlePlayClick = (e: React.MouseEvent) => {
    e.stopPropagation() // Prevent card selection
    onPlay?.()
  }
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      onClick={onSelect}
      className={cn(
        'relative cursor-pointer rounded-xl p-4 transition-all duration-300',
        'border backdrop-blur-sm',
        isSelected
          ? 'bg-nebula-purple/20 border-nebula-purple shadow-neon-purple'
          : 'bg-void-800/30 border-void-600/50 hover:border-nebula-purple/50 hover:bg-void-800/50'
      )}
    >
      {/* Score badge */}
      <div className={cn(
        'absolute -top-2 -right-2 w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold z-10',
        'border-2 border-void-800',
        highlight.score >= 0.8
          ? 'bg-star-gold text-void-950'
          : highlight.score >= 0.6
          ? 'bg-nebula-violet text-white'
          : 'bg-void-600 text-star-white/70'
      )}>
        {Math.round(highlight.score * 10)}
      </div>
      
      {/* Content */}
      <div className="flex items-start gap-3">
        {/* Play button */}
        <button
          onClick={handlePlayClick}
          className={cn(
            'flex-shrink-0 w-12 h-12 rounded-lg flex items-center justify-center',
            'transition-all duration-300',
            isSelected
              ? 'bg-nebula-purple text-white hover:bg-nebula-violet'
              : 'bg-void-700 text-nebula-violet hover:bg-nebula-purple hover:text-white'
          )}
          title={`Play clip (${formatTime(highlight.start)} - ${formatTime(highlight.end)})`}
        >
          <Play className="w-5 h-5 ml-0.5" fill={isSelected ? 'currentColor' : 'none'} />
        </button>
        
        {/* Info */}
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-star-white mb-1 line-clamp-1">
            {highlight.title}
          </h3>
          
          <p className="text-star-white/60 text-sm mb-2 line-clamp-2">
            {highlight.description}
          </p>
          
          {/* Meta */}
          <div className="flex items-center gap-3 text-xs text-star-white/40">
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {formatTime(highlight.start)} - {formatTime(highlight.end)}
            </span>
            <span className="flex items-center gap-1">
              {Math.round(duration)}s
            </span>
          </div>
          
          {/* Tags */}
          {highlight.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {highlight.tags.slice(0, 3).map((tag) => (
                <span
                  key={tag}
                  className="px-2 py-0.5 rounded-full text-xs bg-void-700 text-star-white/60"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
      
      {/* Selection indicator */}
      {isSelected && (
        <motion.div
          layoutId="highlight-selection"
          className="absolute inset-0 rounded-xl border-2 border-nebula-purple pointer-events-none"
          transition={{ type: 'spring', stiffness: 500, damping: 30 }}
        />
      )}
    </motion.div>
  )
}
