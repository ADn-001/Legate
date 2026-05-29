import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Shield, Lock, Phone } from 'lucide-react'
import { useBeneficiaries, useUpdateBeneficiary } from '../../hooks/useBeneficiaries'
import { useAuthStore } from '../../store/auth'
import { useCryptoStore } from '../../store/crypto'
import { keysModule, fromBase64 } from '../../crypto/keys'
import { authApi } from '../../api/auth'
import { usersApi } from '../../api/users'
import Button from '../../components/ui/Button'
import Modal from '../../components/ui/Modal'
import Input from '../../components/ui/Input'
import { Beneficiary } from '../../types/api'

export default function Security() {
  const navigate = useNavigate()
  const user = useAuthStore(s => s.user)
  const { data: beneficiaries } = useBeneficiaries()
  const updateBeneficiary = useUpdateBeneficiary()

  const [selectedEmergencyId, setSelectedEmergencyId] = useState('')
  const [emergencySaving, setEmergencySaving] = useState(false)
  const [emergencyMsg, setEmergencyMsg] = useState<string | null>(null)

  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState('')
  const [deletePassword, setDeletePassword] = useState('')
  const [deleteLoading, setDeleteLoading] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const cek = useCryptoStore(s => s.cek)

  const handleSetEmergencyContact = async () => {
    if (!selectedEmergencyId) return
    setEmergencySaving(true)
    setEmergencyMsg(null)
    try {
      await updateBeneficiary.mutateAsync({ id: selectedEmergencyId, data: { is_emergency_contact: true } })
      setEmergencyMsg('Emergency contact updated successfully.')
    } catch {
      setEmergencyMsg('Failed to update emergency contact.')
    } finally {
      setEmergencySaving(false)
    }
  }

  const handleDeleteAccount = async () => {
    if (deleteConfirm !== 'DELETE') { setDeleteError('You must type DELETE to confirm'); return }
    setDeleteLoading(true)
    setDeleteError(null)
    try {
      await usersApi.deleteAccount({ confirmation: 'DELETE', password: deletePassword })
      useAuthStore.getState().logout()
      useCryptoStore.getState().clearCek()
      navigate('/')
    } catch {
      setDeleteError('Incorrect password or deletion failed.')
    } finally {
      setDeleteLoading(false)
    }
  }

  const currentEmergencyContact = beneficiaries?.find((b: Beneficiary) => b.is_emergency_contact)

  return (
    <div className="min-h-screen bg-[#F0F2F5] p-4">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-4 mb-8">
          <button onClick={() => navigate('/vault')} className="p-2 hover:bg-white rounded-lg transition-colors">
            <ArrowLeft className="w-5 h-5 text-[#0D1117]" />
          </button>
          <div>
            <h1 className="text-3xl font-bold text-[#0D1117]">Security</h1>
            <p className="text-xs uppercase tracking-widest text-gray-400 mt-1">Settings & Protocols</p>
          </div>
        </div>

        {/* Vault Status */}
        <div className="bg-white rounded-2xl shadow-md p-6 mb-8">
          <h3 className="font-semibold text-[#0D1117] mb-4">Vault Status</h3>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[#6B7280] mb-1">Encryption</p>
              <p className="font-semibold text-[#0D1117]">AES-256-GCM End-to-End Encrypted</p>
              {user && <p className="text-xs text-[#6B7280] mt-1">{user.email}</p>}
            </div>
            <div className="flex items-center gap-2 px-4 py-2 bg-green-100 rounded-full">
              <div className="w-2 h-2 bg-green-600 rounded-full" />
              <span className="font-semibold text-green-800 text-sm">ACTIVE</span>
            </div>
          </div>
        </div>

        {/* Emergency Contact */}
        <div className="bg-white rounded-2xl shadow-md p-6 mb-8">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2">
              <Phone className="w-5 h-5 text-[#3D4F6B]" />
              <h3 className="font-semibold text-[#0D1117]">Emergency Contact</h3>
            </div>
            <span className="px-3 py-1 bg-blue-100 text-[#3D4F6B] text-xs font-semibold rounded-full">LEGACY ACCESS</span>
          </div>

          {currentEmergencyContact && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-4">
              <p className="text-sm text-green-800">
                Current emergency contact: <strong>{currentEmergencyContact.full_name}</strong> ({currentEmergencyContact.email})
              </p>
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-[#0D1117] mb-2">Select Emergency Contact</label>
              <select
                value={selectedEmergencyId}
                onChange={e => setSelectedEmergencyId(e.target.value)}
                className="input-field w-full"
              >
                <option value="">Choose from your beneficiaries...</option>
                {beneficiaries?.map((b: Beneficiary) => (
                  <option key={b.id} value={b.id}>{b.full_name} — {b.email}</option>
                ))}
              </select>
            </div>

            <p className="text-xs text-[#6B7280] bg-blue-50 p-3 rounded-lg">
              💡 Emergency contacts can pause delivery up to 2 times (7 days each) while they verify you are okay.
            </p>

            {emergencyMsg && (
              <p className={`text-sm ${emergencyMsg.includes('success') ? 'text-green-600' : 'text-red-600'}`}>
                {emergencyMsg}
              </p>
            )}

            <Button
              fullWidth
              loading={emergencySaving}
              disabled={!selectedEmergencyId}
              onClick={handleSetEmergencyContact}
            >
              Set as Emergency Contact
            </Button>
          </div>
        </div>

        {/* Recovery Phrase Note */}
        <div className="bg-white rounded-2xl shadow-md p-6 mb-8">
          <div className="flex items-center gap-2 mb-4">
            <Shield className="w-5 h-5 text-[#3D4F6B]" />
            <h3 className="font-semibold text-[#0D1117]">Recovery Phrase</h3>
          </div>
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
            <p className="text-sm text-amber-800">
              Your recovery phrase was shown once at setup. If you did not save it, you must delete and re-create your account to generate a new one.
            </p>
          </div>
        </div>

        {/* Account Info */}
        <div className="bg-white rounded-2xl shadow-md p-6 mb-8">
          <div className="space-y-3">
            <p className="flex items-center gap-2 text-[#0D1117]">
              <Lock className="w-4 h-4" />
              <span>🔒 Encrypted storage enabled</span>
            </p>
            <p className="flex items-center gap-2 text-[#0D1117]">
              <Shield className="w-4 h-4" />
              <span>🗑 Data deletion available below</span>
            </p>
          </div>
        </div>

        {/* Danger Zone */}
        <div className="bg-red-50 border border-red-200 rounded-2xl p-6 mb-8">
          <h3 className="font-semibold text-red-800 mb-2">Danger Zone</h3>
          <p className="text-sm text-red-700 mb-4">
            Permanently delete your account and all data. This cannot be undone.
          </p>
          <Button variant="danger" onClick={() => setShowDeleteModal(true)}>
            Delete Account
          </Button>
        </div>

        {/* Legal */}
        <div className="bg-slate-50 border border-gray-200 rounded-2xl p-6">
          <p className="text-xs text-[#6B7280] leading-relaxed">
            <strong>Important:</strong> This is not a legal will. Legate is an instruction-based system for message and document delivery. Please consult with legal professionals for official estate documentation.
          </p>
        </div>
      </div>

      {/* Delete Account Modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => { setShowDeleteModal(false); setDeleteConfirm(''); setDeletePassword(''); setDeleteError(null) }}
        title="Delete Account"
        footer={
          <div className="flex gap-3">
            <Button variant="secondary" fullWidth onClick={() => setShowDeleteModal(false)}>Cancel</Button>
            <Button variant="danger" fullWidth loading={deleteLoading} onClick={handleDeleteAccount}>
              Delete My Account
            </Button>
          </div>
        }
      >
        <div className="space-y-4">
          <p className="text-[#6B7280] text-sm">
            This will permanently delete your account, all capsules, and beneficiaries. This action cannot be undone.
          </p>
          <Input
            label='Type "DELETE" to confirm'
            value={deleteConfirm}
            onChange={e => setDeleteConfirm(e.target.value)}
            placeholder="DELETE"
          />
          <Input
            label="Enter your password"
            type="password"
            value={deletePassword}
            onChange={e => setDeletePassword(e.target.value)}
            placeholder="••••••••"
          />
          {deleteError && <p className="text-sm text-red-600">{deleteError}</p>}
        </div>
      </Modal>
    </div>
  )
}
