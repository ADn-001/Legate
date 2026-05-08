/**
 * Toggle / Switch Component
 * - On/off toggle for boolean settings
 */

interface ToggleProps {
  checked: boolean
  onChange: (checked: boolean) => void
  label?: string
}

export default function Toggle({ checked, onChange, label }: ToggleProps) {
  // TODO: Implement Toggle component
  // - Animated switch
  // - Label text (optional, left-aligned)
  // - Accessible (use input[type="checkbox"])
  return (
    <label>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      {label && <span>{label}</span>}
    </label>
  )
}
