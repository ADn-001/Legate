import { useNavigate } from 'react-router-dom'
import { Shield, Lock, CheckCircle } from 'lucide-react'

export default function Landing() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Navigation Bar */}
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="w-8 h-8 text-[#3D4F6B]" />
            <span className="text-2xl font-bold text-[#3D4F6B]">Legate</span>
          </div>
          <div className="flex gap-4">
            <button
              onClick={() => navigate('/auth/login')}
              className="px-6 py-2 text-[#3D4F6B] hover:text-[#2a3851] font-medium"
            >
              Log In
            </button>
            <button
              onClick={() => navigate('/auth/signup')}
              className="px-6 py-2 bg-[#3D4F6B] text-white rounded-lg hover:bg-[#2a3851] font-medium"
            >
              Get Started
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <div className="max-w-7xl mx-auto px-4 py-20">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          {/* Left: Content */}
          <div className="space-y-8">
            <div>
              <h1 className="text-5xl font-bold text-[#0D1117] mb-4">
                Plan your digital legacy securely
              </h1>
              <p className="text-xl text-[#6B7280] mb-6">
                Your instructions, delivered when it matters. Create encrypted messages and secure instructions for your loved ones.
              </p>
            </div>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4">
              <button
                onClick={() => navigate('/auth/signup')}
                className="px-8 py-4 bg-[#3D4F6B] text-white rounded-2xl font-semibold hover:bg-[#2a3851] transition-colors text-center"
              >
                Get Started
              </button>
              <button className="px-8 py-4 bg-gray-100 text-gray-800 rounded-2xl font-semibold hover:bg-gray-200 transition-colors text-center">
                Learn More
              </button>
            </div>
          </div>

          {/* Right: Hero Image */}
          <div className="relative">
            <div className="bg-gradient-to-br from-[#3D4F6B] to-slate-700 rounded-3xl p-12 h-96 flex items-center justify-center text-white relative overflow-hidden">
              <div className="absolute top-4 left-4 bg-[#22C55E] text-white px-4 py-2 rounded-full text-sm font-semibold flex items-center gap-2">
                <div className="w-2 h-2 bg-white rounded-full"></div>
                VAULT STATUS: ACTIVE
              </div>
              <div className="text-center">
                <Lock className="w-24 h-24 mx-auto mb-4 opacity-80" />
                <p className="text-lg font-semibold">End-to-End Encrypted</p>
              </div>
            </div>
          </div>
        </div>

        {/* Features Section */}
        <div className="mt-24">
          <h2 className="text-4xl font-bold text-[#0D1117] text-center mb-16">
            Why Choose Legate?
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {/* Feature 1 */}
            <div className="bg-white rounded-2xl p-8 shadow-md hover:shadow-lg transition-shadow">
              <div className="bg-blue-100 w-14 h-14 rounded-lg flex items-center justify-center mb-4">
                <Lock className="w-7 h-7 text-[#3D4F6B]" />
              </div>
              <h3 className="text-xl font-bold text-[#0D1117] mb-3">
                End-to-End Encrypted
              </h3>
              <p className="text-[#6B7280]">
                Your capsules are encrypted client-side. Only your designated beneficiaries can access them.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="bg-white rounded-2xl p-8 shadow-md hover:shadow-lg transition-shadow">
              <div className="bg-blue-100 w-14 h-14 rounded-lg flex items-center justify-center mb-4">
                <CheckCircle className="w-7 h-7 text-[#3D4F6B]" />
              </div>
              <h3 className="text-xl font-bold text-[#0D1117] mb-3">
                You Stay in Control
              </h3>
              <p className="text-[#6B7280]">
                Set check-in intervals. Only if you go inactive do your capsules get delivered.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="bg-white rounded-2xl p-8 shadow-md hover:shadow-lg transition-shadow">
              <div className="bg-blue-100 w-14 h-14 rounded-lg flex items-center justify-center mb-4">
                <Shield className="w-7 h-7 text-[#3D4F6B]" />
              </div>
              <h3 className="text-xl font-bold text-[#0D1117] mb-3">
                Secure & Reliable
              </h3>
              <p className="text-[#6B7280]">
                Military-grade encryption, secure recovery phrases, and emergency contact protocols.
              </p>
            </div>
          </div>
        </div>

        {/* How It Works */}
        <div className="mt-24 bg-white rounded-2xl p-12 shadow-md">
          <h2 className="text-4xl font-bold text-[#0D1117] text-center mb-12">
            How It Works
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div className="text-center">
              <div className="bg-[#3D4F6B] text-white w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4 text-lg font-bold">
                1
              </div>
              <h4 className="font-bold text-[#0D1117] mb-2">Create Capsules</h4>
              <p className="text-[#6B7280] text-sm">
                Write encrypted messages and instructions for your loved ones
              </p>
            </div>

            <div className="text-center">
              <div className="bg-[#3D4F6B] text-white w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4 text-lg font-bold">
                2
              </div>
              <h4 className="font-bold text-[#0D1117] mb-2">Assign Beneficiaries</h4>
              <p className="text-[#6B7280] text-sm">
                Choose who receives each capsule and their relationship
              </p>
            </div>

            <div className="text-center">
              <div className="bg-[#3D4F6B] text-white w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4 text-lg font-bold">
                3
              </div>
              <h4 className="font-bold text-[#0D1117] mb-2">Stay Active</h4>
              <p className="text-[#6B7280] text-sm">
                Confirm check-ins regularly. No action needed while active
              </p>
            </div>

            <div className="text-center">
              <div className="bg-[#3D4F6B] text-white w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4 text-lg font-bold">
                4
              </div>
              <h4 className="font-bold text-[#0D1117] mb-2">Auto-Delivery</h4>
              <p className="text-[#6B7280] text-sm">
                If inactive, capsules deliver to beneficiaries automatically
              </p>
            </div>
          </div>
        </div>

        {/* CTA Banner */}
        <div className="mt-24 bg-gradient-to-r from-[#3D4F6B] to-slate-700 rounded-2xl p-12 text-center text-white">
          <h2 className="text-3xl font-bold mb-4">Ready to Secure Your Legacy?</h2>
          <p className="text-lg mb-8 opacity-90">
            Join thousands creating their digital legacies today
          </p>
          <button
            onClick={() => navigate('/auth/signup')}
            className="px-10 py-4 bg-white text-[#3D4F6B] rounded-2xl font-semibold hover:bg-gray-100 transition-colors"
          >
            Get Started Now
          </button>
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-24">
        <div className="max-w-7xl mx-auto px-4 py-12">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Shield className="w-6 h-6 text-[#3D4F6B]" />
                <span className="text-lg font-bold text-[#3D4F6B]">Legate</span>
              </div>
              <p className="text-[#6B7280] text-sm">
                Your digital legacy, secured.
              </p>
            </div>
            <div>
              <h4 className="font-bold text-[#0D1117] mb-4">Product</h4>
              <ul className="space-y-2 text-[#6B7280] text-sm">
                <li><a href="#" className="hover:text-[#3D4F6B]">Features</a></li>
                <li><a href="#" className="hover:text-[#3D4F6B]">Security</a></li>
                <li><a href="#" className="hover:text-[#3D4F6B]">Pricing</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-bold text-[#0D1117] mb-4">Company</h4>
              <ul className="space-y-2 text-[#6B7280] text-sm">
                <li><a href="#" className="hover:text-[#3D4F6B]">About</a></li>
                <li><a href="#" className="hover:text-[#3D4F6B]">Blog</a></li>
                <li><a href="#" className="hover:text-[#3D4F6B]">Contact</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-bold text-[#0D1117] mb-4">Legal</h4>
              <ul className="space-y-2 text-[#6B7280] text-sm">
                <li><a href="#" className="hover:text-[#3D4F6B]">Privacy</a></li>
                <li><a href="#" className="hover:text-[#3D4F6B]">Terms</a></li>
                <li><a href="#" className="hover:text-[#3D4F6B]">Security</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-200 pt-8 text-center text-[#6B7280] text-sm">
            <p>&copy; 2026 Legate. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
