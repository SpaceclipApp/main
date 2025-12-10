'use client'

import { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Camera, Upload, Loader2, X, Image as ImageIcon, Wallet } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/store/auth'

interface AvatarUploadProps {
  currentAvatar?: string | null
  onAvatarChange: (url: string) => void
}

export function AvatarUpload({ currentAvatar, onAvatarChange }: AvatarUploadProps) {
  const [isUploading, setIsUploading] = useState(false)
  const [showOptions, setShowOptions] = useState(false)
  const [showNFTModal, setShowNFTModal] = useState(false)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { user } = useAuthStore()
  
  const isWalletUser = user?.wallet_address
  
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    
    // Validate file type
    if (!file.type.startsWith('image/')) {
      alert('Please select an image file')
      return
    }
    
    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      alert('Image must be smaller than 5MB')
      return
    }
    
    setIsUploading(true)
    
    try {
      // Create preview
      const reader = new FileReader()
      reader.onload = (e) => {
        setPreviewUrl(e.target?.result as string)
      }
      reader.readAsDataURL(file)
      
      // Upload to backend
      const formData = new FormData()
      formData.append('file', file)
      
      // Get auth token
      const token = localStorage.getItem('spaceclip_token')
      
      const response = await fetch('http://localhost:8000/api/auth/avatar', {
        method: 'POST',
        body: formData,
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      })
      
      if (!response.ok) throw new Error('Upload failed')
      
      const data = await response.json()
      onAvatarChange(data.avatar_url)
      setShowOptions(false)
    } catch (error) {
      console.error('Avatar upload failed:', error)
      alert('Failed to upload avatar. Please try again.')
      setPreviewUrl(null)
    } finally {
      setIsUploading(false)
    }
  }
  
  const handleRemoveAvatar = () => {
    onAvatarChange('')
    setPreviewUrl(null)
    setShowOptions(false)
  }
  
  const displayAvatar = previewUrl || currentAvatar
  
  return (
    <div className="relative">
      {/* Avatar display */}
      <div 
        className="relative w-24 h-24 rounded-full cursor-pointer group"
        onClick={() => setShowOptions(!showOptions)}
      >
        {displayAvatar ? (
          <img 
            src={displayAvatar} 
            alt="Avatar" 
            className="w-full h-full rounded-full object-cover border-2 border-void-600"
          />
        ) : (
          <div className="w-full h-full rounded-full bg-nebula-purple/20 flex items-center justify-center border-2 border-void-600">
            <span className="text-3xl text-nebula-violet font-bold">
              {user?.name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || '?'}
            </span>
          </div>
        )}
        
        {/* Hover overlay */}
        <div className="absolute inset-0 rounded-full bg-black/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
          <Camera className="w-6 h-6 text-white" />
        </div>
        
        {/* Upload indicator */}
        {isUploading && (
          <div className="absolute inset-0 rounded-full bg-black/70 flex items-center justify-center">
            <Loader2 className="w-6 h-6 text-white animate-spin" />
          </div>
        )}
      </div>
      
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileSelect}
        className="hidden"
      />
      
      {/* Options dropdown */}
      <AnimatePresence>
        {showOptions && (
          <>
            <div 
              className="fixed inset-0 z-10" 
              onClick={() => setShowOptions(false)} 
            />
            <motion.div
              initial={{ opacity: 0, y: 10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.95 }}
              className="absolute top-full left-0 mt-2 w-56 py-2 rounded-xl bg-void-800 border border-void-600 shadow-xl z-20"
            >
              <button
                onClick={() => {
                  fileInputRef.current?.click()
                  setShowOptions(false)
                }}
                className="flex items-center gap-3 px-4 py-2 text-sm text-star-white/80 hover:bg-void-700 w-full text-left"
              >
                <Upload className="w-4 h-4" />
                Upload Image
              </button>
              
              {isWalletUser && (
                <button
                  onClick={() => {
                    setShowNFTModal(true)
                    setShowOptions(false)
                  }}
                  className="flex items-center gap-3 px-4 py-2 text-sm text-star-white/80 hover:bg-void-700 w-full text-left"
                >
                  <ImageIcon className="w-4 h-4" />
                  Choose from NFTs
                </button>
              )}
              
              {displayAvatar && (
                <>
                  <div className="border-t border-void-600 my-1" />
                  <button
                    onClick={handleRemoveAvatar}
                    className="flex items-center gap-3 px-4 py-2 text-sm text-red-400 hover:bg-void-700 w-full text-left"
                  >
                    <X className="w-4 h-4" />
                    Remove Avatar
                  </button>
                </>
              )}
            </motion.div>
          </>
        )}
      </AnimatePresence>
      
      {/* NFT Selection Modal */}
      <NFTAvatarModal 
        isOpen={showNFTModal} 
        onClose={() => setShowNFTModal(false)}
        onSelect={(url) => {
          onAvatarChange(url)
          setShowNFTModal(false)
        }}
        walletAddress={user?.wallet_address}
      />
    </div>
  )
}

