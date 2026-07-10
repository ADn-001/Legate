import { useNavigate } from 'react-router-dom'
import { settingsApi } from '../../api/settings'
import CapsuleEditor from '../vault/CapsuleEditor'

// This step used to be a standalone, hand-rolled capsule form that predated
// media attachments, the TipTap editor, and the requireCek()-based unlock
// flow — it drifted out of sync with the real CapsuleEditor and ended up
// with no media upload section and no way to recover from a locked vault
// (e.g. after a mobile browser reload mid-onboarding). Reusing CapsuleEditor
// directly keeps both in sync going forward.
export default function StepCapsule() {
  const navigate = useNavigate()

  const goToRecovery = async () => {
    await settingsApi.patchSettings({ setup_step: 4 }).catch(() => {})
    navigate('/setup/recovery')
  }

  return (
    <CapsuleEditor
      compact
      headingTitle="Create your first capsule"
      headingSubtitle="Write a message for your beneficiary. You can add more later."
      backTo="/setup/beneficiary"
      onSaved={goToRecovery}
      onSkip={goToRecovery}
    />
  )
}
