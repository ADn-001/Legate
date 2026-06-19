import { useState } from 'react'
import Input from '../ui/Input'
import Toggle from '../ui/Toggle'
import Button from '../ui/Button'
import { BeneficiaryCreatePayload } from '../../api/beneficiaries'

interface BeneficiaryFormProps {
  initialData?: Partial<BeneficiaryCreatePayload>
  onSubmit: (data: BeneficiaryCreatePayload) => Promise<void>
  onCancel: () => void
  loading?: boolean
  /** F11/FR-23: name of the beneficiary who currently holds the (single)
   * emergency contact slot, if it's someone other than the one being
   * edited here. Used to warn that enabling the toggle replaces them. */
  otherEmergencyContactName?: string
}

export default function BeneficiaryForm({ initialData, onSubmit, onCancel, loading = false, otherEmergencyContactName }: BeneficiaryFormProps) {
  const [fullName, setFullName] = useState(initialData?.full_name || '')
  const [email, setEmail] = useState(initialData?.email || '')
  const [relationship, setRelationship] = useState(initialData?.relationship || '')
  const [isEmergencyContact, setIsEmergencyContact] = useState(initialData?.is_emergency_contact || false)
  const [errors, setErrors] = useState<Record<string, string>>({})

  const validate = () => {
    const errs: Record<string, string> = {}
    if (!fullName.trim()) errs.fullName = 'Full name is required'
    if (!email.trim()) errs.email = 'Email is required'
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errs.email = 'Enter a valid email address'
    setErrors(errs)
    return Object.keys(errs).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return
    await onSubmit({
      full_name: fullName.trim(),
      email: email.trim(),
      relationship: relationship.trim() || undefined,
      is_emergency_contact: isEmergencyContact,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Input
        label="Full Name"
        value={fullName}
        onChange={e => setFullName(e.target.value)}
        placeholder="Jane Smith"
        error={errors.fullName}
        required
      />
      <Input
        label="Email Address"
        type="email"
        value={email}
        onChange={e => setEmail(e.target.value)}
        placeholder="jane@example.com"
        error={errors.email}
        required
      />
      <Input
        label="Relationship (optional)"
        value={relationship}
        onChange={e => setRelationship(e.target.value)}
        placeholder="Sister, Best Friend, etc."
      />
      <div className="py-2">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium text-[#0D1117] text-sm">Emergency Contact</p>
            <p className="text-xs text-[#6B7280]">Can pause delivery for 7 days</p>
          </div>
          <Toggle checked={isEmergencyContact} onChange={setIsEmergencyContact} />
        </div>
        {/* F11/FR-23: only one beneficiary can be the emergency contact. */}
        {isEmergencyContact && otherEmergencyContactName && (
          <p className="text-xs text-amber-600 mt-2">
            This will replace {otherEmergencyContactName} as your emergency contact.
          </p>
        )}
      </div>
      <div className="flex gap-3 pt-2">
        <Button type="button" variant="secondary" fullWidth onClick={onCancel} disabled={loading}>
          Cancel
        </Button>
        <Button type="submit" fullWidth loading={loading}>
          Save
        </Button>
      </div>
    </form>
  )
}
