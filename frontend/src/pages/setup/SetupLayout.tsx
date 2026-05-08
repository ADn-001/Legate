/**
 * Setup Wizard Layout (/setup/*)
 * - 4-step stepper with progress indicator
 * - Wrapper for setup steps
 */

import { Outlet } from 'react-router-dom'

export default function SetupLayout() {
  // TODO: Implement Setup Wizard Layout
  // - Progress indicator (step X of 4) at top
  // - Skip button (visible only on step 3)
  // - Render <Outlet /> for nested routes
  return (
    <div>
      <div>Progress Indicator</div>
      <Outlet />
    </div>
  )
}
