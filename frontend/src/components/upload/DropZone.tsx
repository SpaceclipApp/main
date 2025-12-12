'use client'

import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, Link, Film, Mic, X, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/Button'
import { uploadFile, uploadFromUrl } from '@/lib/api'
import { useProjectStore } from '@/store/project'

export function DropZone() {
  const [mode, setMode] = useState<'drop' | 'url'>('drop')
  const [url, setUrl] = useState('')
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const { setMedia, setStep } = useProjectStore()
  
  const handleUpload = async (file: File) => {
    setIsUploading(true)
    setError(null)
    
    try {
      const media = await uploadFile(file)
      setMedia(media)
      setStep('processing')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload file')
    } finally {
      setIsUploading(false)
    }
  }
  
  const handleUrlSubmit = async () => {
    if (!url.trim()) return
    
    setIsUploading(true)
    setError(null)
    
    try {
      const media = await uploadFromUrl(url)
      setMedia(media)
      setStep('processing')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to download from URL')
    } finally {
      setIsUploading(false)
    }
  }
  
  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      handleUpload(acceptedFiles[0])
    }
  }, [])
  
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'video/*': ['.mp4', '.mov', '.avi', '.mkv', '.webm'],
      'audio/*': ['.mp3', '.m4a', '.wav', '.ogg', '.aac', '.flac'],
    },
    maxFiles: 1,
    disabled: isUploading,
  })
  
  return (
    <div className="w-full max-w-2xl mx-auto">
      {/* Mode Toggle */}
      <div className="flex justify-center mb-6">
        <div className="inline-flex bg-void-800/50 rounded-xl p-1 backdrop-blur-sm border border-void-600/30">
          <button
            onClick={() => setMode('drop')}
            className={cn(
              'px-4 py-2 rounded-lg text-sm font-medium transition-all duration-300',
              mode === 'drop'
                ? 'bg-nebula-purple text-white shadow-neon-purple'
                : 'text-star-white/60 hover:text-star-white'
            )}
          >
            <Upload className="w-4 h-4 inline mr-2" />
            Upload File
          </button>
          <button
            onClick={() => setMode('url')}
            className={cn(
              'px-4 py-2 rounded-lg text-sm font-medium transition-all duration-300',
              mode === 'url'
                ? 'bg-nebula-purple text-white shadow-neon-purple'
                : 'text-star-white/60 hover:text-star-white'
            )}
          >
            <Link className="w-4 h-4 inline mr-2" />
            Paste URL
          </button>
        </div>
      </div>
      
      <AnimatePresence mode="wait">
        {mode === 'drop' ? (
          <motion.div
            key="drop"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            <div
              {...getRootProps()}
              className={cn(
                'relative group cursor-pointer',
                'p-12 rounded-2xl border-2 border-dashed',
                'transition-all duration-300',
                isDragActive
                  ? 'border-nebula-purple bg-nebula-purple/10 shadow-neon-purple'
                  : 'border-void-600 hover:border-nebula-purple/50 hover:bg-void-800/30',
                isUploading && 'pointer-events-none opacity-70'
              )}
            >
              <input {...getInputProps()} />
              
              {/* Animated background effect */}
              <div className="absolute inset-0 rounded-2xl overflow-hidden">
                <div className={cn(
                  'absolute inset-0 bg-gradient-to-r from-nebula-purple/5 via-nebula-pink/5 to-star-cyan/5',
                  'opacity-0 group-hover:opacity-100 transition-opacity duration-500'
                )} />
              </div>
              
              <div className="relative flex flex-col items-center text-center">
                {isUploading ? (
                  <Loader2 className="w-16 h-16 text-nebula-purple animate-spin mb-4" />
                ) : (
                  <div className="relative mb-4">
                    <div className="absolute inset-0 bg-nebula-purple/20 rounded-full blur-xl animate-pulse" />
                    <div className="relative w-16 h-16 rounded-full bg-void-700 flex items-center justify-center">
                      <Upload className="w-8 h-8 text-nebula-violet" />
                    </div>
                  </div>
                )}
                
                <h3 className="text-xl font-semibold text-star-white mb-2">
                  {isUploading
                    ? 'Uploading...'
                    : isDragActive
                    ? 'Drop it here!'
                    : 'Drop your media here'}
                </h3>
                
                <p className="text-star-white/60 mb-4">
                  or click to browse files
                </p>
                
                <div className="flex gap-4 text-sm text-star-white/40">
                  <span className="flex items-center gap-1">
                    <Film className="w-4 h-4" /> Video
                  </span>
                  <span className="flex items-center gap-1">
                    <Mic className="w-4 h-4" /> Audio
                  </span>
                </div>
              </div>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="url"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
            className="glass-card p-8"
          >
            <div className="mb-6">
              <label className="block text-star-white/80 text-sm font-medium mb-2">
                Paste URL from YouTube, X Spaces, or any video/audio link
              </label>
              <div className="relative">
                <input
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://x.com/i/spaces/... or https://youtube.com/..."
                  className="input-cosmic pr-10"
                  disabled={isUploading}
                />
                {url && (
                  <button
                    onClick={() => setUrl('')}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-star-white/40 hover:text-star-white"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
            
            {/* Platform hints */}
            <div className="flex flex-wrap gap-2 mb-6">
              {[
                { name: 'X Spaces', color: 'bg-void-700' },
                { name: 'YouTube', color: 'bg-red-900/30' },
                { name: 'Podcast RSS', color: 'bg-orange-900/30' },
              ].map((platform) => (
                <span
                  key={platform.name}
                  className={cn(
                    'px-3 py-1 rounded-full text-xs',
                    platform.color,
                    'text-star-white/60'
                  )}
                >
                  {platform.name}
                </span>
              ))}
            </div>
            
            <Button
              onClick={handleUrlSubmit}
              isLoading={isUploading}
              disabled={!url.trim()}
              className="w-full"
            >
              {isUploading ? 'Downloading...' : 'Import Media'}
            </Button>
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* Error message */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="mt-4 p-4 rounded-xl bg-red-900/20 border border-red-500/30 text-red-400 text-sm"
          >
            {error}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}







