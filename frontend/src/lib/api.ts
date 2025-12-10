import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: `${API_BASE}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 1800000, // 30 minutes for long videos/podcasts
})

// Add auth token interceptor
api.interceptors.request.use((config) => {
  // Try to get token from localStorage (auth store persists there)
  if (typeof window !== 'undefined') {
    const authData = localStorage.getItem('spaceclip-auth')
    if (authData) {
      try {
        const { state } = JSON.parse(authData)
        if (state?.token) {
          config.headers.Authorization = `Bearer ${state.token}`
        }
      } catch (e) {
        // Ignore parse errors
      }
    }
  }
  return config
})

// Types
export interface MediaInfo {
  id: string
  filename: string
  original_filename: string | null
  media_type: 'video' | 'audio'
  source_type: 'upload' | 'youtube' | 'x_space' | 'url'
  source_url: string | null  // Original URL for YouTube/X Spaces
  duration: number
  file_path: string
  thumbnail_path: string | null
  created_at: string
}

export interface TranscriptSegment {
  id: number
  start: number
  end: number
  text: string
  speaker: string | null
  confidence: number
}

export interface TranscriptionResult {
  media_id: string
  language: string
  segments: TranscriptSegment[]
  full_text: string
}

export interface Highlight {
  id: string
  start: number
  end: number
  title: string
  description: string
  score: number
  tags: string[]
  transcript_segment_ids: number[]
}

export interface HighlightAnalysis {
  media_id: string
  highlights: Highlight[]
  analyzed_at: string
}

export interface ClipResult {
  id: string
  media_id: string
  platform: string
  file_path: string
  duration: number
  width: number
  height: number
  has_captions: boolean
  created_at: string
}

export interface ProjectState {
  media: MediaInfo | null
  status: 'pending' | 'downloading' | 'transcribing' | 'analyzing' | 'complete' | 'error'
  progress: number
  error: string | null
  transcription: TranscriptionResult | null
  highlights: HighlightAnalysis | null
  clips: ClipResult[]
}

export type Platform = 
  | 'instagram_feed'
  | 'instagram_reels'
  | 'tiktok'
  | 'youtube'
  | 'youtube_shorts'
  | 'linkedin'
  | 'twitter'

// API functions
export async function uploadFile(file: File): Promise<MediaInfo> {
  const formData = new FormData()
  formData.append('file', file)
  
  const response = await api.post('/upload/file', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

export async function uploadFromUrl(url: string): Promise<MediaInfo> {
  const response = await api.post('/upload/url', { 
    url,
    source_type: 'url'
  })
  return response.data
}


export async function analyzeHighlights(
  mediaId: string,
  options?: {
    max_highlights?: number
    min_duration?: number
    max_duration?: number
    start_time?: number
    end_time?: number
    append?: boolean
  }
): Promise<HighlightAnalysis> {
  const params = new URLSearchParams()
  if (options?.max_highlights) params.set('max_highlights', String(options.max_highlights))
  if (options?.min_duration) params.set('min_duration', String(options.min_duration))
  if (options?.max_duration) params.set('max_duration', String(options.max_duration))
  if (options?.start_time !== undefined) params.set('start_time', String(options.start_time))
  if (options?.end_time !== undefined) params.set('end_time', String(options.end_time))
  if (options?.append) params.set('append', 'true')
  
  const queryString = params.toString() ? `?${params.toString()}` : ''
  const response = await api.post(`/analyze/${mediaId}${queryString}`)
  return response.data
}

export async function transcribeMedia(
  mediaId: string, 
  language?: string,
  numSpeakers?: number
): Promise<TranscriptionResult> {
  const params = new URLSearchParams()
  if (language) params.set('language', language)
  if (numSpeakers) params.set('num_speakers', String(numSpeakers))
  
  const queryString = params.toString() ? `?${params.toString()}` : ''
  const response = await api.post(`/transcribe/${mediaId}${queryString}`)
  return response.data
}

export async function createClips(request: {
  media_id: string
  start: number
  end: number
  title?: string
  platforms: Platform[]
  include_captions?: boolean
  audiogram_style?: string
}): Promise<ClipResult[]> {
  const response = await api.post('/clips', request)
  return response.data
}

export async function getProject(mediaId: string): Promise<ProjectState> {
  const response = await api.get(`/projects/${mediaId}`)
  return response.data
}

export interface ProjectSummary {
  media_id: string
  title: string
  media_type: 'video' | 'audio'
  duration: number
  status: string
  saved_at: string
  clips_count: number
  highlights_count: number
}

export async function listProjects(): Promise<ProjectSummary[]> {
  const response = await api.get('/projects')
  return response.data
}

export async function deleteProject(projectId: string): Promise<void> {
  await api.delete(`/auth/projects/${projectId}`)
}

export async function archiveProject(projectId: string): Promise<void> {
  await api.post(`/auth/projects/${projectId}/archive`)
}

export async function unarchiveProject(projectId: string): Promise<void> {
  await api.post(`/auth/projects/${projectId}/unarchive`)
}

export async function clearProjectClips(projectId: string): Promise<void> {
  await api.post(`/auth/projects/${projectId}/clear-clips`)
}

// Bulk actions
export async function deleteProjects(projectIds: string[]): Promise<void> {
  await Promise.all(projectIds.map(id => deleteProject(id)))
}

export async function archiveProjects(projectIds: string[]): Promise<void> {
  await Promise.all(projectIds.map(id => archiveProject(id)))
}

export async function processMedia(mediaId: string, autoClip: boolean = true): Promise<void> {
  await api.post(`/process/${mediaId}?auto_clip=${autoClip}`)
}

export async function getPlatforms(): Promise<Array<{
  platform: Platform
  width: number
  height: number
  max_duration: number
  aspect_ratio: string
}>> {
  const response = await api.get('/platforms')
  return response.data
}

export async function generateCaption(text: string, platform: string = 'twitter'): Promise<string> {
  const response = await api.post('/caption', null, {
    params: { text, platform }
  })
  return response.data.caption
}

export function getDownloadUrl(clipId: string): string {
  return `${API_BASE}/api/download/${clipId}`
}

export function getThumbnailUrl(mediaId: string): string {
  return `${API_BASE}/api/thumbnail/${mediaId}`
}

export function getOutputUrl(filename: string): string {
  return `${API_BASE}/outputs/${filename}`
}

