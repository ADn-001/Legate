/**
 * Input Component
 * - Text input with label
 * - Error state
 * - Help text
 */

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  helpText?: string
}

export default function Input({ label, error, helpText, ...props }: InputProps) {
  // TODO: Implement Input component
  // - Label + input field
  // - Border: border-gray-200, rounded-xl
  // - Focus: ring focus state
  // - Error state: red border + error message
  // - Help text below input
  return (
    <div>
      {label && <label>{label}</label>}
      <input {...props} />
      {error && <span>{error}</span>}
      {helpText && <span>{helpText}</span>}
    </div>
  )
}
