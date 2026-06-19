import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { ArrowLeft, Shield, Lock, Phone, KeyRound, CheckCircle, HardDrive, RefreshCw, Copy, AlertTriangle } from 'lucide-react'
import { useBeneficiaries, useUpdateBeneficiary } from '../../hooks/useBeneficiaries'
import { useAuthStore } from '../../store/auth'
import { useCryptoStore } from '../../store/crypto'
import { usersApi } from '../../api/users'
import { authApi } from '../../api/auth'
import { settingsApi } from '../../api/settings'
import { keysModule, toBase64, fromBase64 } from '../../crypto/keys'
import { bip39Module, deriveRecoveryKey, hashMnemonic } from '../../crypto/bip39'
import Button from '../../components/ui/Button'
import Modal from '../../components/ui/Modal'
import Input from '../../components/ui/Input'
import { Beneficiary, StorageUsage } from '../../types/api'

const PASSWORD_HELP = 'At least 12 characters, with a number and a special character.'

const isWeakPassword = (pw: string) =>
  pw.length < 12 || !/\d/.test(pw) || !/[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/.test(pw)

// F12/FR-36: human-readable storage size for the usage progress bar.
const formatBytes = (bytes: number): string => {
  if (bytes <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

export default function Security() {
  const navigate = useNavigate()
  const user = useAuthStore(s => s.user)
  const { data: beneficiaries } = useBeneficiaries()
  const updateBeneficiary = useUpdateBeneficiary()

  const [selectedEmergencyId, setSelectedEmergencyId] = useState('')
  const [emergencySaving, setEmergencySaving] = useState(false)
  const [emergencyMsg, setEmergencyMsg] = useState<string | null>(null)

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmNewPassword, setConfirmNewPassword] = useState('')
  const [passwordLoading, setPasswordLoading] = useState(false)
  const [passwordError, setPasswordError] = useState<string | null>(null)
  const [passwordSuccess, setPasswordSuccess] = useState(false)

  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState('')
  const [deletePassword, setDeletePassword] = useState('')
  const [deleteLoading, setDeleteLoading] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  // F12/FR-36: storage usage progress bar.
  const { data: storageUsage } = useQuery<StorageUsage>({
    queryKey: ['storage-usage'],
    queryFn: () => settingsApi.getStorageUsage().then(r => r.data),
  })
  const storagePercent = storageUsage && storageUsage.limit_bytes > 0
    ? Math.min(100, (storageUsage.total_bytes / storageUsage.limit_bytes) * 100)
    : 0

  // F12/T4.5: regenerate recovery phrase, gated by password confirmation (FR-35).
  const [showRegenModal, setShowRegenModal] = useState(false)
  const [regenStep, setRegenStep] = useState<'password' | 'phrase' | 'success'>('password')
  const [regenPassword, setRegenPassword] = useState('')
  const [regenWords, setRegenWords] = useState<string[]>([])
  const [regenChecked, setRegenChecked] = useState(false)
  const [regenCopied, setRegenCopied] = useState(false)
  const [regenLoading, setRegenLoading] = useState(false)
  const [regenError, setRegenError] = useState<string | null>(null)
  const regenCekRef = useRef<CryptoKey | null>(null)

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

  const closeRegenModal = () => {
    setShowRegenModal(false)
    setRegenStep('password')
    setRegenPassword('')
    setRegenWords([])
    setRegenChecked(false)
    setRegenCopied(false)
    setRegenError(null)
    regenCekRef.current = null
  }

  // F12/T4.5 step 1: confirm the current password (FR-35 re-access) and
  // recover the CEK from it, then generate a brand-new 24-word phrase.
  const handleRegenPasswordConfirm = async () => {
    setRegenError(null)
    if (!regenPassword) { setRegenError('Enter your password.'); return }

    setRegenLoading(true)
    try {
      const { data } = await authApi.getEncryptionKey()
      const { encrypted_cek, cek_iv, pbkdf2_salt } = data
      const wrappingKey = await keysModule.deriveWrappingKey(regenPassword, fromBase64(pbkdf2_salt))

      try {
        regenCekRef.current = await keysModule.decryptCEK(fromBase64(encrypted_cek), wrappingKey, fromBase64(cek_iv))
      } catch {
        setRegenError('Incorrect password.')
        return
      }

      setRegenWords(bip39Module.generatePhrase())
      setRegenStep('phrase')
    } catch (err) {
      if (axios.isAxiosError(err) && !err.response) {
        setRegenError("Can't reach the server. Please try again.")
      } else {
        setRegenError('Something went wrong. Please try again.')
      }
    } finally {
      setRegenLoading(false)
    }
  }

  const handleRegenCopy = async () => {
    await navigator.clipboard.writeText(regenWords.join(' '))
    setRegenCopied(true)
    setTimeout(() => setRegenCopied(false), 2000)
  }

  // F12/T4.5 step 2: wrap the existing CEK under a key derived from the new
  // phrase and overwrite the recovery blob — this permanently invalidates
  // the previous phrase (PATCH /auth/me/recovery-key).
  const handleRegenConfirm = async () => {
    const cek = regenCekRef.current
    if (!cek) return

    setRegenError(null)
    setRegenLoading(true)
    try {
      const mnemonic = regenWords.join(' ')
      const salt = crypto.getRandomValues(new Uint8Array(16))
      const recoveryKey = await deriveRecoveryKey(mnemonic, salt)
      const { encryptedCek, iv } = await keysModule.encryptCEK(cek, recoveryKey)
      const recoveryPhraseHash = await hashMnemonic(mnemonic)

      await authApi.setRecoveryKey({
        recovery_encrypted_cek: toBase64(encryptedCek),
        recovery_cek_iv: toBase64(iv),
        recovery_salt: toBase64(salt),
        recovery_phrase_hash: recoveryPhraseHash,
      })

      setRegenStep('success')
    } catch {
      setRegenError('Could not save your new recovery phrase. Please try again.')
    } finally {
      setRegenLoading(false)
    }
  }

  // T6.4: change password from a logged-in session. Re-derives the CEK from
  // the current password (which both confirms it locally and recovers the
  // CEK), then re-wraps it under the new password.
  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setPasswordError(null)
    setPasswordSuccess(false)

    if (!currentPassword) {
      setPasswordError('Enter your current password.')
      return
    }
    if (isWeakPassword(newPassword)) {
      setPasswordError('New password must be at least 12 characters and include a number and a special character.')
      return
    }
    if (newPassword !== confirmNewPassword) {
      setPasswordError('New passwords do not match.')
      return
    }
    if (newPassword === currentPassword) {
      setPasswordError('New password must be different from your current password.')
      return
    }

    setPasswordLoading(true)
    try {
      const { data } = await authApi.getEncryptionKey()
      const { encrypted_cek, cek_iv, pbkdf2_salt } = data
      const wrappingKey = await keysModule.deriveWrappingKey(currentPassword, fromBase64(pbkdf2_salt))

      let cek: CryptoKey
      try {
        cek = await keysModule.decryptCEK(fromBase64(encrypted_cek), wrappingKey, fromBase64(cek_iv))
      } catch {
        setPasswordError('Incorrect current password.')
        return
      }

      const newSalt = crypto.getRandomValues(new Uint8Array(16))
      const newWrappingKey = await keysModule.deriveWrappingKey(newPassword, newSalt)
      const { encryptedCek, iv } = await keysModule.encryptCEK(cek, newWrappingKey)

      await authApi.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        encrypted_cek: toBase64(encryptedCek),
        cek_iv: toBase64(iv),
        pbkdf2_salt: toBase64(newSalt),
      })

      useCryptoStore.getState().setCek(cek)
      setPasswordSuccess(true)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmNewPassword('')
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 401) {
        setPasswordError('Incorrect current password.')
      } else if (axios.isAxiosError(err) && !err.response) {
        setPasswordError("Can't reach the server. Please try again.")
      } else {
        setPasswordError('Password change failed. Please try again.')
      }
    } finally {
      setPasswordLoading(false)
    }
  }

  const handleDeleteAccount = async () => {
    if (deleteConfirm !== 'DELETE') { setDeleteError('You must type DELETE to confirm'); return }
    setDeleteLoading(true)
    setDeleteError(null)
    try {
      await usersApi.deleteAccount({ confirmation: 'DELETE', password: deletePassword })
      useAuthStore.getState().clear()
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

        {/* Storage Usage (F12/FR-36/FR-46) */}
        {storageUsage && (
          <div className="bg-white rounded-2xl shadow-md p-6 mb-8">
            <div className="flex items-center gap-2 mb-4">
              <HardDrive className="w-5 h-5 text-[#3D4F6B]" />
              <h3 className="font-semibold text-[#0D1117]">Storage</h3>
            </div>
            <div className="flex items-center justify-between text-sm text-[#6B7280] mb-2">
              <span>{formatBytes(storageUsage.total_bytes)} used</span>
              <span>{formatBytes(storageUsage.limit_bytes)} limit</span>
            </div>
            <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${storagePercent >= 90 ? 'bg-red-500' : storagePercent >= 75 ? 'bg-amber-500' : 'bg-[#3D4F6B]'}`}
                style={{ width: `${storagePercent}%` }}
              />
            </div>
            {storagePercent >= 90 && (
              <p className="text-xs text-red-600 mt-2">You're nearly out of storage.</p>
            )}
          </div>
        )}

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
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-4">
            <p className="text-sm text-amber-800">
              Your recovery phrase was shown once at setup. If you did not save it, you must delete and re-create your account to generate a new one.
            </p>
          </div>
          <Button variant="secondary" onClick={() => setShowRegenModal(true)}>
            <RefreshCw className="w-4 h-4" />
            Regenerate Recovery Phrase
          </Button>
        </div>

        {/* Change Password */}
        <div className="bg-white rounded-2xl shadow-md p-6 mb-8">
          <div className="flex items-center gap-2 mb-4">
            <KeyRound className="w-5 h-5 text-[#3D4F6B]" />
            <h3 className="font-semibold text-[#0D1117]">Change Password</h3>
          </div>

          {passwordSuccess && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-4 flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-green-600 flex-shrink-0" />
              <p className="text-sm text-green-800">Your password has been changed.</p>
            </div>
          )}

          {passwordError && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
              <p className="text-sm text-red-700">{passwordError}</p>
            </div>
          )}

          <form onSubmit={handleChangePassword} className="space-y-4">
            <Input
              label="Current password"
              type="password"
              value={currentPassword}
              onChange={e => setCurrentPassword(e.target.value)}
              placeholder="••••••••••••"
              required
            />
            <Input
              label="New password"
              type="password"
              value={newPassword}
              onChange={e => setNewPassword(e.target.value)}
              placeholder="••••••••••••"
              helpText={PASSWORD_HELP}
              required
            />
            <Input
              label="Confirm new password"
              type="password"
              value={confirmNewPassword}
              onChange={e => setConfirmNewPassword(e.target.value)}
              placeholder="••••••••••••"
              required
            />
            <Button type="submit" loading={passwordLoading}>
              Update Password
            </Button>
          </form>
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

      {/* Regenerate Recovery Phrase Modal (F12/T4.5) */}
      <Modal
        isOpen={showRegenModal}
        onClose={closeRegenModal}
        title="Regenerate Recovery Phrase"
        footer={
          regenStep === 'password' ? (
            <div className="flex gap-3">
              <Button variant="secondary" fullWidth onClick={closeRegenModal}>Cancel</Button>
              <Button fullWidth loading={regenLoading} onClick={handleRegenPasswordConfirm}>Continue</Button>
            </div>
          ) : regenStep === 'phrase' ? (
            <div className="flex gap-3">
              <Button variant="secondary" fullWidth onClick={closeRegenModal}>Cancel</Button>
              <Button fullWidth disabled={!regenChecked} loading={regenLoading} onClick={handleRegenConfirm}>
                Confirm & Replace
              </Button>
            </div>
          ) : (
            <Button fullWidth onClick={closeRegenModal}>Done</Button>
          )
        }
      >
        {regenStep === 'password' && (
          <div className="space-y-4">
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-700">
                Regenerating your recovery phrase permanently invalidates your current one. Confirm your password to continue.
              </p>
            </div>
            <Input
              label="Current password"
              type="password"
              value={regenPassword}
              onChange={e => setRegenPassword(e.target.value)}
              placeholder="••••••••••••"
              required
            />
            {regenError && <p className="text-sm text-red-600">{regenError}</p>}
          </div>
        )}

        {regenStep === 'phrase' && (
          <div className="space-y-4">
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
              <p className="text-sm text-amber-800 font-medium">
                ⚠️ Write this down. Your old recovery phrase stops working as soon as you confirm. This new phrase is shown only once.
              </p>
            </div>
            <div className="grid grid-cols-4 gap-2">
              {regenWords.map((word, i) => (
                <div key={i} className="bg-slate-50 rounded-lg p-2 text-center">
                  <p className="text-xs text-[#6B7280] mb-0.5">{i + 1}</p>
                  <p className="text-sm font-medium text-[#0D1117]">{word}</p>
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={handleRegenCopy}
              className="w-full py-2 border border-gray-200 rounded-xl text-sm font-medium text-[#3D4F6B] hover:bg-gray-50 flex items-center justify-center gap-2"
            >
              {regenCopied ? <CheckCircle className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
              {regenCopied ? 'Copied!' : 'Copy to clipboard'}
            </button>
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={regenChecked}
                onChange={e => setRegenChecked(e.target.checked)}
                className="mt-0.5 w-4 h-4 accent-[#3D4F6B]"
              />
              <span className="text-sm text-[#0D1117]">
                I have written down my new recovery phrase and stored it somewhere safe.
              </span>
            </label>
            {regenError && <p className="text-sm text-red-600">{regenError}</p>}
          </div>
        )}

        {regenStep === 'success' && (
          <div className="text-center py-4">
            <CheckCircle className="w-12 h-12 text-green-600 mx-auto mb-4" />
            <p className="text-[#0D1117] font-medium mb-1">Recovery phrase regenerated</p>
            <p className="text-sm text-[#6B7280]">Your old recovery phrase no longer works.</p>
          </div>
        )}
      </Modal>
    </div>
  )
}
