/**
 * Security Banner Component
 * - Informational banner with shield icon
 * - Used for security notices (e.g., "They will only receive instructions...")
 */

interface SecurityBannerProps {
  children: React.ReactNode
  variant?: 'info' | 'warning'
}

export default function SecurityBanner({ children, variant = 'info' }: SecurityBannerProps) {
  // TODO: Implement SecurityBanner component
  // - Shield icon left
  // - Soft blue background (#E5F4FF or similar)
  // - Small text size
  // - Subtle border
  // - Padding around content
  return <div>{children}</div>
}
