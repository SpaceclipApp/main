'use client'

import { motion } from 'framer-motion'
import { Eye, Check } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Template {
  id: string
  name: string
  description: string
  colors: {
    background: string
    waveform: string
    text: string
    accent: string
  }
  preview: {
    waveformColor: string
    accentColor: string
  }
}

const templates: Template[] = [
  {
    id: 'cosmic',
    name: 'Cosmic',
    description: 'Deep space vibes with purple gradients',
    colors: {
      background: '#0f0a1f',
      waveform: '#a855f7',
      text: '#ffffff',
      accent: '#7c3aed',
    },
    preview: {
      waveformColor: '#a855f7',
      accentColor: '#7c3aed',
    },
  },
  {
    id: 'neon',
    name: 'Neon',
    description: 'High-energy cyberpunk aesthetic',
    colors: {
      background: '#000000',
      waveform: '#00ffff',
      text: '#ffffff',
      accent: '#00ff88',
    },
    preview: {
      waveformColor: '#00ffff',
      accentColor: '#00ff88',
    },
  },
  {
    id: 'sunset',
    name: 'Sunset',
    description: 'Warm, vibrant sunset tones',
    colors: {
      background: '#1a1a2e',
      waveform: '#ff6b6b',
      text: '#ffffff',
      accent: '#e94560',
    },
    preview: {
      waveformColor: '#ff6b6b',
      accentColor: '#e94560',
    },
  },
  {
    id: 'minimal',
    name: 'Minimal',
    description: 'Clean, professional black and white',
    colors: {
      background: '#ffffff',
      waveform: '#333333',
      text: '#000000',
      accent: '#000000',
    },
    preview: {
      waveformColor: '#333333',
      accentColor: '#000000',
    },
  },
]

interface TemplateGalleryProps {
  selectedTemplate?: string
  onSelect?: (templateId: string) => void
  readOnly?: boolean
  className?: string
}

/**
 * TemplateGallery - Read-only gallery of available export templates
 * 
 * Shows all available audiogram templates with previews.
 * Can be used in read-only mode or with selection capability.
 */
export function TemplateGallery({ 
  selectedTemplate, 
  onSelect,
  readOnly = true,
  className 
}: TemplateGalleryProps) {
  return (
    <div className={cn('space-y-4', className)}>
      <div className="flex items-center gap-2 mb-4">
        <Eye className="w-4 h-4 text-nebula-violet" />
        <h3 className="font-semibold text-star-white">Available Templates</h3>
        {readOnly && (
          <span className="text-xs text-star-white/40">(Read-only preview)</span>
        )}
      </div>
      
      <div className="grid grid-cols-2 gap-4">
        {templates.map((template) => {
          const isSelected = selectedTemplate === template.id
          
          return (
            <motion.div
              key={template.id}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              whileHover={!readOnly ? { scale: 1.02 } : undefined}
              onClick={() => !readOnly && onSelect?.(template.id)}
              className={cn(
                'relative rounded-xl overflow-hidden border-2 transition-all cursor-pointer',
                isSelected && !readOnly
                  ? 'border-nebula-purple bg-nebula-purple/10'
                  : 'border-void-600 hover:border-void-500',
                readOnly && 'cursor-default'
              )}
            >
              {/* Preview */}
              <div
                className="aspect-[9/16] relative"
                style={{ background: template.colors.background }}
              >
                {/* Waveform preview */}
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="w-full px-4">
                    <svg viewBox="0 0 200 40" className="w-full h-12" preserveAspectRatio="none">
                      <defs>
                        <linearGradient id={`preview-${template.id}`} x1="0%" y1="0%" x2="100%" y2="0%">
                          <stop offset="0%" stopColor={template.preview.waveformColor} stopOpacity="0.6" />
                          <stop offset="50%" stopColor={template.preview.waveformColor} stopOpacity="1" />
                          <stop offset="100%" stopColor={template.preview.waveformColor} stopOpacity="0.6" />
                        </linearGradient>
                      </defs>
                      <path
                        d="M 0 20 L 20 15 L 40 25 L 60 10 L 80 30 L 100 5 L 120 28 L 140 12 L 160 22 L 180 8 L 200 20"
                        fill="none"
                        stroke={`url(#preview-${template.id})`}
                        strokeWidth="2"
                        strokeLinecap="round"
                      />
                    </svg>
                  </div>
                </div>
                
                {/* Progress bar preview */}
                <div className="absolute bottom-8 left-4 right-4">
                  <div 
                    className="h-1 rounded-full"
                    style={{ 
                      background: template.colors.text === '#ffffff' 
                        ? 'rgba(255,255,255,0.15)' 
                        : 'rgba(0,0,0,0.1)' 
                    }}
                  >
                    <div 
                      className="h-full rounded-full"
                      style={{ 
                        background: template.preview.accentColor,
                        width: '60%'
                      }}
                    />
                  </div>
                </div>
                
                {/* Selected indicator */}
                {isSelected && !readOnly && (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="absolute top-2 right-2 w-6 h-6 rounded-full bg-nebula-purple flex items-center justify-center"
                  >
                    <Check className="w-4 h-4 text-white" />
                  </motion.div>
                )}
              </div>
              
              {/* Template info */}
              <div className="p-3 bg-void-900/50">
                <h4 className={cn(
                  'font-medium text-sm mb-1',
                  template.colors.text === '#ffffff' ? 'text-white' : 'text-black'
                )} style={{ color: template.colors.text }}>
                  {template.name}
                </h4>
                <p className="text-xs text-star-white/40 line-clamp-2">
                  {template.description}
                </p>
              </div>
            </motion.div>
          )
        })}
      </div>
      
      {readOnly && (
        <p className="text-xs text-star-white/40 text-center pt-2">
          Templates are automatically synced with export output
        </p>
      )}
    </div>
  )
}
