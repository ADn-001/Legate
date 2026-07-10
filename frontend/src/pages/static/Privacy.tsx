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
          <p className="text-sm text-[#6B7280]">Last updated: July 2026</p>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">1. What We Collect</h2>
            <p>
              We collect your email address, full name (optional), your beneficiaries' names and email
              addresses, and the encrypted blobs that constitute your capsule content and media
              attachments. We also collect standard server logs (IP addresses, request timestamps) for
              security, rate-limiting, and abuse prevention, and an internal activity log of account
              events (sign-in, check-ins, capsule and beneficiary changes) that you can review yourself
              under Activity in the app.
            </p>
            <p className="mt-2">
              <strong>Capsule contents are end-to-end encrypted.</strong> Legate stores only ciphertext —
              your title, message, and any photos or video are encrypted in your browser with AES-256-GCM
              before they ever reach our servers. We cannot read your capsule messages or view your media
              attachments in normal operation.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">2. How We Use It</h2>
            <p>
              We use your email address to send check-in reminders, OTP verification codes, grace-period
              alerts, and — when the delivery condition is met — to deliver your capsules to your
              designated beneficiaries. Beneficiary email addresses are used only to send the nomination
              notice (unless you add them silently) and, eventually, the delivery itself. We do not use
              your information for advertising, and we do not run any third-party analytics or ad tracking
              on this site.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">3. How Your Encryption Key Works</h2>
            <p>
              Your capsule content is protected by a single encryption key that is wrapped (encrypted) three
              separate ways: once under a key derived from your password, once under a key derived from your
              24-word recovery phrase, and once under a delivery key that only our automated delivery process
              can use, and only at the moment your account's delivery condition is actually triggered. Your
              password and recovery phrase are never sent to our servers in plaintext — only derived,
              one-way key material is used. This means that outside of an actual triggered delivery, no one
              at Legate — including us — can decrypt your capsules.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">4. Cookies and Local Storage</h2>
            <p>
              Legate does not use tracking or advertising cookies. Your session is kept using a token stored
              in your browser's local storage, and unsent capsule drafts are cached locally, encrypted at
              rest with your encryption key, so you don't lose work if you close the tab. If you install
              Legate as an app (PWA), your device additionally caches app files and recently viewed data
              for offline access. None of this local data leaves your device.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">5. Sharing</h2>
            <p>
              We share your information only with the infrastructure providers necessary to operate the
              service: our cloud database/storage provider and our transactional email provider. Neither is
              permitted to use your data for their own purposes. We do not sell your data. We may disclose
              information if required by law or valid legal process.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">6. Data Retention</h2>
            <p>
              Your account data is retained as long as your account is active. Within 72 hours of a
              successful capsule delivery, the underlying encrypted content and media blobs are purged from
              storage and your account is marked read-only. If you delete your account yourself, it is
              immediately deactivated and then permanently erased — including your capsules, beneficiaries,
              and encryption keys — within 72 hours, via an automated process you can trigger any time from
              Security settings.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">7. Security</h2>
            <p>
              Capsule contents are encrypted client-side with AES-256-GCM before upload. Your password is
              never sent to our servers — only derived key material is used. We use industry-standard TLS
              for all data in transit, and rate-limit authentication endpoints against abuse. However, no
              system is 100% secure. We recommend keeping your recovery phrase in a physically secure
              location — it is shown to you only once and cannot be retrieved later, only replaced.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">8. Your Rights</h2>
            <p>
              Depending on your jurisdiction, you may have rights to access, correct, or delete your
              personal data. Account deletion is available directly in the app under Security → Delete
              Account, and takes effect immediately with full erasure completing within 72 hours. For any
              other request, contact us at the email below.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">9. Contact</h2>
            <p>
              Questions about this policy? Email{' '}
              <a href="mailto:AdnanMohammedShelim+legate@gmail.com" className="text-[#3D4F6B] underline">
                AdnanMohammedShelim+legate@gmail.com
              </a>.
            </p>
          </section>
        </div>
      </div>
    </div>
  )
}
