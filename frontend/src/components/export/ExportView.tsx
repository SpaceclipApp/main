'use client'

import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Download, 
  Loader2, 
  Check, 
  Instagram, 
  Youtube, 
  Twitter,
  Linkedin,
  ArrowLeft,
  Palette,
  Type,
  Play,
  Pause,
  Volume2,
  Scissors
} from 'lucide-react'
import { cn, formatDuration, formatTime } from '@/lib/utils'
import { useProjectStore } from '@/store/project'
import { Button } from '@/components/ui/Button'
import { ClipRangeEditor } from '@/components/player/ClipRangeEditor'
import { Platform, createClips, getDownloadUrl, updateClipRange } from '@/lib/api'

const platformConfigs: Record<Platform, { 
  name: string
  icon: React.ElementType
  color: string
  bgColor: string
}> = {
  instagram_feed: { name: 'Instagram Feed', icon: Instagram, color: 'text-pink-400', bgColor: 'bg-pink-500/20' },
  instagram_reels: { name: 'Instagram Reels', icon: Instagram, color: 'text-pink-400', bgColor: 'bg-pink-500/20' },
  tiktok: { name: 'TikTok', icon: () => (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
      <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 5 20.1a6.34 6.34 0 0 0 10.86-4.43v-7a8.16 8.16 0 0 0 4.77 1.52v-3.4a4.85 4.85 0 0 1-1-.1z"/>
    </svg>
  ), color: 'text-white', bgColor: 'bg-black/50' },
  youtube: { name: 'YouTube', icon: Youtube, color: 'text-red-500', bgColor: 'bg-red-500/20' },
  youtube_shorts: { name: 'YouTube Shorts', icon: Youtube, color: 'text-red-500', bgColor: 'bg-red-500/20' },
  linkedin: { name: 'LinkedIn', icon: Linkedin, color: 'text-blue-400', bgColor: 'bg-blue-500/20' },
  twitter: { name: 'Twitter/X', icon: Twitter, color: 'text-white', bgColor: 'bg-gray-700/50' },
}

const audiogramStyles = [
  { id: 'cosmic', name: 'Cosmic', colors: ['#7c3aed', '#a855f7'] },
  { id: 'neon', name: 'Neon', colors: ['#00ff88', '#00ffff'] },
  { id: 'sunset', name: 'Sunset', colors: ['#e94560', '#ffd93d'] },
  { id: 'minimal', name: 'Minimal', colors: ['#ffffff', '#000000'] },
]

// Generate SVG waveform path that mimics FFmpeg showwaves output
function generateWaveformPath(width: number, height: number, timeOffset: number = 0): string {
  const points: string[] = []
  const centerY = height / 2
  const segments = 100
  
  for (let i = 0; i <= segments; i++) {
    const x = (i / segments) * width
    
    // Create a natural-looking audio waveform pattern
    // Mix multiple frequencies for realistic look
    const t = i / segments + timeOffset * 0.1
    const wave1 = Math.sin(t * Math.PI * 8) * 0.3
    const wave2 = Math.sin(t * Math.PI * 15 + 1.3) * 0.2
    const wave3 = Math.sin(t * Math.PI * 25 + 2.1) * 0.15
    const wave4 = Math.sin(t * Math.PI * 40) * 0.1
    
    // Combine waves with amplitude envelope
    const envelope = Math.sin(t * Math.PI) * 0.5 + 0.5
    const combinedWave = (wave1 + wave2 + wave3 + wave4) * envelope
    
    const y = centerY + combinedWave * (height * 0.8)
    
    if (i === 0) {
      points.push(`M ${x} ${y}`)
    } else {
      points.push(`L ${x} ${y}`)
    }
  }
  
  return points.join(' ')
}

