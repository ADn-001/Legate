# Legate — Product Requirements Document v2.0

**Document version:** 2.0 — Revised architecture  
**Status:** Draft  
**Date:** May 2026  
**Author:** Product Team  
**Platforms:** Web (desktop), Installable PWA, Capacitor (iOS/Android)  
**Confidentiality:** Internal use only

---

## Revision History

| Version | Date | Author | Change Summary |
|---------|------|--------|----------------|
| 1.0 | March 2026 | Product Team | Initial draft — decentralized storage architecture |
| 2.0 | May 2026 | Product Team | Simplified storage: Supabase replaces shard/node network. Dropped community seeders, Shamir's Secret Sharing, and monetisation tiers. Added PWA + Capacitor targets. Hybrid encryption model. |

---

## 1. Executive Summary

Legate is a digital estate planning application that enables users to compose personal messages — text, photos, and video — addressed to nominated loved ones, to be delivered automatically after the user dies or becomes incapacitated.

The product operates on a check-in mechanism. Users receive a periodic email and confirm they are well with a single click. Sustained non-response beyond a configurable grace period triggers message delivery to nominated beneficiaries.

Legate is delivered as a Progressive Web App (PWA) installable on desktop and mobile, with a native mobile wrapper via Capacitor for iOS and Android. This makes the product platform-agnostic by design — a single codebase runs across all supported environments.

Content is encrypted client-side before transmission using the Web Crypto API (AES-256-GCM). Encrypted content and a server-encrypted key are stored in Supabase. Metadata is managed server-side. No plaintext content is ever stored or transmitted unencrypted.

---

## 2. Goals & Non-Goals

### 2.1 Goals

**Product goals**
- Deliver a setup experience completable in under 7 minutes by a non-technical user
- Achieve a check-in false-trigger rate of 0.00%
- Achieve a delivery reliability rate of 99.9%+ when legitimately triggered
- Ensure no Legate employee can read any user's message content at any time
- Support text, photo, and video content across all supported platforms
- Be fully installable and partially functional offline as a PWA

**Technical goals**
- Single deployable codebase across web, iOS, and Android via PWA + Capacitor
- Platform-agnostic deployment via Docker Compose
- Auto-generated API documentation via FastAPI/Swagger
- GDPR-compliant data handling with right-to-erasure support

### 2.2 Non-Goals (v1)

- Legate is not a password manager
- Legate is not a legal will
- Legate will not integrate with financial institutions or government registries
- Legate will not support group or collaborative wills
- Legate will not provide AI-assisted message drafting
- Legate has no monetisation tiers — all features available to all users in v1
- Legate does not use a community seeder or distributed node network

---

## 3. Stakeholders & Personas

### 3.1 Internal Stakeholders

| Role | Responsibility |
|------|---------------|
| Product Manager | Owns this document; arbitrates scope decisions |
| Engineering Lead | Validates technical feasibility; owns architecture decisions |
| Design Lead | Owns UX flows and visual system |
| Security Architect | Owns encryption and key management |
| Legal Counsel | Reviews compliance requirements |

### 3.2 User Personas

**Persona A — Tariq, 44, software engineer**
Father of two with crypto holdings, a YouTube channel, and 15 years of digital assets. Wants to leave clear instructions for his wife. Values architectural transparency. Will read the technical details section.

**Persona B — Maryam, 61, retired teacher**
Not highly technical. Wants to leave video messages for grandchildren at life milestones. Needs simple setup with no jargon and clear confirmation that things are working.

**Persona C — Daniyar, 35, freelance digital nomad**
Multiple online business accounts and a large social following. Needs highly configurable check-in scheduling and the ability to snooze without opening the app. Travels constantly.

---

## 4. Assumptions & Constraints

### 4.1 Assumptions

- Users have access to at least one reliable email address checked as frequently as their check-in interval
- Beneficiaries do not need the app installed — delivery is via email
- The check-in confirmation link must work without requiring app login
- Users understand Legate is not a legal instrument

### 4.2 Constraints

- **Technical:** Client-side encryption means Legate cannot perform server-side search of capsule content. Search must be client-side against decrypted data.
- **Technical:** The Web Crypto API key is derived from the user's password via PBKDF2. Key loss (forgotten password with no recovery phrase backup) means permanent content loss.
- **Technical:** Capacitor wraps the PWA in a native shell. All Web Crypto API calls work identically in this context.
- **Legal:** Legate cannot legally declare a user dead. The trigger is inability to respond, not death. All copy must reflect this precisely.
- **Legal:** GDPR compliance required from launch — right to erasure must propagate to Supabase Storage and the database within 72 hours.
- **Storage:** Supabase Storage is used for encrypted media files. Supabase PostgreSQL is used for all structured data. Supabase handles encryption at rest for metadata; content is additionally encrypted client-side.

