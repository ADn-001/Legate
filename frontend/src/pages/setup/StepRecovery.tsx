import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { bip39Module, deriveRecoveryKey, hashMnemonic } from '../../crypto/bip39'
import { keysModule, toBase64 } from '../../crypto/keys'
import { authApi } from '../../api/auth'
import { usersApi } from '../../api/users'
import { useAuthStore } from '../../store/auth'
import { requireCek } from '../../store/unlock'
import Button from '../../components/ui/Button'
import { Copy, CheckCircle } from 'lucide-react'

export default function StepRecovery() {
  const navigate = useNavigate()
  const authStore = useAuthStore()
  const [words, setWords] = useState<string[]>([])
  const [checked, setChecked] = useState(false)
  const [copied, setCopied] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setWords(bip39Module.generatePhrase())
  }, [])

  const handleCopy = async () => {
    await navigator.clipboard.writeText(words.join(' '))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleReady = async () => {
    setLoading(true)
    setError(null)
    try {
      // T4.3: wrap the CEK with a recovery-phrase-derived key and store the
      // second blob server-side. The phrase itself is never sent.
      const cek = await requireCek()
      const mnemonic = words.join(' ')
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

      try {
        await usersApi.update({ needs_onboarding: false })
      } catch {
        // Non-critical: the user can still proceed, onboarding flag will
        // resync on next load.
      }
      authStore.setNeedsOnboarding(false)
      navigate('/vault')
    } catch {
      setError('Could not save your recovery phrase. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-md mx-auto px-4 pb-8">
      <div className="bg-white rounded-2xl shadow-lg p-8">
        <h1 className="text-2xl font-bold text-[#0D1117] mb-2">Your Recovery Phrase</h1>
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
          <p className="text-sm text-amber-800 font-medium">
            ⚠️ Write this down. You cannot recover your capsules without it. This phrase is shown only once.
          </p>
        </div>

        <div className="grid grid-cols-4 gap-2 mb-4">
          {words.map((word, i) => (
            <div key={i} className="bg-slate-50 rounded-lg p-2 text-center">
              <p className="text-xs text-[#6B7280] mb-0.5">{i + 1}</p>
              <p className="text-sm font-medium text-[#0D1117]">{word}</p>
            </div>
          ))}
        </div>

        <button
          onClick={handleCopy}
          className="w-full py-2 mb-6 border border-gray-200 rounded-xl text-sm font-medium text-[#3D4F6B] hover:bg-gray-50 flex items-center justify-center gap-2"
        >
          {copied ? <CheckCircle className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
          {copied ? 'Copied!' : 'Copy to clipboard'}
        </button>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        <label className="flex items-start gap-3 mb-6 cursor-pointer">
          <input
            type="checkbox"
            checked={checked}
            onChange={e => setChecked(e.target.checked)}
            className="mt-0.5 w-4 h-4 accent-[#3D4F6B]"
          />
          <span className="text-sm text-[#0D1117]">
            I have written down my recovery phrase and stored it somewhere safe.
          </span>
        </label>

        <Button fullWidth disabled={!checked} loading={loading} onClick={handleReady}>
          I'm Ready
        </Button>
      </div>
    </div>
  )
}