// NFT Avatar Selection Modal
interface NFTAvatarModalProps {
  isOpen: boolean
  onClose: () => void
  onSelect: (url: string) => void
  walletAddress?: string | null
}

function NFTAvatarModal({ isOpen, onClose, onSelect, walletAddress }: NFTAvatarModalProps) {
  const [nfts, setNfts] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedNft, setSelectedNft] = useState<string | null>(null)
  
  // Fetch NFTs when modal opens
  const fetchNFTs = async () => {
    if (!walletAddress) return
    
    setIsLoading(true)
    setError(null)
    
    try {
      // Try to fetch from our backend which will proxy to an NFT API
      const response = await fetch(`http://localhost:8000/api/auth/nfts/${walletAddress}`)
      
      if (!response.ok) {
        // Fallback: Show demo NFTs or empty state
        throw new Error('Could not fetch NFTs')
      }
      
      const data = await response.json()
      setNfts(data.nfts || [])
    } catch (err) {
      // For demo purposes, show some placeholder NFTs
      setNfts([
        { id: '1', name: 'Cool Cat #1234', image: 'https://placekitten.com/200/200' },
        { id: '2', name: 'Bored Ape #5678', image: 'https://placekitten.com/201/201' },
        { id: '3', name: 'Doodle #9012', image: 'https://placekitten.com/202/202' },
      ])
      setError('Using demo NFTs. Connect to mainnet for real NFTs.')
    } finally {
      setIsLoading(false)
    }
  }
  
  // Fetch when modal opens
  if (isOpen && nfts.length === 0 && !isLoading && !error) {
    fetchNFTs()
  }
  
  if (!isOpen) return null
  
  return (
    <>
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
      />
      
      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="w-full max-w-lg"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="glass-card p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-nebula-purple/20 flex items-center justify-center">
                  <Wallet className="w-5 h-5 text-nebula-violet" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-star-white">Choose NFT Avatar</h2>
                  <p className="text-star-white/60 text-sm">Select an NFT from your collection</p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-lg text-star-white/60 hover:text-star-white hover:bg-void-700 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            {/* Content */}
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 text-nebula-violet animate-spin" />
              </div>
            ) : nfts.length === 0 ? (
              <div className="text-center py-12">
                <ImageIcon className="w-12 h-12 text-star-white/20 mx-auto mb-3" />
                <p className="text-star-white/60">No NFTs found in your wallet</p>
                <p className="text-star-white/40 text-sm mt-1">
                  Connect a wallet with NFTs to use this feature
                </p>
              </div>
            ) : (
              <>
                {error && (
                  <p className="text-amber-400 text-sm bg-amber-400/10 px-4 py-2 rounded-lg mb-4">
                    {error}
                  </p>
                )}
                
                <div className="grid grid-cols-3 gap-3 max-h-80 overflow-y-auto">
                  {nfts.map((nft) => (
                    <button
                      key={nft.id}
                      onClick={() => setSelectedNft(nft.image)}
                      className={cn(
                        'relative rounded-xl overflow-hidden border-2 transition-all',
                        selectedNft === nft.image
                          ? 'border-nebula-purple ring-2 ring-nebula-purple/50'
                          : 'border-void-600 hover:border-void-500'
                      )}
                    >
                      <img 
                        src={nft.image} 
                        alt={nft.name}
                        className="w-full aspect-square object-cover"
                      />
                      <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-2">
                        <p className="text-white text-xs truncate">{nft.name}</p>
                      </div>
                    </button>
                  ))}
                </div>
                
                {/* Confirm button */}
                <button
                  onClick={() => selectedNft && onSelect(selectedNft)}
                  disabled={!selectedNft}
                  className="w-full mt-4 py-3 rounded-xl bg-nebula-purple hover:bg-nebula-violet text-white font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Use Selected NFT
                </button>
              </>
            )}
          </div>
        </motion.div>
      </div>
    </>
  )
}

