interface ToggleProps {
  checked: boolean
  onChange: (checked: boolean) => void
  label?: string
  disabled?: boolean
}

export default function Toggle({ checked, onChange, label, disabled }: ToggleProps) {
  return (
    <label className="flex items-center gap-3 cursor-pointer">
      <div className="relative">
        <input
          type="checkbox"
          className="sr-only"
          checked={checked}
          disabled={disabled}
          onChange={(e) => onChange(e.target.checked)}
        />
        <div
          className={`h-8 w-14 rounded-full transition-colors ${checked ? 'bg-[#3D4F6B]' : 'bg-gray-300'} ${disabled ? 'opacity-50' : ''}`}
        />
        <div
          className={`absolute top-1 h-6 w-6 rounded-full bg-white shadow transition-transform ${checked ? 'translate-x-7' : 'translate-x-1'}`}
        />
      </div>
      {label && <span className="text-sm font-medium text-[#0D1117]">{label}</span>}
    </label>
  )
}
