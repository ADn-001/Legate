/**
 * Bottom Sheet Component
 * - Modal-like component that slides up from bottom
 * - Used for mobile-friendly forms/options
 */

interface BottomSheetProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  children: React.ReactNode
}

export default function BottomSheet({ isOpen, onClose, title, children }: BottomSheetProps) {
  // TODO: Implement BottomSheet component
  // - Slides up from bottom
  // - Semi-transparent overlay
  // - Handle/drag indicator at top
  // - Title (optional)
  // - Content area
  // - Close on overlay click
  if (!isOpen) return null
  return (
    <div>
      <div>
        {title && <h2>{title}</h2>}
        {children}
      </div>
    </div>
  )
}
