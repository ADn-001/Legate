import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Lock, Users, Clock, Shield, CheckCircle } from 'lucide-react'

export default function HowItWorks() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-[#F0F2F5] p-4">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center gap-4 mb-8">
          <button onClick={() => navigate(-1)} className="p-2 hover:bg-white rounded-lg transition-colors">
            <ArrowLeft className="w-5 h-5 text-[#0D1117]" />
          </button>
          <h1 className="text-3xl font-bold text-[#0D1117]">How Legate Works</h1>
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-2xl shadow-md p-8">
            <div className="flex items-center gap-3 mb-4">
              <div className="bg-blue-100 w-10 h-10 rounded-lg flex items-center justify-center">
                <Lock className="w-5 h-5 text-[#3D4F6B]" />
              </div>
              <h2 className="text-xl font-bold text-[#0D1117]">Step 1: Create Encrypted Capsules</h2>
            </div>
            <p className="text-[#6B7280] leading-relaxed">
              Write messages, instructions, and attach photos or videos that you want your loved ones to receive.
              Everything is encrypted directly on your device before it ever leaves your browser —
              Legate servers never see the plaintext contents of your capsules.
              Your encryption key is derived from your password using PBKDF2, and each capsule is
              encrypted with AES-256-GCM.
            </p>
          </div>

          <div className="bg-white rounded-2xl shadow-md p-8">
            <div className="flex items-center gap-3 mb-4">
              <div className="bg-blue-100 w-10 h-10 rounded-lg flex items-center justify-center">
                <Users className="w-5 h-5 text-[#3D4F6B]" />
              </div>
              <h2 className="text-xl font-bold text-[#0D1117]">Step 2: Assign Beneficiaries</h2>
            </div>
            <p className="text-[#6B7280] leading-relaxed">
              Each capsule is assigned to a beneficiary — a person you choose to receive it.
              You can designate one person as an emergency contact who can pause delivery
              if something seems wrong. Beneficiaries never have access to your account or encryption key;
              they simply receive the delivered message when the time comes.
            </p>
          </div>

          <div className="bg-white rounded-2xl shadow-md p-8">
            <div className="flex items-center gap-3 mb-4">
              <div className="bg-blue-100 w-10 h-10 rounded-lg flex items-center justify-center">
                <Clock className="w-5 h-5 text-[#3D4F6B]" />
              </div>
              <h2 className="text-xl font-bold text-[#0D1117]">Step 3: Stay Active with Check-ins</h2>
            </div>
            <p className="text-[#6B7280] leading-relaxed">
              Legate periodically sends you a check-in email. You respond to confirm you're active.
              If you miss a check-in by more than the grace period you configured, Legate begins the
              delivery process. You choose how often you want check-ins (anywhere from 7 to 365 days)
              and how long the grace period lasts.
            </p>
          </div>

          <div className="bg-white rounded-2xl shadow-md p-8">
            <div className="flex items-center gap-3 mb-4">
              <div className="bg-blue-100 w-10 h-10 rounded-lg flex items-center justify-center">
                <Shield className="w-5 h-5 text-[#3D4F6B]" />
              </div>
              <h2 className="text-xl font-bold text-[#0D1117]">Step 4: Secure Delivery</h2>
            </div>
            <p className="text-[#6B7280] leading-relaxed">
              When delivery is triggered, Legate decrypts each capsule using a separately wrapped
              delivery key (never your login password) and sends the contents to the beneficiary's
              email. Media attachments are included as 30-day signed links. After delivery, your
              account is memorialized and the underlying data is purged within 72 hours.
            </p>
          </div>

          <div className="bg-white rounded-2xl shadow-md p-8">
            <div className="flex items-center gap-3 mb-4">
              <div className="bg-blue-100 w-10 h-10 rounded-lg flex items-center justify-center">
                <CheckCircle className="w-5 h-5 text-[#3D4F6B]" />
              </div>
              <h2 className="text-xl font-bold text-[#0D1117]">Recovery Phrase</h2>
            </div>
            <p className="text-[#6B7280] leading-relaxed">
              During setup, you're given a 24-word recovery phrase. If you lose your password,
              this phrase is the only way to recover access to your vault. It is shown once and
              never stored by Legate. Store it somewhere safe — printed, written down, or in a
              secure password manager. Without it, a password reset permanently loses all capsule contents.
            </p>
          </div>

          <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6">
            <p className="text-sm text-amber-800 leading-relaxed">
              <strong>Important:</strong> Legate is not a legal will and does not constitute a legally
              binding document in any jurisdiction. For official estate planning, please consult a
              licensed attorney.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
