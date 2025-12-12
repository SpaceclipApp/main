import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { 
  MediaInfo, 
  TranscriptionResult, 
  HighlightAnalysis, 
  ClipResult,
  Highlight,
  Platform,
  ProjectSummary,
  getProject
} from '@/lib/api'

export type AppStep = 'upload' | 'processing' | 'highlights' | 'export'

interface ClipSelection {
  highlightId: string | null
  customStart: number | null
  customEnd: number | null
}

interface ProjectStore {
  // Current step
  step: AppStep
  setStep: (step: AppStep) => void
  
  // Current project ID (for persistence)
  currentProjectId: string | null
  setCurrentProjectId: (id: string | null) => void
  
  // Media state
  media: MediaInfo | null
  setMedia: (media: MediaInfo | null) => void
  
  // Processing state
  isProcessing: boolean
  processingStatus: string
  progress: number
  setProcessing: (status: string, progress: number) => void
  setIsProcessing: (isProcessing: boolean) => void
  
  // Transcription
  transcription: TranscriptionResult | null
  setTranscription: (transcription: TranscriptionResult | null) => void
  
  // Highlights
  highlights: HighlightAnalysis | null
  setHighlights: (highlights: HighlightAnalysis | null) => void
  
  // Clip selection
  selectedHighlight: Highlight | null
  selectHighlight: (highlight: Highlight | null) => void
  clipRange: { start: number; end: number } | null
  setClipRange: (start: number, end: number) => void
  
  // Generated clips
  clips: ClipResult[]
  addClip: (clip: ClipResult) => void
  addClips: (clips: ClipResult[]) => void
  
  // Export options
  selectedPlatforms: Platform[]
  togglePlatform: (platform: Platform) => void
  includeCaption: boolean
  setIncludeCaption: (include: boolean) => void
  audiogramStyle: string
  setAudiogramStyle: (style: string) => void
  
  // Project history
  recentProjects: string[]  // List of recent media IDs
  addToRecent: (mediaId: string) => void
  
  // Load project from backend
  loadProject: (mediaId: string) => Promise<void>
  
  // Reset
  reset: () => void
  // Clear all (including recent projects) - used for logout
  clearAll: () => void
}

const initialState = {
  step: 'upload' as AppStep,
  currentProjectId: null as string | null,
  media: null,
  isProcessing: false,
  processingStatus: '',
  progress: 0,
  transcription: null,
  highlights: null,
  selectedHighlight: null,
  clipRange: null,
  clips: [],
  selectedPlatforms: ['instagram_reels', 'tiktok'] as Platform[],
  includeCaption: true,
  audiogramStyle: 'cosmic',
  recentProjects: [] as string[],
}

export const useProjectStore = create<ProjectStore>()(
  persist(
    (set, get) => ({
      ...initialState,
      
      setStep: (step) => set({ step }),
      
      setCurrentProjectId: (id) => set({ currentProjectId: id }),
      
      setMedia: (media) => {
        set({ media, currentProjectId: media?.id || null })
        if (media?.id) {
          get().addToRecent(media.id)
        }
      },
      
      setProcessing: (processingStatus, progress) => 
        set({ processingStatus, progress }),
      
      setIsProcessing: (isProcessing) => set({ isProcessing }),
      
      setTranscription: (transcription) => set({ transcription }),
      
      setHighlights: (highlights) => set({ highlights }),
      
      selectHighlight: (highlight) => set({ 
        selectedHighlight: highlight,
        clipRange: highlight ? { start: highlight.start, end: highlight.end } : null
      }),
      
      setClipRange: (start, end) => set({ clipRange: { start, end } }),
      
      addClip: (clip) => set((state) => ({ clips: [...state.clips, clip] })),
      
      addClips: (clips) => set((state) => ({ clips: [...state.clips, ...clips] })),
      
      togglePlatform: (platform) => set((state) => ({
        selectedPlatforms: state.selectedPlatforms.includes(platform)
          ? state.selectedPlatforms.filter((p) => p !== platform)
          : [...state.selectedPlatforms, platform]
      })),
      
      setIncludeCaption: (includeCaption) => set({ includeCaption }),
      
      setAudiogramStyle: (audiogramStyle) => set({ audiogramStyle }),
      
      addToRecent: (mediaId) => set((state) => {
        const filtered = state.recentProjects.filter(id => id !== mediaId)
        return { recentProjects: [mediaId, ...filtered].slice(0, 10) }
      }),
      
      loadProject: async (mediaId: string) => {
        try {
          const project = await getProject(mediaId)
          
          set({
            currentProjectId: mediaId,
            media: project.media,
            transcription: project.transcription,
            highlights: project.highlights,
            clips: project.clips,
            step: project.highlights ? 'highlights' : 
                  project.transcription ? 'processing' : 'upload',
            progress: project.progress,
          })
          
          get().addToRecent(mediaId)
        } catch (error) {
          console.error('Failed to load project:', error)
        }
      },
      
      reset: () => set({
        ...initialState,
        // Preserve recent projects across resets
        recentProjects: get().recentProjects,
      }),
      
      clearAll: () => set({
        ...initialState,
        // Clear everything including recent projects
        recentProjects: [],
      }),
    }),
    {
      name: 'spaceclip-storage',
      partialize: (state) => ({
        // Only persist these fields
        currentProjectId: state.currentProjectId,
        recentProjects: state.recentProjects,
        selectedPlatforms: state.selectedPlatforms,
        includeCaption: state.includeCaption,
        audiogramStyle: state.audiogramStyle,
      }),
    }
  )
)

