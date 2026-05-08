/**
 * Button Component
 * - Primary, secondary, danger variants
 * - Full-width option
 * - Loading state
 */

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger'
  fullWidth?: boolean
  loading?: boolean
  children: React.ReactNode
}

export default function Button({
  variant = 'primary',
  fullWidth = false,
  loading = false,
  disabled,
  children,
  ...props
}: ButtonProps) {
  // TODO: Implement Button component
  // - Variants: primary (#3D4F6B), secondary (gray-100), danger (#C0392B)
  // - Full-width option
  // - Loading state with spinner
  // - Disabled state
  return (
    <button disabled={disabled || loading} {...props}>
      {loading ? 'Loading...' : children}
    </button>
  )
}
