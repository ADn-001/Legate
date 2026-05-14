/**
 * Router smoke tests.
 * Verifies that the router mounts without throwing and that route
 * fallback behaviour works correctly.
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route, Navigate } from 'react-router-dom'
import Landing from '../pages/Landing'

describe('Router', () => {
  it('renders without crashing', () => {
    expect(() =>
      render(
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </MemoryRouter>,
      ),
    ).not.toThrow()
  })

  it('renders the Landing page at "/"', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </MemoryRouter>,
    )
    // Landing page contains "Legate" branding
    expect(screen.getAllByText(/Legate/i).length).toBeGreaterThan(0)
  })

  it('unknown routes redirect to "/"', () => {
    render(
      <MemoryRouter initialEntries={['/this-route-does-not-exist']}>
        <Routes>
          <Route path="/" element={<div data-testid="landing">Landing</div>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByTestId('landing')).toBeInTheDocument()
  })
})
