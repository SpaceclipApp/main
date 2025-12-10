import type { Metadata } from 'next'
import './globals.css'
import { Providers } from './providers'

export const metadata: Metadata = {
  title: 'SpaceClip - Transform Media into Viral Clips',
  description: 'AI-powered tool to extract highlights from podcasts, videos, and X Spaces. Create platform-optimized clips with transcription and audiograms.',
  keywords: ['podcast clips', 'twitter spaces', 'audiogram', 'video clips', 'AI transcription'],
  icons: {
    icon: '/favicon.svg',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-void-950 antialiased">
        <Providers>
          <div className="nebula-bg min-h-screen">
            <div className="stars fixed inset-0 pointer-events-none" />
            {children}
          </div>
        </Providers>
      </body>
    </html>
  )
}

