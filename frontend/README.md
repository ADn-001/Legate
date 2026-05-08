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
- **Capacitor** - iOS/Android shell (future)

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
├── store/                # Zustand stores (auth, crypto)
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
│   └── tokenized/
│
├── components/           # Reusable components
│   ├── layout/           # AppShell, BottomNav, TopBar
│   ├── ui/               # Button, Input, Card, Modal, etc.
│   ├── capsule/          # Capsule-specific components
│   └── beneficiary/      # Beneficiary-specific components
│
├── types/                # TypeScript types
│   ├── api.ts            # API response types
│   └── crypto.ts         # Crypto-related types
│
└── utils/                # Utility functions
    ├── dates.ts          # Date formatting
    ├── audit.ts          # Event type labels
    └── storage.ts        # Supabase Storage helpers
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

### Tokenized Pages
Pages like `/checkin/confirm`, `/emergency/pause` are accessed via email links and require NO authentication. They accept a token in the URL query parameter and call unauthenticated API endpoints.

### Auto-Save & Drafts
Capsule editor has local auto-save (localStorage draft key) but does NOT encrypt or upload to server until user clicks "Save Capsule".

### Responsive Design
Mobile-first approach with Tailwind CSS. Uses bottom sheet modals on mobile for better UX. Bottom nav hidden on onboarding, auth, and tokenized pages.

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

## Capacitor (iOS/Android)

For now, the app is a PWA. Capacitor can wrap it later without code changes.

To add native features:
```bash
npm install @capacitor/core @capacitor/app @capacitor/push-notifications
```

## Next Steps

1. **Implement UI Components**: Button, Input, Card, Modal, BottomSheet, etc.
2. **Implement Pages**: Landing, Login, Signup, Setup wizard, Dashboard, etc.
3. **Implement Crypto**: PBKDF2 key derivation, AES-256-GCM encryption, BIP-39 phrase generation.
4. **Integrate API Client**: Connect all pages to API endpoints.
5. **Set up React Query**: Implement hooks for data fetching.
6. **Add Error Handling**: Proper error states and user feedback.
7. **Add Loading States**: Loading spinners and skeleton loaders.
8. **Accessibility**: Ensure ARIA labels, keyboard navigation, focus management.
9. **Testing**: Unit tests, integration tests, E2E tests.
10. **Styling**: Refine Tailwind CSS, add custom styles, ensure dark mode support.

---

*Refer to [legate_frontend_prd.md](../docs/legate_frontend_prd.md) for detailed PRD specifications.*