// Clip preview component that matches actual export style
function ClipPreview({ 
  media, 
  range, 
  title, 
  audiogramStyle 
}: { 
  media: any
  range: { start: number; end: number }
  title: string
  audiogramStyle: string
}) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const audioRef = useRef<HTMLAudioElement>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  
  const isVideo = media.media_type === 'video'
  const isYouTube = media.source_url?.includes('youtube.com') || media.source_url?.includes('youtu.be')
  const duration = range.end - range.start
  
  // Get YouTube video ID
  const getYouTubeId = (url: string) => {
    const match = url?.match(/(?:youtu\.be\/|youtube\.com(?:\/embed\/|\/v\/|\/watch\?v=|\/watch\?.+&v=))([^&?\s]+)/)
    return match ? match[1] : null
  }
  
  const youtubeId = isYouTube ? getYouTubeId(media.source_url) : null
  
  const handlePlayPause = () => {
    const el = isVideo ? videoRef.current : audioRef.current
    if (!el) return
    
    if (isPlaying) {
      el.pause()
    } else {
      el.currentTime = range.start
      el.play()
    }
    setIsPlaying(!isPlaying)
  }
  
  useEffect(() => {
    const el = isVideo ? videoRef.current : audioRef.current
    if (!el) return
    
    const handleTimeUpdate = () => {
      setCurrentTime(el.currentTime - range.start)
      if (el.currentTime >= range.end) {
        el.pause()
        setIsPlaying(false)
        el.currentTime = range.start
      }
    }
    
    el.addEventListener('timeupdate', handleTimeUpdate)
    return () => el.removeEventListener('timeupdate', handleTimeUpdate)
  }, [range, isVideo])
  
  // Theme colors matching the backend audiogram generator
  const themeColors: Record<string, { bg: string; wave: string; accent: string }> = {
    cosmic: { bg: '#0f0a1f', wave: '#a855f7', accent: '#7c3aed' },
    neon: { bg: '#000000', wave: '#00ffff', accent: '#00ff88' },
    sunset: { bg: '#1a1a2e', wave: '#ff6b6b', accent: '#e94560' },
    minimal: { bg: '#ffffff', wave: '#333333', accent: '#000000' },
  }
  
  const colors = themeColors[audiogramStyle] || themeColors.cosmic
  const isMinimal = audiogramStyle === 'minimal'
  
  return (
    <div className="space-y-3">
      <div className="aspect-[9/16] max-h-80 mx-auto rounded-xl flex items-center justify-center relative overflow-hidden" style={{ background: colors.bg }}>
        {isYouTube && youtubeId ? (
          <iframe
            src={`https://www.youtube.com/embed/${youtubeId}?start=${Math.floor(range.start)}&end=${Math.floor(range.end)}&autoplay=0`}
            className="w-full h-full"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        ) : isVideo ? (
          <video 
            ref={videoRef}
            src={`http://localhost:8000/uploads/${media.file_path?.split('/').pop()}`}
            className="w-full h-full object-cover"
          />
        ) : (
          <>
            <audio 
              ref={audioRef}
              src={`http://localhost:8000/uploads/${media.file_path?.split('/').pop()}`}
            />
            {/* Audiogram preview - matches export layout exactly */}
            <div className="absolute inset-0 flex flex-col">
              {/* Title at top - 12% from top like the export */}
              <div className="pt-[12%] px-4 text-center">
                <p className={cn(
                  "font-medium",
                  isMinimal ? "text-black" : "text-white"
                )} style={{ fontSize: 'clamp(12px, 5vw, 16px)' }}>
                  {title}
                </p>
              </div>
              
              {/* Waveform visualization - positioned at ~50% like export */}
              <div className="absolute left-[7.5%] right-[7.5%]" style={{ top: '50%', transform: 'translateY(-50%)' }}>
                {/* SVG waveform line matching FFmpeg showwaves mode=cline output */}
                <svg 
                  viewBox="0 0 200 40" 
                  className="w-full h-12"
                  preserveAspectRatio="none"
                >
                  <defs>
                    <linearGradient id={`waveGradient-${audiogramStyle}`} x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stopColor={colors.wave} stopOpacity="0.6" />
                      <stop offset="50%" stopColor={colors.wave} stopOpacity="1" />
                      <stop offset="100%" stopColor={colors.wave} stopOpacity="0.6" />
                    </linearGradient>
                  </defs>
                  {/* Generate waveform path that looks like audio */}
                  <path
                    d={generateWaveformPath(200, 40, isPlaying ? currentTime : 0)}
                    fill="none"
                    stroke={`url(#waveGradient-${audiogramStyle})`}
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
              
              {/* Progress bar - at 65% from top like export */}
              <div className="absolute left-[7.5%] right-[7.5%]" style={{ top: '65%' }}>
                {/* Background bar */}
                <div 
                  className="h-1 rounded-full overflow-hidden"
                  style={{ background: isMinimal ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.15)' }}
                >
                  {/* Animated progress */}
                  <div 
                    className="h-full rounded-full transition-all duration-100"
                    style={{ 
                      background: colors.accent,
                      width: `${Math.min(100, (currentTime / duration) * 100)}%`
                    }}
                  />
                </div>
              </div>
              
              {/* SpaceClip branding - bottom right corner */}
              <div className={cn(
                "absolute bottom-3 right-4 text-[10px] font-medium",
                isMinimal ? "text-black/40" : "text-white/40"
              )}>
                SpaceClip
              </div>
            </div>
          </>
        )}
        
        {/* Play button overlay for non-YouTube */}
        {!isYouTube && (
          <button
            onClick={handlePlayPause}
            className="absolute inset-0 flex items-center justify-center bg-black/10 hover:bg-black/20 transition-colors z-10"
          >
            <div className="w-12 h-12 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
              {isPlaying ? (
                <Pause className="w-5 h-5 text-white" />
              ) : (
                <Play className="w-5 h-5 text-white ml-0.5" />
              )}
            </div>
          </button>
        )}
      </div>
      
      {/* Clip info */}
      <div className="text-center">
        <p className="text-star-white/80 text-sm font-medium">{title}</p>
        <p className="text-star-white/40 text-xs">
          {formatTime(range.start)} - {formatTime(range.end)} ({formatDuration(duration)})
        </p>
      </div>
    </div>
  )
}

