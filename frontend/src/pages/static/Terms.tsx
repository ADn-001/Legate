import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'

export default function Terms() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-[#F0F2F5] p-4">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center gap-4 mb-8">
          <button onClick={() => navigate(-1)} className="p-2 hover:bg-white rounded-lg transition-colors">
            <ArrowLeft className="w-5 h-5 text-[#0D1117]" />
          </button>
          <h1 className="text-3xl font-bold text-[#0D1117]">Terms of Service</h1>
        </div>

        <div className="bg-white rounded-2xl shadow-md p-8 space-y-6 text-[#374151] leading-relaxed">
          <p className="text-sm text-[#6B7280]">Last updated: July 2026</p>

          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
            <p className="text-sm text-amber-800">
              <strong>Legate is not a legal will, estate planning service, or substitute for legal counsel.</strong>
              It is a message delivery platform. Please consult a licensed attorney for official estate planning.
              Legate also cannot determine or declare that you have died — only that you stopped
              responding to check-ins.
            </p>
          </div>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">1. Acceptance</h2>
            <p>
              By creating an account or using Legate, you agree to these Terms. If you disagree,
              do not use the service. We may update these Terms periodically; continued use constitutes acceptance.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">2. Service Description</h2>
            <p>
              Legate lets you create encrypted personal messages ("capsules"), optionally with photo or
              video attachments, and assign each one to a beneficiary. You set a check-in interval and a
              grace period; if you don't confirm a check-in within that window, your capsules are
              automatically delivered to your beneficiaries by email. You may optionally designate one
              beneficiary as an emergency contact, who can pause an in-progress delivery countdown a
              limited number of times before it proceeds. You may add beneficiaries with or without an
              upfront notification email — either way, they only ever receive account access-free content:
              beneficiaries cannot log in to your account or see your settings. Delivery is automated and
              not guaranteed to occur within any specific timeframe.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">3. Account, Password, and Recovery Phrase</h2>
            <p>
              You are responsible for maintaining the security of your account password and your 24-word
              recovery phrase. Your recovery phrase is shown to you once, at setup, and is not stored by
              Legate in any recoverable form — if you lose both your password and your recovery phrase,
              Legate cannot recover your encrypted capsule content. Regenerating your recovery phrase from
              Security settings immediately invalidates the previous one. You must be 18 years or older to
              create an account.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">4. Prohibited Content</h2>
            <p>
              You may not use Legate to store or deliver content that is illegal, defamatory, threatening,
              harassing, or that violates any applicable law. We reserve the right to terminate accounts
              that violate these terms, subject to applicable notice requirements. Because capsule content
              is end-to-end encrypted, we cannot proactively screen it — enforcement of this section relies
              on reports and legal process.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">5. Delivery</h2>
            <p>
              Legate will make commercially reasonable efforts to deliver capsules when triggered. Delivery
              is attempted per beneficiary and retried automatically on failure (invalid address, full
              inbox, temporary provider issue) without resending to beneficiaries who already received
              their capsule. Any photo or video attachment is delivered as a signed link that expires a
              few days after delivery, timed to when the underlying encrypted files are removed from
              storage. Legate is not liable for non-delivery resulting from factors outside its reasonable
              control, including a beneficiary's email provider rejecting or losing the message.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">6. Account Deletion</h2>
            <p>
              You may delete your account at any time from Security settings by confirming your password.
              Deletion takes effect immediately — your account becomes inaccessible right away — with full
              erasure of your data (capsules, beneficiaries, encryption keys, and account record) completing
              automatically within 72 hours.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">7. Limitation of Liability</h2>
            <p>
              Legate is provided "as is" without warranties of any kind. To the maximum extent permitted
              by law, Legate and its operators are not liable for any indirect, incidental, or consequential
              damages arising from your use of the service, including loss of data or failed delivery.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">8. Termination</h2>
            <p>
              We may suspend or terminate accounts that violate these Terms, subject to applicable notice
              requirements. Upon termination, your data will be handled per our Privacy Policy.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">9. Contact</h2>
            <p>
              Questions? Email{' '}
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
