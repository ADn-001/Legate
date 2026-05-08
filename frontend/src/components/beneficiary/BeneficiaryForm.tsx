/**
 * Beneficiary Form Component
 * - Reusable form for adding/editing beneficiaries
 * - Fields: Full Name, Email, Relationship, Is Emergency Contact
 */

interface BeneficiaryFormProps {
  initialData?: {
    firstName: string
    lastName: string
    email: string
    relationship?: string
    isEmergencyContact?: boolean
  }
  onSubmit: (data: any) => Promise<void>
  onCancel: () => void
  loading?: boolean
}

export default function BeneficiaryForm({ initialData, onSubmit, onCancel, loading = false }: BeneficiaryFormProps) {
  // TODO: Implement BeneficiaryForm component
  // - Full Name input (or separate First/Last)
  // - Email input
  // - Relationship dropdown (optional)
  // - Is Emergency Contact toggle
  // - Save button (loading state)
  // - Cancel button
  // - Form validation
  return <form>Beneficiary Form</form>
}
