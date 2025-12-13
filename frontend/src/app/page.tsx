'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useEffect, useRef } from 'react'
import { Rocket, Sparkles, Wand2, Download } from 'lucide-react'
import { useProjectStore } from '@/store/project'
import { Header } from '@/components/layout/Header'
import { DropZone } from '@/components/upload/DropZone'
import { ProjectHistory } from '@/components/projects/ProjectHistory'
import { ProcessingView } from '@/components/processing/ProcessingView'
import { ProcessingQueue } from '@/components/processing/ProcessingQueue'
import { HighlightsView } from '@/components/highlights/HighlightsView'
import { ExportView } from '@/components/export/ExportView'

const features = [
  {
    icon: Rocket,
    title: 'Upload Anything',
    description: 'Videos, audio, X Spaces, YouTube—we handle it all'
  },
  {
    icon: Sparkles,
    title: 'AI Highlights',
    description: 'Smart detection finds your best moments automatically'
  },
  {
    icon: Wand2,
    title: 'Auto Captions',
    description: 'Beautiful transcriptions with waveform audiograms'
  },
  {
    icon: Download,
    title: 'Export Everywhere',
    description: 'One click to TikTok, Reels, Shorts, and more'
  },
]

export default function Home() {
  const { step } = useProjectStore()
  const highlightsRef = useRef<HTMLDivElement>(null)
  const exportRef = useRef<HTMLDivElement>(null)
  
  // Reset scroll position when step changes
  useEffect(() => {
    if (step === 'highlights' && highlightsRef.current) {
      highlightsRef.current.scrollTop = 0
    } else if (step === 'export' && exportRef.current) {
      exportRef.current.scrollTop = 0
    }
  }, [step])
  
  return (
    <div className="relative min-h-screen flex flex-col">
      <Header />
      
      <main className="flex-1 flex flex-col">
        <AnimatePresence mode="wait">
          {step === 'upload' && (
            <motion.div
              key="upload"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0, x: -50 }}
              transition={{ duration: 0.3 }}
              className="flex-1 flex flex-col"
            >
              {/* Hero section */}
              <section className="relative py-20 px-4 text-center">
                {/* Glow effect */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-nebula-purple/10 rounded-full blur-[120px] pointer-events-none" />
                
                <motion.div
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6 }}
                  className="relative max-w-4xl mx-auto"
                >
                  <motion.div
                    initial={{ scale: 0.8 }}
                    animate={{ scale: 1 }}
                    transition={{ duration: 0.5, delay: 0.1 }}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-nebula-purple/10 border border-nebula-purple/30 text-sm text-nebula-violet mb-6"
                  >
                    <Sparkles className="w-4 h-4" />
                    <span>AI-Powered • Privacy-First • Local Processing</span>
                  </motion.div>
                  
                  <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold mb-6">
                    <span className="text-star-white">Transform Media into</span>
                    <br />
                    <span className="text-gradient">Viral Clips</span>
                  </h1>
                  
                  <p className="text-xl text-star-white/60 max-w-2xl mx-auto mb-12">
                    Turn your podcasts, videos, and X Spaces into scroll-stopping content. 
                    AI finds highlights, generates captions, and optimizes for every platform.
                  </p>
                  
                  <DropZone />
                </motion.div>
              </section>
              
              {/* Features grid */}
              <section className="py-20 px-4">
                <div className="max-w-5xl mx-auto">
                  <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
                    {features.map((feature, i) => (
                      <motion.div
                        key={feature.title}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.4 + i * 0.1 }}
                        className="glass-card p-6 text-center group hover:border-nebula-purple/50 transition-all duration-300"
                      >
                        <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-nebula-purple/10 flex items-center justify-center group-hover:bg-nebula-purple/20 transition-colors">
                          <feature.icon className="w-6 h-6 text-nebula-violet" />
                        </div>
                        <h3 className="font-semibold text-star-white mb-2">
                          {feature.title}
                        </h3>
                        <p className="text-sm text-star-white/60">
                          {feature.description}
                        </p>
                      </motion.div>
                    ))}
                  </div>
                </div>
              </section>
            </motion.div>
          )}
          
          {step === 'processing' && (
            <motion.div
              key="processing"
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -50 }}
              transition={{ duration: 0.3 }}
              className="flex-1 flex items-center justify-center px-4 py-12"
            >
              <ProcessingView />
            </motion.div>
          )}
          
          {step === 'highlights' && (
            <motion.div
              key="highlights"
              ref={highlightsRef}
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -50 }}
              transition={{ duration: 0.3 }}
              className="flex-1 px-4 py-8 overflow-y-auto"
            >
              <HighlightsView />
            </motion.div>
          )}
          
          {step === 'export' && (
            <motion.div
              key="export"
              ref={exportRef}
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -50 }}
              transition={{ duration: 0.3 }}
              className="flex-1 px-4 py-8 overflow-y-auto"
            >
              <ExportView />
            </motion.div>
          )}
        </AnimatePresence>
        
        {/* Recent Projects Section - Shown when on upload step */}
        {step === 'upload' && (
          <section className="py-8 px-4">
            <ProjectHistory />
          </section>
        )}
      </main>
      
      {/* Footer */}
      <footer className="border-t border-void-700/50 py-6 px-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between text-sm text-star-white/40">
          <span>SpaceClip • Local-first AI clipping</span>
          <span>Powered by Whisper + Ollama</span>
        </div>
      </footer>
      
      {/* Persistent Processing Queue */}
      <ProcessingQueue />
    </div>
  )
}

