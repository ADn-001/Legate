/**
 * Beneficiary Card Component
 * - Displays beneficiary metadata (name, email, relationship)
 * - Used in beneficiary list
 */

interface BeneficiaryCardProps {
  id: string
  firstName: string
  lastName: string
  email: string
  relationship?: string
  isPending?: boolean
  onEdit: () => void
  onDelete: () => void
}

export default function BeneficiaryCard({
  id,
  firstName,
  lastName,
  email,
  relationship,
  isPending,
  onEdit,
  onDelete,
}: BeneficiaryCardProps) {
  // TODO: Implement BeneficiaryCard component
  // - Avatar circle (initials)
  // - Full name (bold)
  // - Email
  // - Relationship (if provided)
  // - Edit icon (pencil) → onEdit
  // - Delete icon (trash) → onDelete
  // - If pending: dashed border, italic name, "Invite pending..." subtext, × dismiss button
  // - Card styling: white bg, rounded-xl, hover effect
  return <div>Beneficiary Card</div>
}