---

## 5. System Architecture Overview

### 5.1 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + Tailwind CSS |
| PWA | Workbox (service worker, offline cache, install manifest) |
| Mobile wrapper | Capacitor (iOS + Android native shell over PWA) |
| Client encryption | Web Crypto API — AES-256-GCM |
| Backend | FastAPI (Python) |
| Task queue | Celery + Redis |
| Database | Supabase (PostgreSQL) via SQLAlchemy + Alembic |
| File storage | Supabase Storage |
| Authentication | JWT (access + refresh tokens), Supabase Auth |
| Email | Resend (primary) |
| Deployment | Docker Compose |
| API docs | FastAPI auto-generated Swagger UI at `/docs` |

### 5.2 Component Overview

| Component | Description | Trust Boundary |
|-----------|-------------|----------------|
| PWA / Capacitor app | Primary user interface. Handles all content creation, client-side encryption, and upload. The plaintext content key never leaves this layer. | Fully trusted — user's device |
| FastAPI backend | Handles authentication, check-in scheduling, grace period logic, delivery triggering. Stores encrypted key blob. Never sees plaintext content. | Trusted, audited |
| Celery worker | Processes scheduled tasks: check-in email dispatch, grace period monitoring, delivery triggering, post-delivery cleanup. | Trusted, internal |
| Redis | Message broker for Celery. Also stores JWT blacklist and rate limit counters. | Internal only |
| Supabase PostgreSQL | Stores all structured data — users, capsules (metadata only), beneficiaries, check-in schedules, audit logs. Row Level Security enforced. | Trusted, encrypted at rest |
| Supabase Storage | Stores AES-256-GCM encrypted content blobs and media files. Supabase never holds the plaintext key. | Trusted, double-encrypted |
| Resend | Transactional email — check-in links, reminders, delivery emails. Receives rendered delivery content at trigger time only. | Third party |
| Web companion (stateless) | Hosts check-in confirm, snooze, and emergency pause web views. Token-authenticated, no login required. | Trusted, stateless |

### 5.3 Encryption Architecture

1. At account creation, a 256-bit content encryption key (CEK) is generated using `crypto.getRandomValues()` in the browser.
2. The CEK is encrypted using AES-256-GCM with a key derived from the user's password via PBKDF2 (100,000 iterations, SHA-256, random 16-byte salt).
3. The encrypted CEK blob (ciphertext + IV + salt) is stored in Supabase. The server never sees the raw CEK.
4. When creating a capsule, content is encrypted in the browser using the CEK before upload.
5. At delivery time, the FastAPI backend retrieves the encrypted CEK blob and the encrypted content from Supabase. The delivery service decrypts using the stored key derivation parameters. This is the single moment where plaintext is reconstructed — it occurs in an isolated delivery worker and plaintext is not persisted.
6. A 24-word BIP-39 recovery phrase is generated at setup as a backup decryption path if the user's password is lost.

### 5.4 Data Flow — Content Creation to Delivery

1. User writes a capsule on their device.
2. Web Crypto API encrypts content with CEK. Encrypted blob uploaded to Supabase Storage.
3. Capsule metadata (title, beneficiary, status) stored in Supabase PostgreSQL — never plaintext content.
4. Celery beat dispatches check-in emails on schedule via Resend.
5. User confirms via email link. FastAPI resets the check-in timer.
6. On grace period expiry: Celery triggers delivery worker.
7. Delivery worker retrieves encrypted content + encrypted CEK from Supabase, decrypts, renders delivery email, sends via Resend.
8. Plaintext is discarded immediately after send. Account enters memorial state.
9. All content purged from Supabase Storage within 72 hours of confirmed delivery.

### 5.5 Deployment Architecture

The full application is containerised via Docker Compose with the following services:

- `api` — FastAPI application server (Uvicorn)
- `worker` — Celery worker for background tasks
- `beat` — Celery beat scheduler for periodic tasks
- `redis` — Redis broker and cache
- `nginx` — Reverse proxy + static PWA file serving

Supabase is consumed as a managed cloud service (not self-hosted). The Docker Compose stack can be deployed to any cloud provider or on-premises Linux host, satisfying the platform/OS-agnostic requirement.

Frontend PWA is deployed independently to Vercel or Netlify (static build). Capacitor builds are submitted to App Store and Play Store.

