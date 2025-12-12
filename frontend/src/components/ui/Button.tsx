'use client'

import { forwardRef } from 'react'
import { cn } from '@/lib/utils'
import { motion, HTMLMotionProps } from 'framer-motion'

interface ButtonProps extends Omit<HTMLMotionProps<'button'>, 'children'> {
  variant?: 'cosmic' | 'outline' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
  children: React.ReactNode
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'cosmic', size = 'md', isLoading, children, disabled, ...props }, ref) => {
    const baseStyles = 'relative inline-flex items-center justify-center font-medium transition-all duration-300 ease-out disabled:opacity-50 disabled:cursor-not-allowed'
    
    const variants = {
      cosmic: 'bg-gradient-to-r from-nebula-purple to-nebula-violet text-white shadow-neon-purple hover:scale-105 hover:shadow-[0_0_30px_rgba(124,58,237,0.6)] active:scale-100 rounded-xl overflow-hidden',
      outline: 'border-2 border-nebula-purple/50 text-nebula-violet bg-transparent backdrop-blur-sm hover:border-nebula-purple hover:bg-nebula-purple/10 hover:shadow-neon-purple rounded-xl',
      ghost: 'text-star-white/70 hover:text-star-white hover:bg-void-700/50 rounded-lg',
    }
    
    const sizes = {
      sm: 'px-3 py-1.5 text-sm gap-1.5',
      md: 'px-5 py-2.5 text-base gap-2',
      lg: 'px-7 py-3.5 text-lg gap-2.5',
    }
    
    return (
      <motion.button
        ref={ref}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        disabled={disabled || isLoading}
        whileTap={{ scale: 0.98 }}
        {...props}
      >
        {isLoading && (
          <svg className="animate-spin h-4 w-4 mr-2" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        )}
        {children}
        {variant === 'cosmic' && (
          <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full animate-shimmer" />
        )}
      </motion.button>
    )
  }
)

Button.displayName = 'Button'







