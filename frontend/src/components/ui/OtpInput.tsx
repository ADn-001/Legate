/**
 * OTP Input Component
 * - 6-box input for OTP
 * - Auto-advance to next box on digit entry
 * - Paste support
 */

interface OtpInputProps {
  value: string
  onChange: (value: string) => void
  length?: number
}

export default function OtpInput({ value, onChange, length = 6 }: OtpInputProps) {
  // TODO: Implement OtpInput component
  // - Display 6 input boxes (or custom length)
  // - Auto-advance to next box on digit entry
  // - Support backspace to move to previous
  // - Support paste (split string into boxes)
  // - Only accept numeric input
  return <div>OTP Input</div>
}
