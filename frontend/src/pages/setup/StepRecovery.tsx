import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { bip39Module } from '../../crypto/bip39'
import { usersApi } from '../../api/users'
import { useAuthStore } from '../../store/auth'
import Button from '../../components/ui/Button'
import { Copy, CheckCircle } from 'lucide-react'

export default function StepRecovery() {
  const navigate = useNavigate()
  const authStore = useAuthStore()
  const [words, setWords] = useState<string[]>([])
  const [checked, setChecked] = useState(false)
  const [copied, setCopied] = useState(false)
  const [loading, setLoading] = useState(false)

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
    try {
      await usersApi.update({ needs_onboarding: false })
      authStore.setNeedsOnboarding(false)
      navigate('/vault')
    } catch {
      navigate('/vault')
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
