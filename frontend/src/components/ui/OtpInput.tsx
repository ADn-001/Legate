import { useRef } from 'react'

interface OtpInputProps {
  value: string[]
  onChange: (value: string[]) => void
  length?: number
}

export default function OtpInput({ value, onChange, length = 6 }: OtpInputProps) {
  const refs = useRef<(HTMLInputElement | null)[]>([])

  const handleChange = (index: number, val: string) => {
    if (!/^\d*$/.test(val)) return
    const newOtp = [...value]
    newOtp[index] = val.slice(-1)
    onChange(newOtp)
    if (val && index < length - 1) refs.current[index + 1]?.focus()
  }

  const handleKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !value[index] && index > 0) {
      refs.current[index - 1]?.focus()
    }
  }

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault()
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, length)
    const newOtp = [...value]
    pasted.split('').forEach((char, i) => { newOtp[i] = char })
    onChange(newOtp)
    const nextEmpty = pasted.length < length ? pasted.length : length - 1
    refs.current[nextEmpty]?.focus()
  }

  return (
    <div className="flex justify-center gap-2">
      {Array.from({ length }, (_, i) => (
        <input
          key={i}
          ref={(el) => { refs.current[i] = el }}
          type="text"
          inputMode="numeric"
          maxLength={1}
          value={value[i] || ''}
          onChange={(e) => handleChange(i, e.target.value)}
          onKeyDown={(e) => handleKeyDown(i, e)}
          onPaste={handlePaste}
          className="w-12 h-12 text-center text-2xl font-bold border-2 border-gray-200 rounded-lg focus:outline-none focus:border-[#3D4F6B] focus:ring-2 focus:ring-[#3D4F6B]/20"
        />
      ))}
    </div>
  )
}
