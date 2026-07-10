# Legate Frontend

React + TypeScript + Vite + Tailwind CSS frontend for the Legate digital legacy app.

## Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **React Router v6** - Routing
- **Zustand** - State management (auth, crypto)
- **React Query** - Server state management
- **Axios** - HTTP client
- **Web Crypto API** - Client-side encryption
- **BIP-39** - Recovery phrase generation

The app is a PWA (installable via the browser's "Add to Home Screen"). A native
shell such as Capacitor was scoped out — the PWA already provides an app-like
experience. `@capacitor/core` remains listed in `package.json` but is unused.

## Project Structure

```
src/
├── main.tsx              # Entry point
├── App.tsx               # Root component
├── router.tsx            # Route definitions
├── index.css             # Global styles (Tailwind)
│
├── api/                  # API endpoints (Axios)
├── crypto/               # Encryption/crypto logic
├── store/                # Zustand stores (auth, crypto, unlock, pendingAuth)
├── hooks/                # React hooks (useAuth, useCapsules, etc.)
│
├── pages/                # Page components (organized by route)
│   ├── Landing.tsx
│   ├── auth/
│   ├── setup/
│   ├── vault/
│   ├── people/
│   ├── security/
│   ├── activity/
│   └── static/           # Privacy, Terms, HowItWorks (public, no auth)
│
├── components/           # Reusable components
│   ├── layout/           # AppShell, BottomNav, TopBar
│   ├── ui/                # Button, Input, Card, Modal, etc.
│   ├── auth/              # UnlockModal
│   ├── capsule/           # Capsule-specific components
│   └── beneficiary/       # Beneficiary-specific components
│
├── types/                # TypeScript types
│   ├── api.ts            # API response types
│   └── crypto.ts         # Crypto-related types
│
├── utils/                # Utility functions
│   ├── dates.ts           # Date formatting
│   ├── audit.ts           # Event type labels
│   ├── storage.ts         # Supabase Storage helpers
│   ├── media-upload.ts    # Encrypt → upload → thumbnail → confirm pipeline
│   └── outbox.ts          # Offline-queued action retry
│
└── test/                 # Vitest unit/component tests
```

## Key Implementation Notes

### Encryption & Security
- **CEK (Content Encryption Key)**: Held in-memory only. Never persisted to localStorage, sessionStorage, or IndexedDB.
- **On Signup**: Derive wrapping key via PBKDF2, generate CEK, encrypt CEK, send to API.
- **On Login**: Re-derive wrapping key from password, decrypt CEK, hold in memory.
- **Capsule Content**: Encrypted client-side before upload to Supabase Storage. API only receives metadata.
- **Recovery Phrase**: BIP-39 24-word phrase generated client-side, never sent to server.

### State Management
- **Auth Store** (Zustand): User info, tokens, login/logout actions.
- **Crypto Store** (Zustand): CEK (in-memory only), set/clear methods.
- **Server State** (React Query): Capsules, beneficiaries, settings, audit logs.

### Authentication Flow
1. User signs up → derives wrapping key, generates CEK, sends encrypted CEK to API.
2. User receives email verification OTP → verifies email → receives JWT tokens.
3. On login → retrieves encrypted CEK from API, re-derives wrapping key, decrypts CEK into memory.
4. Token refresh handled automatically by Axios interceptor.

### Check-In Email Links
`GET /checkin/confirm`, `GET /checkin/snooze`, and `GET /checkin/emergency/pause`
are backend endpoints, not frontend routes — clicking a link in a check-in or
grace-period email hits the FastAPI backend directly, which validates the
single-use token and returns a small standalone HTML confirmation/error page
(see `backend/app/api/checkin.py`). The frontend never renders these; there is
no corresponding `pages/` folder for them.

### Auto-Save & Drafts
The capsule editor auto-saves to `localStorage` (keyed `draft_capsule_<id|new>`)
while the vault is unlocked. Drafts are encrypted at rest with the in-memory CEK
before being written (see `CapsuleEditor.tsx`), and are never uploaded to the
server until the user clicks "Save Capsule".

### Responsive Design
Mobile-first approach with Tailwind CSS. Uses bottom sheet modals on mobile for better UX. Bottom nav hidden on onboarding and auth pages.

## Setup & Development

### Prerequisites
- Node.js 18+
- npm or yarn

### Installation
```bash
cd frontend
npm install
```

### Environment Variables
Copy `.env.example` to `.env` and fill in your values:
```bash
cp .env.example .env
```

### Development Server
```bash
npm run dev
```

Server runs on http://localhost:5173

### Build for Production
```bash
npm run build
```

Output goes to `dist/`

### Type Checking
```bash
npm run type-check
```

### Linting
```bash
npm run lint
```

## API Integration

All API calls go through the Axios client configured in `src/api/client.ts`:
- Automatic token refresh on 401
- Request/response interceptors for headers
- Base URL from environment variable

---

*Refer to [Legate_PRD_v3_0.md](../implementation/Legate_PRD_v3_0.md) for the full product spec, and
[Legate_Testers_Guide.md](../implementation/Legate_Testers_Guide.md) for a feature-by-feature testing walkthrough.*
