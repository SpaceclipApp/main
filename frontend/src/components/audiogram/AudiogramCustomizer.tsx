'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Palette, Type, Image, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface AudiogramSettings {
  style: 'waveform' | 'bars' | 'circle' | 'spectrum'
  colorScheme: string
  backgroundColor: string
  waveformColor: string
  textColor: string
  showTitle: boolean
  showSpeaker: boolean
  fontFamily: string
  logoUrl?: string
}

const presetThemes = [
  {
    id: 'cosmic',
    name: 'Cosmic',
    backgroundColor: '#0f0f23',
    waveformColor: '#7c3aed',
    textColor: '#ffffff',
  },
  {
    id: 'neon',
    name: 'Neon',
    backgroundColor: '#000000',
    waveformColor: '#00ff88',
    textColor: '#ffffff',
  },
  {
    id: 'sunset',
    name: 'Sunset',
    backgroundColor: '#1a1a2e',
    waveformColor: '#e94560',
    textColor: '#ffffff',
  },
  {
    id: 'minimal',
    name: 'Minimal',
    backgroundColor: '#ffffff',
    waveformColor: '#000000',
    textColor: '#000000',
  },
  {
    id: 'ocean',
    name: 'Ocean',
    backgroundColor: '#0c1445',
    waveformColor: '#00d4ff',
    textColor: '#ffffff',
  },
  {
    id: 'forest',
    name: 'Forest',
    backgroundColor: '#0d1f0d',
    waveformColor: '#4ade80',
    textColor: '#ffffff',
  },
]

const visualizationStyles = [
  { id: 'waveform', name: 'Waveform', icon: '〰️' },
  { id: 'bars', name: 'Bars', icon: '📊' },
  { id: 'circle', name: 'Circle', icon: '⭕' },
  { id: 'spectrum', name: 'Spectrum', icon: '🌈' },
]

const fontOptions = [
  { id: 'inter', name: 'Inter', family: 'Inter, sans-serif' },
  { id: 'space', name: 'Space Grotesk', family: 'Space Grotesk, sans-serif' },
  { id: 'mono', name: 'JetBrains Mono', family: 'JetBrains Mono, monospace' },
  { id: 'serif', name: 'Playfair', family: 'Playfair Display, serif' },
]

interface AudiogramCustomizerProps {
  settings: AudiogramSettings
  onChange: (settings: AudiogramSettings) => void
  className?: string
}