---

## 6. Functional Requirements

Priority notation: **P0** = must have for v1, **P1** = ships shortly after, **P2** = future roadmap.

### 6.1 Authentication & Account Management

| ID | Priority | Requirement |
|----|----------|-------------|
| FR-01 | P0 | Users create an account with email and password (min 12 chars, 1 number, 1 special character). |
| FR-02 | P0 | Email verification via 6-digit OTP before app access. |
| FR-03 | P0 | Password reset via email magic link, expires 30 minutes. |
| FR-04 | P1 | Biometric authentication (Face ID, Touch ID, fingerprint) via Capacitor Biometrics plugin on mobile. Falls back to password. |
| FR-05 | P0 | Account deletion permanently destroys all user data. User must type DELETE and enter password. GDPR right to erasure — all Supabase Storage objects and database rows purged within 72 hours. |
| FR-06 | P1 | Change registered email with re-verification of new address. |

### 6.2 Onboarding & Setup Wizard

| ID | Priority | Requirement |
|----|----------|-------------|
| FR-07 | P0 | 3-screen onboarding carousel on first launch. Skip always visible. |
| FR-08 | P0 | 4-step guided wizard: (1) check-in configuration, (2) first beneficiary, (3) first capsule (skippable), (4) backup key display. |
| FR-09 | P0 | Wizard is resumable — returns to last incomplete step on next open. |
| FR-10 | P0 | Backup key step displays 24-word BIP-39 recovery phrase. User must tap confirmation checkbox. Copy and export-as-PDF actions available. |

### 6.3 Check-in System

| ID | Priority | Requirement |
|----|----------|-------------|
| FR-11 | P0 | Configurable check-in interval: 7, 14, 30, 60 days, or custom (7–365 days). |
| FR-12 | P0 | Configurable grace period: 3, 7, 14, or 30 days. Trigger fires at grace period end if unconfirmed. |
| FR-13 | P0 | Check-in email contains a single-click confirmation link requiring no app login. Clicking resets timer and shows confirmation page. |
| FR-14 | P0 | Check-in email contains snooze option: +7, +14, or +30 days. Maximum 2 snoozes per cycle. Snooze page shows remaining allowance. |
| FR-15 | P0 | Confirmation and snooze links expire 7 days after dispatch. Expired links show clear message directing user to app. |
| FR-16 | P0 | During grace period, escalating reminder emails sent at configurable intervals (default: day 3 and day 7 of grace period). |
| FR-17 | P1 | Push notification sent same day as check-in email via Capacitor Push Notifications plugin. Deep-links to one-tap confirm screen. |
| FR-18 | P0 | Check-in interval and grace period configurable from settings at any time. Reducing grace period shows confirmation warning. |

### 6.4 Beneficiary Management

| ID | Priority | Requirement |
|----|----------|-------------|
| FR-19 | P0 | Add beneficiary: full name (required), email (required), relationship category (optional). |
| FR-20 | P0 | Nomination email sent to beneficiary on add — does not reveal content, capsule counts, or account details. |
| FR-21 | P0 | Edit beneficiary name and email. Email change re-sends nomination to new address. |
| FR-22 | P0 | Remove beneficiary with confirmation. Warns linked capsules will be unassigned. Removal notification sent to beneficiary. |
| FR-23 | P1 | One beneficiary may be designated emergency contact. Receives pre-trigger confirmation email at grace period end with 48 hours to pause delivery. |
| FR-24 | P1 | Emergency contact pause available via single-click link. Extends grace period by 7 days. Maximum 2 pauses per trigger event. |

### 6.5 Message Capsules

| ID | Priority | Requirement |
|----|----------|-------------|
| FR-25 | P0 | Create text capsule for specific beneficiary. Rich text editor (bold, italic, unordered lists). Max 10,000 characters. |
| FR-26 | P0 | Capsule content autosaves locally every 30 seconds. Save status indicator visible. Content not lost if app closed mid-edit. |
| FR-27 | P0 | Attach up to 20 photos per capsule (JPEG, PNG, HEIC, max 10MB each). Thumbnail grid shown in editor. |
| FR-28 | P1 | Attach one video per capsule — recorded in-app (max 5 min) or uploaded from device (max 500MB, MP4/MOV). Thumbnail auto-generated. |
| FR-29 | P1 | Multiple capsules per beneficiary with editable titles. Drag-and-drop reordering determines delivery order. |
| FR-30 | P1 | Preview mode renders capsule exactly as beneficiary will receive it. "Preview" banner clearly identifies non-live state. |
| FR-31 | P0 | Capsule deletion triggers confirmation dialog. Content purged from Supabase Storage within 24 hours. "Pending deletion" badge until purge confirmed. |

