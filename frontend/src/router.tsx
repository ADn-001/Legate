import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'

// Pages
import Landing from './pages/Landing'
import Login from './pages/auth/Login'
import Signup from './pages/auth/Signup'
import VerifyEmail from './pages/auth/VerifyEmail'
import SetupLayout from './pages/setup/SetupLayout'
import StepCheckin from './pages/setup/StepCheckin'
import StepBeneficiary from './pages/setup/StepBeneficiary'
import StepCapsule from './pages/setup/StepCapsule'
import StepRecovery from './pages/setup/StepRecovery'
import Dashboard from './pages/vault/Dashboard'
import CapsuleList from './pages/vault/CapsuleList'
import CapsuleEditor from './pages/vault/CapsuleEditor'
import Beneficiaries from './pages/people/Beneficiaries'
import Security from './pages/security/Security'
import Activity from './pages/activity/Activity'
import CheckinConfirm from './pages/tokenized/CheckinConfirm'
import CheckinSnooze from './pages/tokenized/CheckinSnooze'
import EmergencyPause from './pages/tokenized/EmergencyPause'

export function AppRouter() {
  return (
    <Router>
      <Routes>
        {/* Unauthenticated routes */}
        <Route path="/" element={<Landing />} />
        <Route path="/auth/login" element={<Login />} />
        <Route path="/auth/signup" element={<Signup />} />
        <Route path="/auth/verify-email" element={<VerifyEmail />} />

        {/* Setup wizard */}
        <Route path="/setup" element={<SetupLayout />}>
          <Route path="checkin" element={<StepCheckin />} />
          <Route path="beneficiary" element={<StepBeneficiary />} />
          <Route path="capsule" element={<StepCapsule />} />
          <Route path="recovery" element={<StepRecovery />} />
        </Route>

        {/* Authenticated routes */}
        <Route path="/vault" element={<Dashboard />} />
        <Route path="/vault/capsules" element={<CapsuleList />} />
        <Route path="/vault/capsules/new" element={<CapsuleEditor />} />
        <Route path="/vault/capsules/:id" element={<CapsuleEditor />} />

        {/* Beneficiary management */}
        <Route path="/people" element={<Beneficiaries />} />

        {/* Security settings */}
        <Route path="/security" element={<Security />} />

        {/* Activity log */}
        <Route path="/activity" element={<Activity />} />

        {/* Tokenized (no auth required) routes */}
        <Route path="/checkin/confirm" element={<CheckinConfirm />} />
        <Route path="/checkin/snooze" element={<CheckinSnooze />} />
        <Route path="/emergency/pause" element={<EmergencyPause />} />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  )
}