export function AudiogramCustomizer({ settings, onChange, className }: AudiogramCustomizerProps) {
  const [activeTab, setActiveTab] = useState<'theme' | 'style' | 'text' | 'brand'>('theme')
  
  const updateSetting = <K extends keyof AudiogramSettings>(
    key: K, 
    value: AudiogramSettings[K]
  ) => {
    onChange({ ...settings, [key]: value })
  }
  
  const applyTheme = (theme: typeof presetThemes[0]) => {
    onChange({
      ...settings,
      colorScheme: theme.id,
      backgroundColor: theme.backgroundColor,
      waveformColor: theme.waveformColor,
      textColor: theme.textColor,
    })
  }
  
  return (
    <div className={cn('glass-card', className)}>
      {/* Tab navigation */}
      <div className="flex border-b border-void-700">
        {[
          { id: 'theme', label: 'Theme', icon: Palette },
          { id: 'style', label: 'Style', icon: Sparkles },
          { id: 'text', label: 'Text', icon: Type },
          { id: 'brand', label: 'Brand', icon: Image },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={cn(
              'flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium transition-colors',
              activeTab === tab.id
                ? 'text-nebula-violet border-b-2 border-nebula-purple'
                : 'text-star-white/60 hover:text-star-white'
            )}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>
      
      <div className="p-4">
        {/* Theme tab */}
        {activeTab === 'theme' && (
          <div className="space-y-4">
            <p className="text-sm text-star-white/60">Choose a color theme</p>
            <div className="grid grid-cols-3 gap-2">
              {presetThemes.map((theme) => (
                <button
                  key={theme.id}
                  onClick={() => applyTheme(theme)}
                  className={cn(
                    'p-3 rounded-lg border-2 transition-all',
                    settings.colorScheme === theme.id
                      ? 'border-nebula-purple'
                      : 'border-transparent hover:border-void-600'
                  )}
                  style={{ backgroundColor: theme.backgroundColor }}
                >
                  <div 
                    className="h-8 rounded mb-2"
                    style={{ 
                      background: `linear-gradient(90deg, ${theme.waveformColor}40, ${theme.waveformColor})` 
                    }}
                  />
                  <span 
                    className="text-xs font-medium"
                    style={{ color: theme.textColor }}
                  >
                    {theme.name}
                  </span>
                </button>
              ))}
            </div>
            
            {/* Custom colors */}
            <div className="pt-4 border-t border-void-700">
              <p className="text-sm text-star-white/60 mb-3">Custom colors</p>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-star-white/40 mb-1">Background</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="color"
                      value={settings.backgroundColor}
                      onChange={(e) => updateSetting('backgroundColor', e.target.value)}
                      className="w-8 h-8 rounded cursor-pointer"
                    />
                    <input
                      type="text"
                      value={settings.backgroundColor}
                      onChange={(e) => updateSetting('backgroundColor', e.target.value)}
                      className="flex-1 px-2 py-1 rounded bg-void-800 text-star-white text-xs font-mono"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs text-star-white/40 mb-1">Waveform</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="color"
                      value={settings.waveformColor}
                      onChange={(e) => updateSetting('waveformColor', e.target.value)}
                      className="w-8 h-8 rounded cursor-pointer"
                    />
                    <input
                      type="text"
                      value={settings.waveformColor}
                      onChange={(e) => updateSetting('waveformColor', e.target.value)}
                      className="flex-1 px-2 py-1 rounded bg-void-800 text-star-white text-xs font-mono"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
        
        {/* Style tab */}
        {activeTab === 'style' && (
          <div className="space-y-4">
            <p className="text-sm text-star-white/60">Visualization style</p>
            <div className="grid grid-cols-2 gap-2">
              {visualizationStyles.map((style) => (
                <button
                  key={style.id}
                  onClick={() => updateSetting('style', style.id as AudiogramSettings['style'])}
                  className={cn(
                    'p-4 rounded-lg border-2 transition-all text-center',
                    settings.style === style.id
                      ? 'border-nebula-purple bg-nebula-purple/10'
                      : 'border-void-600 hover:border-void-500'
                  )}
                >
                  <span className="text-2xl mb-2 block">{style.icon}</span>
                  <span className="text-sm text-star-white">{style.name}</span>
                </button>
              ))}
            </div>
          </div>
        )}
        
        {/* Text tab */}
        {activeTab === 'text' && (
          <div className="space-y-4">
            <div>
              <p className="text-sm text-star-white/60 mb-3">Font family</p>
              <div className="grid grid-cols-2 gap-2">
                {fontOptions.map((font) => (
                  <button
                    key={font.id}
                    onClick={() => updateSetting('fontFamily', font.family)}
                    className={cn(
                      'p-3 rounded-lg border-2 transition-all',
                      settings.fontFamily === font.family
                        ? 'border-nebula-purple bg-nebula-purple/10'
                        : 'border-void-600 hover:border-void-500'
                    )}
                    style={{ fontFamily: font.family }}
                  >
                    <span className="text-star-white">{font.name}</span>
                  </button>
                ))}
              </div>
            </div>
            
            <div className="pt-4 border-t border-void-700">
              <p className="text-sm text-star-white/60 mb-3">Display options</p>
              <div className="space-y-2">
                <label className="flex items-center justify-between">
                  <span className="text-sm text-star-white">Show title</span>
                  <button
                    onClick={() => updateSetting('showTitle', !settings.showTitle)}
                    className={cn(
                      'w-10 h-6 rounded-full transition-colors',
                      settings.showTitle ? 'bg-nebula-purple' : 'bg-void-700'
                    )}
                  >
                    <motion.div
                      className="w-4 h-4 bg-white rounded-full"
                      animate={{ x: settings.showTitle ? 22 : 4 }}
                    />
                  </button>
                </label>
                <label className="flex items-center justify-between">
                  <span className="text-sm text-star-white">Show speaker names</span>
                  <button
                    onClick={() => updateSetting('showSpeaker', !settings.showSpeaker)}
                    className={cn(
                      'w-10 h-6 rounded-full transition-colors',
                      settings.showSpeaker ? 'bg-nebula-purple' : 'bg-void-700'
                    )}
                  >
                    <motion.div
                      className="w-4 h-4 bg-white rounded-full"
                      animate={{ x: settings.showSpeaker ? 22 : 4 }}
                    />
                  </button>
                </label>
              </div>
            </div>
          </div>
        )}
        
        {/* Brand tab */}
        {activeTab === 'brand' && (
          <div className="space-y-4">
            <p className="text-sm text-star-white/60">Upload your logo</p>
            <div className="border-2 border-dashed border-void-600 rounded-lg p-8 text-center hover:border-nebula-purple/50 transition-colors cursor-pointer">
              <Image className="w-8 h-8 mx-auto mb-2 text-star-white/40" />
              <p className="text-sm text-star-white/60">
                Drag & drop or click to upload
              </p>
              <p className="text-xs text-star-white/40 mt-1">
                PNG, SVG up to 2MB
              </p>
            </div>
            
            {settings.logoUrl && (
              <div className="flex items-center gap-3 p-3 bg-void-800 rounded-lg">
                <img 
                  src={settings.logoUrl} 
                  alt="Logo" 
                  className="w-10 h-10 object-contain"
                />
                <span className="flex-1 text-sm text-star-white truncate">
                  logo.png
                </span>
                <button 
                  onClick={() => updateSetting('logoUrl', undefined)}
                  className="text-red-400 text-sm hover:text-red-300"
                >
                  Remove
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export const defaultAudiogramSettings: AudiogramSettings = {
  style: 'waveform',
  colorScheme: 'cosmic',
  backgroundColor: '#0f0f23',
  waveformColor: '#7c3aed',
  textColor: '#ffffff',
  showTitle: true,
  showSpeaker: true,
  fontFamily: 'Space Grotesk, sans-serif',
}




