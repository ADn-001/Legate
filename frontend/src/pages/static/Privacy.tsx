import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'

export default function Privacy() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-[#F0F2F5] p-4">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center gap-4 mb-8">
          <button onClick={() => navigate(-1)} className="p-2 hover:bg-white rounded-lg transition-colors">
            <ArrowLeft className="w-5 h-5 text-[#0D1117]" />
          </button>
          <h1 className="text-3xl font-bold text-[#0D1117]">Privacy Policy</h1>
        </div>

        <div className="bg-white rounded-2xl shadow-md p-8 space-y-6 text-[#374151] leading-relaxed">
          <p className="text-sm text-[#6B7280]">Last updated: June 2026</p>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">1. What We Collect</h2>
            <p>
              We collect your email address, full name (optional), and the encrypted blobs that constitute
              your capsule content and media attachments. We also collect standard server logs including
              IP addresses and request timestamps for security and abuse prevention.
            </p>
            <p className="mt-2">
              <strong>Capsule contents are end-to-end encrypted.</strong> Legate stores only ciphertext.
              We cannot read your capsule messages or view your media attachments without your encryption key,
              which is derived from your password and never transmitted to our servers in plaintext.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">2. How We Use It</h2>
            <p>
              We use your email address to send check-in reminders, OTP verification codes, and —
              when the delivery condition is met — to deliver your capsules to your designated beneficiaries.
              We do not use your information for advertising.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">3. Sharing</h2>
            <p>
              We share your information only with infrastructure providers necessary to operate the service
              (cloud hosting, email delivery). We do not sell your data. We may disclose information if
              required by law or valid legal process.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">4. Data Retention</h2>
            <p>
              Your account data is retained as long as your account is active. Within 72 hours of
              successful capsule delivery, the underlying encrypted content blobs are purged from
              storage. You may request deletion of your account at any time from the Security settings page.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">5. Security</h2>
            <p>
              Capsule contents are encrypted client-side with AES-256-GCM. Your password is never sent
              to our servers — only derived key material is used. We use industry-standard TLS for all
              data in transit. However, no system is 100% secure. We recommend keeping your recovery phrase
              in a physically secure location.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">6. Your Rights</h2>
            <p>
              Depending on your jurisdiction, you may have rights to access, correct, or delete your
              personal data. Contact us at privacy@legate.app to exercise these rights. Account deletion
              is also available directly in the app under Security → Danger Zone.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">7. Contact</h2>
            <p>
              Questions about this policy? Email <a href="mailto:privacy@legate.app" className="text-[#3D4F6B] underline">privacy@legate.app</a>.
            </p>
          </section>
        </div>
      </div>
    </div>
  )
}
