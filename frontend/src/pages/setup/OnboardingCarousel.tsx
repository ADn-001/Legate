/**
 * OnboardingCarousel — T5/FR-07 (Phase 4)
 *
 * Shown once before the setup wizard, after first login.
 * 3 screens: value prop → how check-ins work → encryption promise.
 * "Skip" is always visible per FR-07.
 *
 * Seen state is persisted in localStorage (survives page reloads on the same
 * device). If the user logs in on a new device, they'll see the carousel once
 * more — acceptable given we have no server-side onboarding_seen flag.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Shield, Clock, Lock, ArrowRight, ChevronRight } from 'lucide-react'

const CAROUSEL_SEEN_KEY = 'legate_carousel_seen'

interface Slide {
  icon: React.ReactNode
  title: string
  body: string
}

const SLIDES: Slide[] = [
  {
    icon: <Shield className="w-16 h-16 text-[#3D4F6B]" />,
    title: 'Your digital legacy, secured',
    body: 'Store messages, documents, and memories that your loved ones will receive when the time comes — safely encrypted so only they can read them.',
  },
  {
    icon: <Clock className="w-16 h-16 text-[#3D4F6B]" />,
    title: 'Check-ins keep you in control',
    body: 'Legate sends you a periodic check-in. As long as you confirm it, nothing is released. Miss the window and a grace period kicks in before delivery — you\'re always in control.',
  },
  {
    icon: <Lock className="w-16 h-16 text-[#3D4F6B]" />,
    title: 'End-to-end encrypted',
    body: 'Your capsules are encrypted on your device before leaving it. Not even Legate\'s servers can read your content — only the recipients you choose.',
  },
]

export default function OnboardingCarousel() {
  const navigate = useNavigate()
  const [slide, setSlide] = useState(0)

  function proceed() {
    localStorage.setItem(CAROUSEL_SEEN_KEY, '1')
    navigate('/setup/checkin')
  }

  function next() {
    if (slide < SLIDES.length - 1) {
      setSlide(slide + 1)
    } else {
      proceed()
    }
  }

  const { icon, title, body } = SLIDES[slide]
  const isLast = slide === SLIDES.length - 1

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex flex-col items-center justify-between p-6">
      {/* Skip — always visible (FR-07) */}
      <div className="w-full max-w-md flex justify-end">
        <button
          onClick={proceed}
          className="text-sm text-[#6B7280] hover:text-[#0D1117] transition-colors py-2"
        >
          Skip
        </button>
      </div>

      {/* Slide content */}
      <div className="flex-1 flex flex-col items-center justify-center text-center max-w-md w-full gap-6 py-8">
        <div className="w-28 h-28 bg-white rounded-3xl shadow-md flex items-center justify-center">
          {icon}
        </div>

        <div>
          <h2 className="text-2xl font-bold text-[#0D1117] mb-3">{title}</h2>
          <p className="text-[#6B7280] leading-relaxed">{body}</p>
        </div>

        {/* Dots */}
        <div className="flex gap-2">
          {SLIDES.map((_, i) => (
            <button
              key={i}
              onClick={() => setSlide(i)}
              aria-label={`Go to slide ${i + 1}`}
              className={`w-2 h-2 rounded-full transition-all ${
                i === slide ? 'w-6 bg-[#3D4F6B]' : 'bg-gray-300'
              }`}
            />
          ))}
        </div>
      </div>

      {/* Next / Get started button */}
      <div className="w-full max-w-md">
        <button
          onClick={next}
          className="w-full py-4 bg-[#3D4F6B] text-white rounded-2xl font-semibold hover:bg-[#2a3851] transition-colors flex items-center justify-center gap-2"
        >
          {isLast ? (
            <>Get started <ArrowRight className="w-5 h-5" /></>
          ) : (
            <>Next <ChevronRight className="w-5 h-5" /></>
          )}
        </button>
      </div>
    </div>
  )
}
