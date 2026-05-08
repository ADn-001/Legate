/**
 * Capsule Card Component
 * - Displays capsule metadata (title, beneficiaries, status)
 * - Used in capsule list
 */

interface CapsuleCardProps {
  id: string
  title: string
  beneficiaries: string[]
  status: 'draft' | 'active' | 'delivered'
  onEdit: () => void
  onDelete: () => void
}

export default function CapsuleCard({ id, title, beneficiaries, status, onEdit, onDelete }: CapsuleCardProps) {
  // TODO: Implement CapsuleCard component
  // - Title (bold)
  // - Beneficiary names
  // - Status badge
  // - Edit icon (pencil) → onEdit
  // - Delete icon (trash) → onDelete
  // - Card styling: white bg, rounded-xl, hover effect
  return <div>Capsule Card</div>
}