### 6.6 Storage & Encryption

| ID | Priority | Requirement |
|----|----------|-------------|
| FR-32 | P0 | All capsule content encrypted client-side using Web Crypto API (AES-256-GCM) before upload to Supabase Storage. |
| FR-33 | P0 | Content encryption key (CEK) derived from user password via PBKDF2. Encrypted CEK blob stored in Supabase. Server never holds raw CEK. |
| FR-34 | P0 | Metadata (titles, beneficiary assignments, schedule config) stored in Supabase PostgreSQL with Supabase encryption at rest. |
| FR-35 | P0 | 24-word BIP-39 recovery phrase generated at account creation as backup decryption path. Shown once at setup, re-accessible with password confirmation. |
| FR-36 | P0 | Storage usage shown per capsule with progress bar against a defined storage limit. |
| FR-37 | P0 | PWA supports offline viewing of previously loaded capsule metadata. Edits to drafts cached locally and synced on reconnection. |

### 6.7 Delivery Engine

| ID | Priority | Requirement |
|----|----------|-------------|
| FR-38 | P0 | On trigger, Celery delivery worker retrieves encrypted content and encrypted CEK from Supabase, decrypts in isolated worker process, renders delivery email, sends via Resend. |
| FR-39 | P0 | Each beneficiary receives email with all assigned capsules in configured order. Text inline, photos as embedded gallery, video as secure download link (valid 30 days). |
| FR-40 | P0 | Delivery email includes plain-language explanation of Legate and why the beneficiary is receiving this. Non-alarming tone. |
| FR-41 | P0 | All capsule content purged from Supabase Storage within 72 hours of confirmed delivery. Account enters read-only memorial state. |
| FR-42 | P0 | Delivery failures retried up to 3 times at 1-hour intervals. Internal alert raised on persistent failure. |
| FR-43 | P1 | Delivery confirmation sent to emergency contact (if designated) once all beneficiary emails dispatched. |

### 6.8 Dashboard & Transparency

| ID | Priority | Requirement |
|----|----------|-------------|
| FR-44 | P0 | Dashboard displays check-in status card: current status (active/due soon/overdue), last confirmed date, next due date, days remaining. |
| FR-45 | P0 | "How Legate works" screen explains full product flow in plain language. Secondary technical details section for technical users. |
| FR-46 | P0 | Settings screen shows current storage usage, option to view/copy backup key (password required). |

---

## 7. Non-Functional Requirements

### 7.1 Performance

| ID | Priority | Requirement |
|----|----------|-------------|
| NFR-01 | P0 | PWA cold launch within 2.5 seconds on mid-range device on 4G. |
| NFR-02 | P0 | Check-in confirmation processes and shows confirmation page within 1.5 seconds of click. |
| NFR-03 | P0 | Capsule save and encryption completes within 5 seconds for text-only. Photo upload and encryption up to 30 seconds with visible progress. |
| NFR-04 | P1 | App remains usable offline for viewing existing capsule metadata and editing drafts. Sync on reconnect. |

### 7.2 Reliability & Availability

| ID | Priority | Requirement |
|----|----------|-------------|
| NFR-05 | P0 | FastAPI backend and Celery scheduler maintain 99.9% monthly uptime. Downtime communicated via in-app banner and email. |
| NFR-06 | P0 | Check-in emails dispatched within 1-hour window of scheduled time. |
| NFR-07 | P0 | Delivery pipeline guarantees at-least-once delivery per beneficiary. |

### 7.3 Security

| ID | Priority | Requirement |
|----|----------|-------------|
| NFR-08 | P0 | All data in transit encrypted using TLS 1.3. Older versions rejected. |
| NFR-09 | P0 | Delivery worker process does not log plaintext content. Plaintext discarded immediately post-send. |
| NFR-10 | P0 | All API endpoints require authentication. Rate limiting: 10 req/min unauthenticated, 100 req/min authenticated. |
| NFR-11 | P0 | App passes independent penetration test before public launch. Critical/high findings remediated. |
| NFR-12 | P0 | Check-in tokens single-use, expire after 7 days. Invalidated immediately on use. Redis used for token blacklist. |
| NFR-13 | P1 | Certificate pinning on Capacitor mobile builds. |
| NFR-14 | P0 | Supabase Row Level Security policies enforced — users can only access their own rows. |

### 7.4 Privacy & Compliance

