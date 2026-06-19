import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/auth'
import AppShell from './components/layout/AppShell'

// Pages
import Landing from './pages/Landing'
import Login from './pages/auth/Login'
import Signup from './pages/auth/Signup'
import VerifyEmail from './pages/auth/VerifyEmail'
import ForgotPassword from './pages/auth/ForgotPassword'
import ResetPassword from './pages/auth/ResetPassword'
import SetupLayout from './pages/setup/SetupLayout'
import StepCheckin from './pages/setup/StepCheckin'
import StepBeneficiary from './pages/setup/StepBeneficiary'
import StepCapsule from './pages/setup/StepCapsule'
import StepRecovery from './pages/setup/StepRecovery'
import Dashboard from './pages/vault/Dashboard'
import CapsuleList from './pages/vault/CapsuleList'
import CapsuleEditor from './pages/vault/CapsuleEditor'
import CapsuleView from './pages/vault/CapsuleView'
import Beneficiaries from './pages/people/Beneficiaries'
import Security from './pages/security/Security'
import Recover from './pages/security/Recover'
import Activity from './pages/activity/Activity'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore(s => s.isAuthenticated)
  if (!isAuthenticated) return <Navigate to="/auth/login" replace />
  return <>{children}</>
}

export function AppRouter() {
  return (
    <Router>
      <AppShell>
        <Routes>
          {/* Unauthenticated routes */}
          <Route path="/" element={<Landing />} />
          <Route path="/auth/login" element={<Login />} />
          <Route path="/auth/signup" element={<Signup />} />
          <Route path="/auth/verify-email" element={<VerifyEmail />} />
          <Route path="/auth/forgot-password" element={<ForgotPassword />} />
          <Route path="/auth/reset-password" element={<ResetPassword />} />

          {/* Setup wizard — requires auth */}
          <Route path="/setup" element={<ProtectedRoute><SetupLayout /></ProtectedRoute>}>
            <Route path="checkin" element={<StepCheckin />} />
            <Route path="beneficiary" element={<StepBeneficiary />} />
            <Route path="capsule" element={<StepCapsule />} />
            <Route path="recovery" element={<StepRecovery />} />
          </Route>

          {/* Authenticated routes */}
          <Route path="/vault" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/vault/capsules" element={<ProtectedRoute><CapsuleList /></ProtectedRoute>} />
          <Route path="/vault/capsules/new" element={<ProtectedRoute><CapsuleEditor /></ProtectedRoute>} />
          <Route path="/vault/capsules/:id/view" element={<ProtectedRoute><CapsuleView /></ProtectedRoute>} />
          <Route path="/vault/capsules/:id" element={<ProtectedRoute><CapsuleEditor /></ProtectedRoute>} />
          <Route path="/people" element={<ProtectedRoute><Beneficiaries /></ProtectedRoute>} />
          <Route path="/security" element={<ProtectedRoute><Security /></ProtectedRoute>} />
          <Route path="/recover" element={<ProtectedRoute><Recover /></ProtectedRoute>} />
          <Route path="/activity" element={<ProtectedRoute><Activity /></ProtectedRoute>} />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppShell>
    </Router>
  )
}
