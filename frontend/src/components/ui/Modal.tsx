/**
 * Modal Component
 * - Overlay + centered modal dialog
 * - Close button
 * - Title, content, footer
 */

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  children: React.ReactNode
  footer?: React.ReactNode
}

export default function Modal({ isOpen, onClose, title, children, footer }: ModalProps) {
  // TODO: Implement Modal component
  // - Overlay: dark semi-transparent background
  // - Centered modal with white background, rounded-xl
  // - Close button (X) top right
  // - Title heading (optional)
  // - Content area (children)
  // - Footer actions (optional)
  // - Trap focus within modal
  if (!isOpen) return null
  return (
    <div>
      <div>
        {title && <h2>{title}</h2>}
        {children}
        {footer && <div>{footer}</div>}
      </div>
    </div>
  )
}
