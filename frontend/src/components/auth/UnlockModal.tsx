import { useState } from 'react'
import Modal from '../ui/Modal'
import Button from '../ui/Button'
import { authApi } from '../../api/auth'
import { keysModule, fromBase64 } from '../../crypto/keys'
import { useCryptoStore } from '../../store/crypto'
import { useUnlockStore } from '../../store/unlock'

export default function UnlockModal() {
  const { isOpen, pending, _close } = useUnlockStore()
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const reset = () => {
    setPassword('')
    setError(null)
    setLoading(false)
  }

  const handleCancel = () => {
    pending?.reject(new Error('Unlock cancelled'))
    reset()
    _close()
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const keyRes = await authApi.getEncryptionKey()
      const { encrypted_cek, cek_iv, pbkdf2_salt } = keyRes.data
      const salt = fromBase64(pbkdf2_salt)
      const wrappingKey = await keysModule.deriveWrappingKey(password, salt)
      const cek = await keysModule.decryptCEK(fromBase64(encrypted_cek), wrappingKey, fromBase64(cek_iv))

      useCryptoStore.getState().setCek(cek)
      pending?.resolve(cek)
      reset()
      _close()
    } catch {
      setError('Incorrect password')
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <Modal isOpen={isOpen} onClose={handleCancel} title="Unlock your vault">
      <form onSubmit={handleSubmit} className="space-y-4">
        <p className="text-sm text-[#6B7280]">
          Enter your password to decrypt your data for this session.
        </p>
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}
        <div>
          <label className="block text-sm font-medium text-[#0D1117] mb-2">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            className="input-field w-full"
            autoFocus
            required
          />
        </div>
        <div className="flex gap-3 pt-2">
          <Button type="button" variant="secondary" fullWidth onClick={handleCancel} disabled={loading}>
            Cancel
          </Button>
          <Button type="submit" fullWidth loading={loading}>
            Unlock
          </Button>
        </div>
      </form>
    </Modal>
  )
}
