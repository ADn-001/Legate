import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { Shield, KeyRound, CheckCircle, AlertTriangle } from 'lucide-react'
import { bip39Module, deriveRecoveryKey, hashMnemonic } from '../../crypto/bip39'
import { keysModule, toBase64, fromBase64 } from '../../crypto/keys'
import { authApi } from '../../api/auth'
import { useAuthStore } from '../../store/auth'
import { useCryptoStore } from '../../store/crypto'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'

const PASSWORD_HELP = 'At least 12 characters, with a number and a special character.'

const isWeakPassword = (pw: string) =>
  pw.length < 12 || !/\d/.test(pw) || !/[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/.test(pw)

// T6.2/T6.3: lands here from the Supabase password-reset magic link
// (#access_token=...&refresh_token=...&type=recovery). Authenticates with
// those tokens, then requires the recovery phrase to unwrap and re-wrap the
// CEK under the new password. Accounts with no recovery blob are offered an
// explicit reset-with-data-loss path.
export default function ResetPassword() {
  const navigate = useNavigate()

  const [linkValid, setLinkValid] = useState<boolean | null>(null)
  const [phrase, setPhrase] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [noRecoveryBlob, setNoRecoveryBlob] = useState(false)
  const [dataLossConfirm, setDataLossConfirm] = useState('')

  useEffect(() => {
    const rawHash = window.location.hash.startsWith('#') ? window.location.hash.slice(1) : window.location.hash
    const params = new URLSearchParams(rawHash)
    const accessToken = params.get('access_token')
    const refreshToken = params.get('refresh_token')

    if (!accessToken || !refreshToken) {
      setLinkValid(false)
      return
    }

    useAuthStore.getState().setTokens(accessToken, refreshToken)

    ;(async () => {
      try {
        const { data: meData } = await authApi.getMe()
        useAuthStore.getState().setUser(meData)
        useAuthStore.getState().setNeedsOnboarding(!!meData.needs_onboarding)
        setLinkValid(true)
      } catch {
        setLinkValid(false)
      }
    })()
  }, [])

  const validateInputs = (): string | null => {
    const words = phrase.trim().split(/\s+/).filter(Boolean)
    if (words.length !== 24 || !bip39Module.validatePhrase(phrase)) {
      return 'That recovery phrase is not valid. Check the spelling and word order.'
    }
    if (isWeakPassword(newPassword)) {
      return 'New password must be at least 12 characters and include a number and a special character.'
    }
    if (newPassword !== confirmPassword) {
      return 'Passwords do not match.'
    }
    return null
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    const validationError = validateInputs()
    if (validationError) {
      setError(validationError)
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

      await authApi.resetPassword({
        new_password: newPassword,
        encrypted_cek: toBase64(encryptedCek),
        cek_iv: toBase64(iv),
        pbkdf2_salt: toBase64(newSalt),
      })

      useCryptoStore.getState().setCek(cek)
      setSuccess(true)
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 400) {
        // No recovery blob set up for this account (legacy account).
        setNoRecoveryBlob(true)
      } else if (axios.isAxiosError(err) && !err.response) {
        setError("Can't reach the server. Please try again.")
      } else if (axios.isAxiosError(err) && (err.response?.status === 401 || err.response?.status === 403)) {
        setError('This password reset link is invalid or has expired. Request a new one.')
      } else {
        setError('Password reset failed. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleDataLossReset = async () => {
    if (dataLossConfirm !== 'RESET') {
      setError('Type RESET to confirm.')
      return
    }
    if (isWeakPassword(newPassword)) {
      setError('New password must be at least 12 characters and include a number and a special character.')
      return
    }
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setError(null)
    setLoading(true)
    try {
      const cek = await keysModule.generateCEK()
      const newSalt = crypto.getRandomValues(new Uint8Array(16))
      const newWrappingKey = await keysModule.deriveWrappingKey(newPassword, newSalt)
      const { encryptedCek, iv } = await keysModule.encryptCEK(cek, newWrappingKey)

      await authApi.resetPasswordDataLoss({
        new_password: newPassword,
        encrypted_cek: toBase64(encryptedCek),
        cek_iv: toBase64(iv),
        pbkdf2_salt: toBase64(newSalt),
      })

      useCryptoStore.getState().setCek(cek)
      setSuccess(true)
    } catch (err) {
      if (axios.isAxiosError(err) && !err.response) {
        setError("Can't reach the server. Please try again.")
      } else if (axios.isAxiosError(err) && (err.response?.status === 401 || err.response?.status === 403)) {
        setError('This password reset link is invalid or has expired. Request a new one.')
      } else {
        setError('Password reset failed. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  if (linkValid === null) {
    return (
      <div className="min-h-screen bg-[#F0F2F5] flex items-center justify-center p-4">
        <p className="text-[#6B7280]">Checking your reset link…</p>
      </div>
    )
  }

  if (linkValid === false) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
        <div className="w-full max-w-md bg-white rounded-2xl shadow-lg p-8 text-center">
          <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-[#0D1117] mb-2">Link invalid or expired</h1>
          <p className="text-[#6B7280] mb-6">
            This password reset link is no longer valid. Reset links expire after 30 minutes and can only be used once.
          </p>
          <Button fullWidth onClick={() => navigate('/auth/forgot-password')}>Request a new link</Button>
        </div>
      </div>
    )
  }

  if (success) {
    return (
      <div className="min-h-screen bg-[#F0F2F5] p-4 flex items-center justify-center">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-md p-8 text-center">
          <CheckCircle className="w-12 h-12 text-green-600 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-[#0D1117] mb-2">Password reset</h1>
          <p className="text-[#6B7280] mb-6">
            {noRecoveryBlob
              ? 'Your password has been reset with a new vault key. Capsules created before this reset can no longer be decrypted.'
              : 'Your password has been changed and your vault is unlocked. Your existing capsules remain intact.'}
          </p>
          <Button fullWidth onClick={() => navigate('/vault')}>Continue to vault</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#F0F2F5] p-4">
      <div className="max-w-2xl mx-auto py-12">
        <div className="flex items-center justify-center gap-2 mb-8">
          <Shield className="w-8 h-8 text-[#3D4F6B]" />
          <span className="text-2xl font-bold text-[#3D4F6B]">Legate</span>
        </div>

        {!noRecoveryBlob ? (
          <div className="bg-white rounded-2xl shadow-md p-6">
            <div className="flex items-center gap-2 mb-4">
              <KeyRound className="w-5 h-5 text-[#3D4F6B]" />
              <h3 className="font-semibold text-[#0D1117]">Reset your password</h3>
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
                helpText={PASSWORD_HELP}
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
                Reset password
              </Button>
            </form>
          </div>
        ) : (
          <div className="bg-white rounded-2xl shadow-md p-6">
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle className="w-5 h-5 text-amber-500" />
              <h3 className="font-semibold text-[#0D1117]">No recovery phrase on file</h3>
            </div>

            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-4">
              <p className="text-sm text-amber-800">
                This account has no recovery phrase set up, so your existing vault contents cannot be unlocked
                with a new password. You can still reset your password and create a new vault key, but
                <strong> all capsules you've already written will become permanently unrecoverable</strong> —
                they'll be marked as such so you can re-create them.
              </p>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            <div className="space-y-4">
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
                value={confirmPassword}
                onChange={e => setConfirmPassword(e.target.value)}
                placeholder="••••••••••••"
                required
              />

              <Input
                label='Type "RESET" to confirm permanent data loss'
                value={dataLossConfirm}
                onChange={e => setDataLossConfirm(e.target.value)}
                placeholder="RESET"
              />

              <div className="flex gap-3">
                <Button variant="secondary" fullWidth onClick={() => { setNoRecoveryBlob(false); setError(null) }}>
                  Back
                </Button>
                <Button variant="danger" fullWidth loading={loading} onClick={handleDataLossReset}>
                  Reset anyway
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
