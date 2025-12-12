'use client'

import { useState, useMemo, useRef } from 'react'
import { motion } from 'framer-motion'
import { Sparkles, ChevronRight, Sliders, Clock, Film, Music } from 'lucide-react'
import { useProjectStore } from '@/store/project'
import { Button } from '@/components/ui/Button'
import { HighlightCard } from './HighlightCard'
import { TranscriptViewer } from './TranscriptViewer'
import { MoreHighlightsButton } from './MoreHighlightsButton'
import { MediaPlayer, MediaPlayerRef } from '@/components/player/MediaPlayer'
import { formatDuration } from '@/lib/utils'

export function HighlightsView() {
  const {
    media,
    highlights,
    transcription,
    selectedHighlight,
    selectHighlight,
    clipRange,
    setClipRange,
    setStep,
  } = useProjectStore()
  
  const [showTranscript, setShowTranscript] = useState(false)
  const playerRef = useRef<MediaPlayerRef>(null)
  
  const sortedHighlights = useMemo(() => {
    if (!highlights?.highlights) return []
    return [...highlights.highlights].sort((a, b) => b.score - a.score)
  }, [highlights])
  
  const handleContinue = () => {
    if (selectedHighlight || clipRange) {
      setStep('export')
    }
  }
  
  const handlePlayHighlight = (highlight: typeof sortedHighlights[0]) => {
    // Select the highlight and seek to its start time
    selectHighlight(highlight)
    
    if (playerRef.current) {
      playerRef.current.seekTo(highlight.start)
      playerRef.current.play()
    }
  }
  
  if (!highlights || !media) {
    return null
  }
  
  // Build media URL - check if it's a YouTube URL or local file
  const isYouTube = media.source_url?.includes('youtube.com') || media.source_url?.includes('youtu.be')
  const mediaUrl = media.source_url || `http://localhost:8000/uploads/${media.filename}`
  
  return (
    <div className="w-full max-w-6xl mx-auto">
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Highlights list */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-nebula-purple/20 flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-nebula-violet" />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-star-white">
                  AI Highlights
                </h2>
                <p className="text-star-white/60 text-sm">
                  {sortedHighlights.length} clips detected • Click play to preview
                </p>
              </div>
            </div>
            
            <button
              onClick={() => setShowTranscript(!showTranscript)}
              className="text-sm text-nebula-violet hover:text-nebula-pink transition-colors"
            >
              {showTranscript ? 'Hide' : 'Show'} Transcript
            </button>
          </div>
          
          {/* Highlight cards */}
          <div className="space-y-3">
            {sortedHighlights.map((highlight, index) => (
              <HighlightCard
                key={highlight.id}
                highlight={highlight}
                isSelected={selectedHighlight?.id === highlight.id}
                onSelect={() => selectHighlight(highlight)}
                onPlay={() => handlePlayHighlight(highlight)}
                index={index}
              />
            ))}
          </div>
          
          {/* Find more highlights */}
          <MoreHighlightsButton />
          
          {/* Transcript viewer */}
          {showTranscript && transcription && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-6"
            >
              <TranscriptViewer
                transcription={transcription}
                clipRange={clipRange}
                onRangeSelect={setClipRange}
                onSegmentClick={(segment) => {
                  // Seek player to segment start time
                  if (playerRef.current) {
                    playerRef.current.seekTo(segment.start)
                  }
                }}
              />
            </motion.div>
          )}
        </div>
        
        {/* Sidebar */}
        <div className="space-y-4">
          {/* Media Player */}
          {isYouTube ? (
            // YouTube embed player - key forces re-render when clip changes
            <div className="glass-card overflow-hidden">
              <div className="aspect-video bg-black">
                <iframe
                  key={`yt-${clipRange?.start || 0}-${clipRange?.end || 0}`}
                  src={`https://www.youtube.com/embed/${getYouTubeVideoId(media.source_url || '')}?start=${Math.floor(clipRange?.start || 0)}&end=${Math.floor(clipRange?.end || media.duration)}&autoplay=0`}
                  className="w-full h-full"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                />
              </div>
              <div className="p-4">
                <p className="text-star-white/60 text-sm">
                  Click play on the video to preview the selected clip
                </p>
                {clipRange && (
                  <p className="text-nebula-violet text-sm mt-2">
                    Clip: {formatDuration(clipRange.start)} - {formatDuration(clipRange.end)} ({formatDuration(clipRange.end - clipRange.start)})
                  </p>
                )}
              </div>
            </div>
          ) : (
            <MediaPlayer
              ref={playerRef}
              src={mediaUrl}
              mediaType={media.media_type as 'audio' | 'video'}
              transcription={transcription?.segments}
              clipRange={clipRange}
              autoSeekToClip={true}
              onTimeUpdate={(time) => {
                // Could sync with transcript here
              }}
            />
          )}
          
          {/* Media info card */}
          <div className="glass-card p-5">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-xl bg-void-700 flex items-center justify-center">
                {media.media_type === 'video' ? (
                  <Film className="w-6 h-6 text-red-400" />
                ) : (
                  <Music className="w-6 h-6 text-nebula-violet" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-medium text-star-white truncate">
                  {media.original_filename}
                </h3>
                <p className="text-star-white/60 text-sm">
                  {media.media_type} • {formatDuration(media.duration)}
                </p>
              </div>
            </div>
            
            {/* Clip range display */}
            {clipRange && (
              <div className="bg-void-900/50 rounded-lg p-3 mt-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-star-white/60">Selected clip</span>
                  <span className="font-mono text-nebula-violet">
                    {formatDuration(clipRange.end - clipRange.start)}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs text-star-white/40 mt-1">
                  <span>{formatDuration(clipRange.start)}</span>
                  <span>{formatDuration(clipRange.end)}</span>
                </div>
              </div>
            )}
          </div>
          
          {/* Selected highlight details */}
          {selectedHighlight && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-card p-5"
            >
              <h3 className="font-semibold text-star-white mb-2">
                {selectedHighlight.title}
              </h3>
              <p className="text-star-white/60 text-sm mb-4">
                {selectedHighlight.description}
              </p>
              
              <div className="flex flex-wrap gap-2 mb-4">
                {selectedHighlight.tags.map((tag) => (
                  <span
                    key={tag}
                    className="px-2 py-1 rounded-full text-xs bg-nebula-purple/20 text-nebula-violet"
                  >
                    #{tag}
                  </span>
                ))}
              </div>
              
              <div className="flex items-center gap-2 text-sm">
                <Clock className="w-4 h-4 text-star-white/40" />
                <span className="text-star-white/60">
                  {formatDuration(selectedHighlight.end - selectedHighlight.start)} clip
                </span>
              </div>
            </motion.div>
          )}
          
          {/* Continue button */}
          <Button
            onClick={handleContinue}
            disabled={!selectedHighlight && !clipRange}
            className="w-full"
            size="lg"
          >
            Continue to Export
            <ChevronRight className="w-5 h-5 ml-2" />
          </Button>
          
          {!selectedHighlight && (
            <p className="text-center text-star-white/40 text-sm">
              Select a highlight to continue
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

// Helper to extract YouTube video ID
function getYouTubeVideoId(url: string): string {
  const match = url.match(/(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/)
  return match?.[1] || ''
}
