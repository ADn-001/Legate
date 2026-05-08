/**
 * Badge Component
 * - Status badge (draft, active, delivered)
 * - Variants: default, success, warning, error
 */

interface BadgeProps {
  children: React.ReactNode
  variant?: 'default' | 'success' | 'warning' | 'error'
}

export default function Badge({ children, variant = 'default' }: BadgeProps) {
  // TODO: Implement Badge component
  // - Variants:
  //   - default: gray
  //   - success: green (#22C55E)
  //   - warning: amber
  //   - error: red (#C0392B)
  return <span>{children}</span>
}
