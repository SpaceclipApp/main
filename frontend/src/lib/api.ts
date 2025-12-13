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

// Add response interceptor for 401 handling with refresh
let isRefreshing = false
let failedQueue: Array<{
  resolve: (value?: any) => void
  reject: (reason?: any) => void
}> = []

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token)
    }
  })
  failedQueue = []
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // If error is 401 and we haven't tried refreshing yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // If already refreshing, queue this request
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then(token => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return api(originalRequest)
        }).catch(err => {
          return Promise.reject(err)
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        // Get current token
        const authData = localStorage.getItem('spaceclip-auth')
        if (!authData) {
          throw new Error('No auth data')
        }

        const { state } = JSON.parse(authData)
        if (!state?.token) {
          throw new Error('No token')
        }

        // Attempt refresh
        const refreshResponse = await api.post('/auth/refresh', {}, {
          headers: {
            Authorization: `Bearer ${state.token}`
          }
        })

        const { user, token: newToken } = refreshResponse.data

        // Update auth store
        if (typeof window !== 'undefined') {
          const authStore = await import('../store/auth')
          authStore.useAuthStore.getState().login(user, newToken)
        }

        // Update token in original request
        originalRequest.headers.Authorization = `Bearer ${newToken}`

        // Process queued requests
        processQueue(null, newToken)

        // Retry original request
        return api(originalRequest)
      } catch (refreshError) {
        // Refresh failed, process queue with error
        processQueue(refreshError, null)

        // Logout user
        if (typeof window !== 'undefined') {
          const authStore = await import('../store/auth')
          authStore.useAuthStore.getState().logout()
        }

        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

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
  // Absolute timestamps in source media (Task 2.5.2: Fix clip time semantics)
  // Optional for backwards compatibility with existing clips
  start: number | null  // Seconds from media start (absolute)
  end: number | null    // Seconds from media start (absolute)
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
  status_message: string | null
  error: string | null
  transcription: TranscriptionResult | null
  highlights: HighlightAnalysis | null
  clips: ClipResult[]
}

export interface ProjectStatusResponse {
  media_id: string
  status: 'pending' | 'downloading' | 'transcribing' | 'analyzing' | 'complete' | 'error'
  progress: number
  status_message: string | null
  error: string | null
  has_transcription: boolean
  has_highlights: boolean
  clip_count: number
  updated_at: string
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

/**
 * Get lightweight project status for polling during processing.
 * Optimized for frequent calls (every 2s) with minimal data transfer.
 */
export async function getProjectStatus(mediaId: string): Promise<ProjectStatusResponse> {
  const response = await api.get(`/projects/${mediaId}/status`)
  return response.data
}

export interface ClipCaption {
  id: number
  start: number
  end: number
  original_start?: number
  original_end?: number
  text: string
  speaker: string | null
  confidence?: number
}

export interface ClipCaptionsResponse {
  media_id: string
  clip_start: number
  clip_end: number
  clip_duration: number
  segments: ClipCaption[]
  segment_count: number
}

/**
 * Get captions/transcript segments for a specific time range.
 * Used for regenerating captions after clip boundary adjustment.
 */
export async function getClipCaptions(
  mediaId: string,
  start: number,
  end: number
): Promise<ClipCaptionsResponse> {
  const response = await api.get(`/projects/${mediaId}/captions`, {
    params: { start, end }
  })
  return response.data
}

export interface ClipRangeResponse {
  media_id: string
  start: number
  end: number
  duration: number
  highlight: {
    id: string
    title: string
    original_start: number
    original_end: number
  } | null
  captions: ClipCaption[]
  caption_count: number
}

/**
 * Update/save the current clip range selection.
 * Returns updated captions for the new range.
 */
export async function updateClipRange(
  mediaId: string,
  start: number,
  end: number,
  highlightId?: string
): Promise<ClipRangeResponse> {
  const params: Record<string, any> = { start, end }
  if (highlightId) {
    params.highlight_id = highlightId
  }
  const response = await api.post(`/projects/${mediaId}/clip-range`, null, { params })
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

export async function listProjects(includeArchived: boolean = false): Promise<ProjectSummary[]> {
  const response = await api.get('/projects', {
    params: { include_archived: includeArchived }
  })
  return response.data
}

export async function deleteProject(mediaId: string): Promise<void> {
  // Use the media-level delete endpoint (routes.py)
  await api.delete(`/projects/${mediaId}`)
}

export async function archiveProject(mediaId: string): Promise<void> {
  // Archive endpoint - use media-level route
  await api.post(`/projects/${mediaId}/archive`)
}

export async function unarchiveProject(mediaId: string): Promise<void> {
  // Unarchive endpoint - use media-level route
  await api.post(`/projects/${mediaId}/unarchive`)
}

export async function clearProjectClips(mediaId: string): Promise<void> {
  // Clear clips for a media item
  await api.post(`/projects/${mediaId}/clear-clips`)
}

// Bulk actions
export async function deleteProjects(mediaIds: string[]): Promise<void> {
  await Promise.all(mediaIds.map(id => deleteProject(id)))
}

export async function archiveProjects(mediaIds: string[]): Promise<void> {
  await Promise.all(mediaIds.map(id => archiveProject(id)))
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

