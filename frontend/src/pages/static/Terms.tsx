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
          <p className="text-sm text-[#6B7280]">Last updated: June 2026</p>

          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
            <p className="text-sm text-amber-800">
              <strong>Legate is not a legal will, estate planning service, or substitute for legal counsel.</strong>
              It is a message delivery platform. Please consult a licensed attorney for official estate planning.
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
              Legate is a platform for creating encrypted personal messages ("capsules") that are automatically
              delivered to designated beneficiaries when a check-in is missed beyond a configured grace period.
              Delivery is automated and not guaranteed to occur within any specific timeframe.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">3. Account and Recovery Phrase</h2>
            <p>
              You are responsible for maintaining the security of your account password and recovery phrase.
              Legate cannot recover encrypted capsule content if your password and recovery phrase are both lost.
              You must be 18 years or older to create an account.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">4. Prohibited Content</h2>
            <p>
              You may not use Legate to store or deliver content that is illegal, defamatory, threatening,
              harassing, or that violates any applicable law. We reserve the right to terminate accounts
              that violate these terms, subject to applicable notice requirements.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">5. Delivery</h2>
            <p>
              Legate will make commercially reasonable efforts to deliver capsules when triggered.
              Delivery failures due to invalid email addresses, full inboxes, or technical issues
              will be retried up to three times over 72 hours. Legate is not liable for non-delivery
              resulting from factors outside its reasonable control.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">6. Limitation of Liability</h2>
            <p>
              Legate is provided "as is" without warranties of any kind. To the maximum extent permitted
              by law, Legate and its operators are not liable for any indirect, incidental, or consequential
              damages arising from your use of the service, including loss of data or failed delivery.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">7. Termination</h2>
            <p>
              You may delete your account at any time. We may suspend or terminate accounts that
              violate these Terms. Upon termination, your data will be handled per our Privacy Policy.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-[#0D1117] mb-3">8. Contact</h2>
            <p>
              Questions? Email <a href="mailto:legal@legate.app" className="text-[#3D4F6B] underline">legal@legate.app</a>.
            </p>
          </section>
        </div>
      </div>
    </div>
  )
}
