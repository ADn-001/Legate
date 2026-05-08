/**
 * Card Component
 * - White background, rounded-xl, subtle shadow
 * - Flexible content
 */

interface CardProps {
  children: React.ReactNode
  className?: string
}

export default function Card({ children, className = '' }: CardProps) {
  // TODO: Implement Card component
  // - Background: #FFFFFF
  // - Border-radius: rounded-xl
  // - Shadow: subtle drop shadow
  // - Padding: p-6 or similar
  return <div className={`bg-white rounded-xl shadow ${className}`}>{children}</div>
}