| ID | Priority | Requirement |
|----|----------|-------------|
| NFR-15 | P0 | Published Privacy Policy and Terms of Service accessible from app before launch. |
| NFR-16 | P0 | GDPR data subject rights supported: access, rectification, erasure, restriction, portability, objection. Erasure propagates to Supabase within 72 hours. |
| NFR-17 | P0 | Data breach notification process in place. Users notified within 72 hours per GDPR Article 33. |
| NFR-18 | P0 | No third-party ad network analytics SDKs. First-party aggregated analytics only. |

### 7.5 Accessibility

| ID | Priority | Requirement |
|----|----------|-------------|
| NFR-19 | P0 | WCAG 2.1 AA contrast (4.5:1 body, 3:1 large text). Color never sole state indicator. |
| NFR-20 | P0 | Minimum 44×44pt touch targets. Icon-only controls have accessible labels. |
| NFR-21 | P0 | Fully navigable via screen readers. All meaningful content has ARIA labels and roles. |
| NFR-22 | P0 | All animations respect Reduce Motion setting. |

### 7.6 PWA Requirements

| ID | Priority | Requirement |
|----|----------|-------------|
| NFR-23 | P0 | App manifest defines name, icons (192px, 512px), theme color, display: standalone. |
| NFR-24 | P0 | Service worker (Workbox) caches shell, static assets, and previously loaded capsule metadata for offline access. |
| NFR-25 | P0 | App passes Lighthouse PWA audit with score ≥ 90. |
| NFR-26 | P0 | Installable on iOS (Safari Add to Home Screen) and Android (Chrome install prompt). |

---

## 8. Risks & Mitigations

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R-01 | False trigger — messages delivered while user is alive | Medium | High | Grace period + escalating reminders + emergency contact pause. Multi-layer safeguard. |
| R-02 | User loses password and recovery phrase — permanent content loss | Medium | High | Prominent BIP-39 key export at setup. Annual reminder. Re-display in settings with password auth. |
| R-03 | Delivery worker compromised — plaintext exposed at delivery | Low | Critical | Worker process isolation. No plaintext logging. Independent security audit. Incident response plan. |
| R-04 | Resend deliverability failure — check-in or delivery emails not received | Low | High | Retry queue (3 attempts). Push notification as redundant check-in channel. Secondary email provider fallback plan. |
| R-05 | Supabase outage — app unavailable | Low | High | PWA offline mode for read access. Celery retry queue for scheduled tasks. Multi-region Supabase project. |
| R-06 | GDPR audit on right-to-erasure compliance | Low | High | Erasure propagation tested pre-launch. Documented erasure process. DPO engaged. |
| R-07 | Legal challenge from platforms re: ToS facilitation | Medium | Medium | Legate stores instructions, not credentials. Legal review of copy pre-launch. |

---

## 9. Open Questions

| ID | Question | Owner | Target |
|----|---------|-------|--------|
| OQ-01 | Which cloud provider hosts the Docker Compose stack for production? | Engineering | Pre-beta |
| OQ-02 | Exact wording of beneficiary nomination email — needs legal review | Legal | Alpha |
| OQ-03 | Exact wording of delivery email — non-definitive tone | Legal | Beta |
| OQ-04 | Data residency policy — EU users may require EU-region Supabase project | Legal + Engineering | Beta |
| OQ-05 | What happens when registered email bounces permanently? Manual recovery process needed. | Product | v1.0 |
| OQ-06 | Dark mode — in scope for v1.0? | Design | Immediately |

---

## 10. Launch Acceptance Criteria

### Functional gates
- All P0 functional requirements implemented and passing QA acceptance tests
- End-to-end delivery tested with 10+ test accounts
- Zero false triggers in beta (100+ users, 3+ months)
- Check-in email delivered within 1 hour of scheduled time in 99%+ of test dispatches

### Security gates
- Independent penetration test completed. Critical/high findings remediated.
- Encryption implementation reviewed against OWASP Mobile Security Testing Guide.
- Supabase RLS policies audited for privilege escalation.

### PWA gates
- Lighthouse PWA score ≥ 90 on mobile and desktop
- Installable and functional offline on iOS Safari and Android Chrome
- Capacitor builds pass App Store and Play Store review

### Legal & compliance gates
- Privacy Policy and Terms of Service published and reviewed by legal
- GDPR compliance assessment documented
- Data Processing Agreement in place with Supabase and Resend

### Quality gates
- Crash-free rate 99.5%+ across beta devices
- App cold launch under 2.5 seconds on reference device set
- Accessibility audit: all P0 requirements verified

---

*End of Legate PRD v2.0*