export function ExportView() {
  const {
    media,
    selectedHighlight,
    clipRange,
    setClipRange,
    transcription,
    selectedPlatforms,
    togglePlatform,
    includeCaption,
    setIncludeCaption,
    audiogramStyle,
    setAudiogramStyle,
    addClips,
    clips,
    setStep,
  } = useProjectStore()
  
  const [isExporting, setIsExporting] = useState(false)
  const [exportProgress, setExportProgress] = useState<Record<Platform, 'pending' | 'processing' | 'complete'>>({} as any)
  const [error, setError] = useState<string | null>(null)
  const [updatedCaptions, setUpdatedCaptions] = useState<any[]>([])
  
  // Handle clip range commit (when user finishes dragging handles)
  const handleRangeCommit = async (start: number, end: number) => {
    if (!media) return
    
    try {
      const response = await updateClipRange(
        media.id,
        start,
        end,
        selectedHighlight?.id
      )
      // Update captions for the new range
      setUpdatedCaptions(response.captions)
    } catch (err) {
      console.error('Failed to update clip range:', err)
    }
  }
  
  const range = clipRange || (selectedHighlight ? { start: selectedHighlight.start, end: selectedHighlight.end } : null)
  
  const handleExport = async () => {
    if (!media || !range || selectedPlatforms.length === 0) return
    
    setIsExporting(true)
    setError(null)
    
    // Initialize progress
    const progress: Record<Platform, 'pending' | 'processing' | 'complete'> = {} as any
    selectedPlatforms.forEach(p => progress[p] = 'pending')
    setExportProgress(progress)
    
    try {
      // Mark all as processing
      selectedPlatforms.forEach(p => {
        progress[p] = 'processing'
      })
      setExportProgress({ ...progress })
      
      // Create clips
      const newClips = await createClips({
        media_id: media.id,
        start: range.start,
        end: range.end,
        title: selectedHighlight?.title,
        platforms: selectedPlatforms,
        include_captions: includeCaption,
        audiogram_style: audiogramStyle,
      })
      
      addClips(newClips)
      
      // Mark all as complete
      selectedPlatforms.forEach(p => {
        progress[p] = 'complete'
      })
      setExportProgress({ ...progress })
      
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Export failed')
    } finally {
      setIsExporting(false)
    }
  }
  
  if (!media || !range) {
    return null
  }
  
  const clipDuration = range.end - range.start
  
  return (
    <div className="w-full max-w-4xl mx-auto">
      {/* Back button */}
      <button
        onClick={() => setStep('highlights')}
        className="flex items-center gap-2 text-star-white/60 hover:text-star-white mb-6 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to highlights
      </button>
      
      <div className="grid md:grid-cols-2 gap-6">
        {/* Left: Preview & Settings */}
        <div className="space-y-6">
          {/* Clip preview */}
          <div className="glass-card p-5">
            <h3 className="font-semibold text-star-white mb-4">Clip Preview</h3>
            
            <ClipPreview 
              media={media}
              range={range}
              title={selectedHighlight?.title || 'Custom Clip'}
              audiogramStyle={audiogramStyle}
            />
          </div>
          
          {/* Clip Range Editor - Drag handles for adjusting boundaries */}
          <div className="glass-card p-5">
            <div className="flex items-center gap-2 mb-4">
              <Scissors className="w-4 h-4 text-nebula-violet" />
              <h3 className="font-semibold text-star-white">Adjust Clip Boundaries</h3>
            </div>
            
            <ClipRangeEditor
              duration={media.duration}
              clipRange={range}
              onRangeChange={(start, end) => setClipRange(start, end)}
              onRangeCommit={handleRangeCommit}
              transcription={transcription?.segments}
              minClipDuration={5}
              maxClipDuration={180}
            />
            
            {/* Show updated caption count */}
            {updatedCaptions.length > 0 && (
              <p className="text-xs text-star-white/40 mt-2">
                {updatedCaptions.length} caption segments in selection
              </p>
            )}
          </div>
          
          {/* Audiogram style selector */}
          {media.media_type === 'audio' && (
            <div className="glass-card p-5">
              <div className="flex items-center gap-2 mb-4">
                <Palette className="w-4 h-4 text-nebula-violet" />
                <h3 className="font-semibold text-star-white">Audiogram Style</h3>
              </div>
              
              <div className="grid grid-cols-2 gap-2">
                {audiogramStyles.map((style) => (
                  <button
                    key={style.id}
                    onClick={() => setAudiogramStyle(style.id)}
                    className={cn(
                      'p-3 rounded-xl transition-all duration-200',
                      'border flex items-center gap-3',
                      audiogramStyle === style.id
                        ? 'border-nebula-purple bg-nebula-purple/10'
                        : 'border-void-600 hover:border-void-500'
                    )}
                  >
                    <div 
                      className="w-8 h-8 rounded-lg"
                      style={{
                        background: `linear-gradient(135deg, ${style.colors[0]}, ${style.colors[1]})`
                      }}
                    />
                    <span className="text-sm text-star-white">{style.name}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
          
          {/* Caption toggle */}
          <div className="glass-card p-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Type className="w-4 h-4 text-nebula-violet" />
                <span className="font-medium text-star-white">Include Captions</span>
              </div>
              
              <button
                onClick={() => setIncludeCaption(!includeCaption)}
                className={cn(
                  'relative w-12 h-6 rounded-full transition-all duration-300',
                  includeCaption ? 'bg-nebula-purple' : 'bg-void-700'
                )}
              >
                <motion.div
                  className="absolute top-1 w-4 h-4 rounded-full bg-white"
                  animate={{ left: includeCaption ? 28 : 4 }}
                  transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                />
              </button>
            </div>
            
            <p className="text-star-white/40 text-sm mt-2">
              Auto-generated captions from transcript
            </p>
          </div>
        </div>
        
        {/* Right: Platform selection */}
        <div className="space-y-6">
          <div className="glass-card p-5">
            <h3 className="font-semibold text-star-white mb-4">Export Platforms</h3>
            
            <div className="space-y-2">
              {(Object.keys(platformConfigs) as Platform[]).map((platform) => {
                const config = platformConfigs[platform]
                const Icon = config.icon
                const isSelected = selectedPlatforms.includes(platform)
                const status = exportProgress[platform]
                
                return (
                  <motion.button
                    key={platform}
                    onClick={() => !isExporting && togglePlatform(platform)}
                    disabled={isExporting}
                    className={cn(
                      'w-full p-3 rounded-xl flex items-center gap-3 transition-all duration-200',
                      'border',
                      isSelected
                        ? 'border-nebula-purple bg-nebula-purple/10'
                        : 'border-void-600 hover:border-void-500',
                      isExporting && 'opacity-70 cursor-not-allowed'
                    )}
                    whileHover={!isExporting ? { scale: 1.02 } : undefined}
                    whileTap={!isExporting ? { scale: 0.98 } : undefined}
                  >
                    <div className={cn(
                      'w-10 h-10 rounded-lg flex items-center justify-center',
                      config.bgColor
                    )}>
                      <Icon className={cn('w-5 h-5', config.color)} />
                    </div>
                    
                    <span className="flex-1 text-left font-medium text-star-white">
                      {config.name}
                    </span>
                    
                    {status === 'processing' && (
                      <Loader2 className="w-5 h-5 text-nebula-violet animate-spin" />
                    )}
                    {status === 'complete' && (
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        className="w-6 h-6 rounded-full bg-aurora-green flex items-center justify-center"
                      >
                        <Check className="w-4 h-4 text-white" />
                      </motion.div>
                    )}
                    {!status && (
                      <div className={cn(
                        'w-5 h-5 rounded border-2 transition-all',
                        isSelected
                          ? 'border-nebula-purple bg-nebula-purple'
                          : 'border-void-500'
                      )}>
                        {isSelected && <Check className="w-full h-full text-white" />}
                      </div>
                    )}
                  </motion.button>
                )
              })}
            </div>
          </div>
          
          {/* Export button */}
          <Button
            onClick={handleExport}
            disabled={selectedPlatforms.length === 0 || isExporting}
            isLoading={isExporting}
            className="w-full"
            size="lg"
          >
            {isExporting ? 'Creating Clips...' : `Export ${selectedPlatforms.length} Clip${selectedPlatforms.length !== 1 ? 's' : ''}`}
          </Button>
          
          {/* Error */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="p-4 rounded-xl bg-red-900/20 border border-red-500/30 text-red-400 text-sm"
              >
                {error}
              </motion.div>
            )}
          </AnimatePresence>
          
          {/* Generated clips */}
          {clips.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-card p-5"
            >
              <h3 className="font-semibold text-star-white mb-4">
                Ready to Download
              </h3>
              
              <div className="space-y-2">
                {clips.map((clip) => {
                  const config = platformConfigs[clip.platform as Platform]
                  const Icon = config?.icon || Download
                  
                  return (
                    <a
                      key={clip.id}
                      href={getDownloadUrl(clip.id)}
                      download
                      className="flex items-center gap-3 p-3 rounded-lg bg-void-800/50 hover:bg-void-700/50 transition-colors"
                    >
                      <div className={cn('w-8 h-8 rounded flex items-center justify-center', config?.bgColor || 'bg-void-700')}>
                        <Icon className={cn('w-4 h-4', config?.color || 'text-star-white')} />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm text-star-white">{config?.name || clip.platform}</p>
                        <p className="text-xs text-star-white/40">
                          {clip.width}x{clip.height} • {formatDuration(clip.duration)}
                        </p>
                      </div>
                      <Download className="w-4 h-4 text-nebula-violet" />
                    </a>
                  )
                })}
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  )
}


