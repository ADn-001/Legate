import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { ArrowLeft, KeyRound, CheckCircle } from 'lucide-react'
import { bip39Module, deriveRecoveryKey, hashMnemonic } from '../../crypto/bip39'
import { keysModule, toBase64, fromBase64 } from '../../crypto/keys'
import { authApi } from '../../api/auth'
import { useCryptoStore } from '../../store/crypto'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'

// T4.4: account recovery via the 24-word recovery phrase. Unwraps the CEK
// from the recovery blob, re-wraps it with a new password, and persists the
// new primary blob — this is what makes "forgot password != data loss" true.
export default function Recover() {
  const navigate = useNavigate()
  const [phrase, setPhrase] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    const words = phrase.trim().split(/\s+/).filter(Boolean)
    if (words.length !== 24 || !bip39Module.validatePhrase(phrase)) {
      setError('That recovery phrase is not valid. Check the spelling and word order.')
      return
    }
    if (newPassword.length < 12 || !/\d/.test(newPassword) || !/[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/.test(newPassword)) {
      setError('New password must be at least 12 characters and include a number and a special character.')
      return
    }
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setLoading(true)
    try {
      const recoveryPhraseHash = await hashMnemonic(phrase)
      const { data } = await authApi.validateRecoveryPhrase({ recovery_phrase_hash: recoveryPhraseHash })

      const recoveryKey = await deriveRecoveryKey(phrase, fromBase64(data.recovery_salt))
      const cek = await keysModule.decryptCEK(
        fromBase64(data.recovery_encrypted_cek),
        recoveryKey,
        fromBase64(data.recovery_cek_iv)
      )

      const newSalt = crypto.getRandomValues(new Uint8Array(16))
      const newWrappingKey = await keysModule.deriveWrappingKey(newPassword, newSalt)
      const { encryptedCek, iv } = await keysModule.encryptCEK(cek, newWrappingKey)

      await authApi.updatePrimaryKey({
        encrypted_cek: toBase64(encryptedCek),
        cek_iv: toBase64(iv),
        pbkdf2_salt: toBase64(newSalt),
      })

      useCryptoStore.getState().setCek(cek)
      setSuccess(true)
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 400) {
        setError('Incorrect recovery phrase, or no recovery phrase is set up for this account.')
      } else if (axios.isAxiosError(err) && !err.response) {
        setError("Can't reach the server. Please try again.")
      } else {
        setError('Recovery failed. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <div className="min-h-screen bg-[#F0F2F5] p-4 flex items-center justify-center">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-md p-8 text-center">
          <CheckCircle className="w-12 h-12 text-green-600 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-[#0D1117] mb-2">Recovery complete</h1>
          <p className="text-[#6B7280] mb-6">
            Your vault has been unlocked with your new password. Your existing capsules remain intact.
          </p>
          <Button fullWidth onClick={() => navigate('/vault')}>Continue to vault</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#F0F2F5] p-4">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-4 mb-8">
          <button onClick={() => navigate('/security')} className="p-2 hover:bg-white rounded-lg transition-colors">
            <ArrowLeft className="w-5 h-5 text-[#0D1117]" />
          </button>
          <div>
            <h1 className="text-3xl font-bold text-[#0D1117]">Account Recovery</h1>
            <p className="text-xs uppercase tracking-widest text-gray-400 mt-1">Restore vault access</p>
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-md p-6">
          <div className="flex items-center gap-2 mb-4">
            <KeyRound className="w-5 h-5 text-[#3D4F6B]" />
            <h3 className="font-semibold text-[#0D1117]">Enter your recovery phrase</h3>
          </div>
          <p className="text-sm text-[#6B7280] mb-4">
            Enter all 24 words of your recovery phrase, separated by spaces, and choose a new password.
            We'll use the phrase to unlock your vault and re-encrypt it with the new password.
          </p>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1">
              <label className="block text-sm font-medium text-[#0D1117]">Recovery phrase</label>
              <textarea
                value={phrase}
                onChange={e => setPhrase(e.target.value)}
                placeholder="word1 word2 word3 ... word24"
                rows={3}
                className="input-field w-full font-mono text-sm"
                required
              />
            </div>

            <Input
              label="New password"
              type="password"
              value={newPassword}
              onChange={e => setNewPassword(e.target.value)}
              placeholder="••••••••••••"
              helpText="At least 12 characters, with a number and a special character."
              required
            />

            <Input
              label="Confirm new password"
              type="password"
              value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)}
              placeholder="••••••••••••"
              required
            />

            <Button type="submit" fullWidth loading={loading}>
              Recover vault
            </Button>
          </form>
        </div>
      </div>
    </div>
  )
}
