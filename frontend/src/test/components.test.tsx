/**
 * Component smoke tests.
 * Renders each component and verifies it mounts without throwing.
 * We use MemoryRouter to satisfy react-router-dom hooks in pages.
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

// Layout components
import AppShell from '../components/layout/AppShell'
import TopBar from '../components/layout/TopBar'
import BottomNav from '../components/layout/BottomNav'

// UI components
import Badge from '../components/ui/Badge'

// Pages (implemented)
import Landing from '../pages/Landing'
import Login from '../pages/auth/Login'
import Signup from '../pages/auth/Signup'

// ---------------------------------------------------------------------------
// AppShell
// ---------------------------------------------------------------------------
describe('AppShell', () => {
  it('mounts without throwing', () => {
    expect(() => render(<AppShell />)).not.toThrow()
  })

  it('renders placeholder text', () => {
    render(<AppShell />)
    expect(screen.getByText(/App Shell/i)).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// TopBar
// ---------------------------------------------------------------------------
describe('TopBar', () => {
  it('mounts without throwing', () => {
    expect(() => render(<TopBar />)).not.toThrow()
  })

  it('renders a header element', () => {
    render(<TopBar />)
    expect(document.querySelector('header')).not.toBeNull()
  })
})

// ---------------------------------------------------------------------------
// BottomNav
// ---------------------------------------------------------------------------
describe('BottomNav', () => {
  it('mounts without throwing', () => {
    expect(() => render(<BottomNav />)).not.toThrow()
  })

  it('renders a nav element', () => {
    render(<BottomNav />)
    expect(document.querySelector('nav')).not.toBeNull()
  })
})

// ---------------------------------------------------------------------------
// Badge — all variants
// ---------------------------------------------------------------------------
describe('Badge', () => {
  it('renders with default variant', () => {
    render(<Badge>Draft</Badge>)
    expect(screen.getByText('Draft')).toBeInTheDocument()
  })

  it('renders with success variant', () => {
    render(<Badge variant="success">Active</Badge>)
    expect(screen.getByText('Active')).toBeInTheDocument()
  })

  it('renders with warning variant', () => {
    render(<Badge variant="warning">Pending</Badge>)
    expect(screen.getByText('Pending')).toBeInTheDocument()
  })

  it('renders with error variant', () => {
    render(<Badge variant="error">Deleted</Badge>)
    expect(screen.getByText('Deleted')).toBeInTheDocument()
  })

  it('renders children as text content', () => {
    render(<Badge>Custom Label</Badge>)
    expect(screen.getByText('Custom Label')).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// Landing page
// ---------------------------------------------------------------------------
describe('Landing', () => {
  it('mounts without throwing', () => {
    expect(() =>
      render(
        <MemoryRouter>
          <Landing />
        </MemoryRouter>,
      ),
    ).not.toThrow()
  })

  it('renders Legate branding', () => {
    render(
      <MemoryRouter>
        <Landing />
      </MemoryRouter>,
    )
    expect(screen.getAllByText(/Legate/i).length).toBeGreaterThan(0)
  })

  it('renders Log In button', () => {
    render(
      <MemoryRouter>
        <Landing />
      </MemoryRouter>,
    )
    expect(screen.getByText(/Log In/i)).toBeInTheDocument()
  })

  it('renders Get Started button', () => {
    render(
      <MemoryRouter>
        <Landing />
      </MemoryRouter>,
    )
    expect(screen.getAllByText(/Get Started/i).length).toBeGreaterThan(0)
  })
})

// ---------------------------------------------------------------------------
// Login page
// ---------------------------------------------------------------------------
describe('Login', () => {
  it('mounts without throwing', () => {
    expect(() =>
      render(
        <MemoryRouter>
          <Login />
        </MemoryRouter>,
      ),
    ).not.toThrow()
  })

  it('renders email input', () => {
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    )
    expect(screen.getByPlaceholderText(/you@example.com/i)).toBeInTheDocument()
  })

  it('renders sign in heading', () => {
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    )
    expect(screen.getByText(/Welcome Back/i)).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// Signup page
// ---------------------------------------------------------------------------
describe('Signup', () => {
  it('mounts without throwing', () => {
    expect(() =>
      render(
        <MemoryRouter>
          <Signup />
        </MemoryRouter>,
      ),
    ).not.toThrow()
  })

  it('renders Create Your Account heading', () => {
    render(
      <MemoryRouter>
        <Signup />
      </MemoryRouter>,
    )
    expect(screen.getByText(/Create Your Account/i)).toBeInTheDocument()
  })

  it('renders email and password inputs', () => {
    render(
      <MemoryRouter>
        <Signup />
      </MemoryRouter>,
    )
    expect(screen.getByPlaceholderText(/you@example.com/i)).toBeInTheDocument()
  })
})
