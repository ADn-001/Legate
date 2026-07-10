# Legate UML & Data Flow Diagrams v2.0

Revised for simplified architecture: Supabase + FastAPI + Celery + Redis + React PWA + Capacitor. Removed shard/node/seeder diagrams. Added deployment diagram, security flow diagram, and CI/CD lifecycle diagram.

---

## 1. Class Diagram

```plantuml
@startuml
skinparam classAttributeIconSize 0
skinparam linetype ortho

class User {
  +UUID id
  +String email
  +String passwordHash
  +Boolean emailVerified
  +Enum status
  +DateTime createdAt
  +DateTime lastLoginAt
}

class UserSettings {
  +UUID id
  +UUID userId
  +int checkInIntervalDays
  +int gracePeriodDays
  +int snoozeCountRemaining
  +Boolean needsOnboarding
  +DateTime nextCheckInAt
}

class EncryptionKey {
  +UUID id
  +UUID userId
  +Bytes encryptedCek
  +Bytes cekIv
  +Bytes pbkdf2Salt
  +int pbkdf2Iterations
  +String recoveryPhraseHash
}

class Beneficiary {
  +UUID id
  +UUID userId
  +String fullName
  +String email
  +String relationship
  +Boolean isEmergencyContact
  +Enum status
}

class Capsule {
  +UUID id
  +UUID userId
  +String title
  +Enum status
  +String storageObjectPath
  +Bytes cipherIv
  +int deliveryOrder
  +DateTime autoSavedAt
}

class CapsuleRecipient {
  +UUID id
  +UUID capsuleId
  +UUID beneficiaryId
  +Boolean isPrimary
  +Enum status
  +DateTime deliveredAt
}

class MediaAttachment {
  +UUID id
  +UUID capsuleId
  +Enum type
  +String mimeType
  +long sizeBytes
  +String storageObjectPath
  +Bytes cipherIv
  +Enum status
}

class CheckInSchedule {
  +UUID id
  +UUID userId
  +int intervalDays
  +int gracePeriodDays
  +DateTime nextDispatchAt
  +DateTime lastConfirmedAt
  +int snoozeCount
  +Boolean isPaused
  +int pauseCount
}

class CheckInEvent {
  +UUID id
  +UUID scheduleId
  +String token
  +Enum tokenType
  +Enum status
  +DateTime expiresAt
  +DateTime usedAt
}

class ReleaseTrigger {
  +UUID id
  +UUID userId
  +Enum reason
  +Enum status
  +DateTime triggeredAt
  +int pauseCount
}

class DeliveryEvent {
  +UUID id
  +UUID releaseTriggerID
  +UUID capsuleRecipientId
  +Enum deliveryStatus
  +String resendMessageId
  +int attempts
  +DateTime sentAt
}

class AuditLog {
  +UUID id
  +UUID userId
  +String eventType
  +String resourceType
  +UUID resourceId
  +DateTime createdAt
}

User "1" -- "1" UserSettings
User "1" -- "1" EncryptionKey
User "1" -- "*" Beneficiary
User "1" -- "*" Capsule
User "1" -- "1" CheckInSchedule
User "1" -- "*" AuditLog
Capsule "1" -- "*" CapsuleRecipient
Capsule "1" -- "*" MediaAttachment
CapsuleRecipient "*" -- "1" Beneficiary
CheckInSchedule "1" -- "*" CheckInEvent
ReleaseTrigger "1" -- "*" DeliveryEvent
CapsuleRecipient "1" -- "*" DeliveryEvent

@enduml
```

---

## 2. System Architecture Diagram

```plantuml
@startuml
skinparam componentStyle rectangle

package "Client Layer" {
  [React PWA\n(Vite + Workbox)] as PWA
  [Capacitor Shell\n(iOS / Android)] as CAP
  CAP --> PWA : wraps
}

package "Backend (Docker Compose)" {
  [FastAPI\n(Uvicorn)] as API
  [Celery Worker\n(delivery + cleanup)] as WORKER
  [Celery Beat\n(scheduler)] as BEAT
  [Redis\n(broker + cache)] as REDIS
  [Nginx\n(reverse proxy)] as NGINX

  NGINX --> API
  BEAT --> REDIS
  REDIS --> WORKER
  API --> REDIS : enqueue tasks
}

package "Supabase (Managed)" {
  database "PostgreSQL\n(structured data)" as PG
  storage "Supabase Storage\n(encrypted blobs)" as STORAGE
  [Supabase Auth] as SBAUTH
}

cloud "External Services" {
  [Resend\n(email)] as EMAIL
}

PWA --> NGINX : HTTPS / TLS 1.3
API --> PG : SQLAlchemy
API --> STORAGE : Supabase client
API --> SBAUTH : JWT validation
WORKER --> PG : read capsules + keys
WORKER --> STORAGE : fetch encrypted content
WORKER --> EMAIL : send delivery emails

@enduml
```

---

## 3. Sequence Diagrams

### 3.1 Account Creation & Key Setup

```plantuml
@startuml
actor User
participant "PWA\n(Browser)" as PWA
participant "FastAPI" as API
participant "Supabase\nPostgreSQL" as DB
participant "Resend" as EMAIL

User -> PWA: enter email + password
PWA -> PWA: derive wrapping key via PBKDF2\n(password + random salt, 100k iterations)
PWA -> PWA: generate random CEK (256-bit)
PWA -> PWA: encrypt CEK with wrapping key (AES-256-GCM)
PWA -> API: POST /auth/signup\n{ email, password_hash, encrypted_cek, cek_iv, pbkdf2_salt }
API -> DB: INSERT users, user_settings,\nencryption_keys, checkin_schedules
API -> EMAIL: send OTP verification email
API --> PWA: 201 Created
User -> PWA: enter 6-digit OTP
PWA -> API: POST /auth/verify-email { otp }
API -> DB: UPDATE users.email_verified = true
API --> PWA: 200 OK + JWT access token + refresh token
PWA -> PWA: generate 24-word BIP-39 recovery phrase\ndisplay to user
@enduml
```

---

### 3.2 Capsule Creation (Hybrid Encryption)

```plantuml
@startuml
actor User
participant "PWA\n(Web Crypto API)" as PWA
participant "FastAPI" as API
participant "Supabase\nPostgreSQL" as DB
participant "Supabase\nStorage" as STORAGE

User -> PWA: write capsule content + attach photos
PWA -> PWA: retrieve CEK from session memory\n(decrypted at login, held in memory only)
PWA -> PWA: encrypt content with CEK\n(AES-256-GCM, random IV per capsule)
PWA -> PWA: encrypt each photo file with CEK
PWA -> API: POST /capsules\n{ title, beneficiary_id, cipher_iv, content_hash }
API -> DB: INSERT capsule (metadata only, no plaintext)
API -> DB: INSERT capsule_recipient
API --> PWA: 201 { capsule_id, upload_urls[] }
PWA -> STORAGE: PUT encrypted content blob → capsule-content/{user_id}/{capsule_id}/content.enc
PWA -> STORAGE: PUT encrypted photo blobs → media-attachments/{user_id}/{capsule_id}/{photo_id}.enc
PWA -> API: PATCH /capsules/{id}\n{ storage_object_path, media_attachment_ids }
API -> DB: UPDATE capsule.storage_object_path\nINSERT media_attachments
API --> PWA: 200 OK
@enduml
```

---

### 3.3 Check-in Lifecycle

```plantuml
@startuml
participant "Celery Beat" as BEAT
participant "Celery Worker" as WORKER
participant "FastAPI" as API
participant "Supabase\nPostgreSQL" as DB
participant "Resend" as EMAIL
actor User

== Scheduled dispatch ==
BEAT -> WORKER: trigger check_in_dispatch task\n(every hour, finds due schedules)
WORKER -> DB: SELECT checkin_schedules\nWHERE next_dispatch_at <= NOW()
WORKER -> DB: INSERT checkin_event\n(token, type=confirm, expires_at=+7d)
WORKER -> EMAIL: send check-in email\n(confirm link + snooze links)
WORKER -> DB: UPDATE checkin_schedule.last_dispatched_at

== User confirms ==
User -> API: GET /checkin/confirm?token=abc123
API -> DB: SELECT checkin_event WHERE token=abc123
API -> DB: validate: not expired, not used
API -> DB: UPDATE checkin_event.status = used
API -> DB: UPDATE checkin_schedule\n(last_confirmed_at, next_dispatch_at += interval)
API --> User: redirect → confirmation web page

== User snoozes ==
User -> API: GET /checkin/snooze?token=xyz&days=14
API -> DB: validate token, check snooze_count < snooze_limit
API -> DB: UPDATE checkin_schedule.next_dispatch_at += 14 days\nINCREMENT snooze_count
API --> User: redirect → snooze confirmation page

== Grace period expires → trigger ==
BEAT -> WORKER: trigger grace_period_check task
WORKER -> DB: find schedules past grace period\nwith no confirmation
WORKER -> DB: INSERT release_trigger { reason: checkin_missed }
WORKER -> DB: UPDATE checkin_schedule.is_paused = false
WORKER -> WORKER: enqueue delivery_dispatch task

@enduml
```

---

### 3.4 Delivery Pipeline

```plantuml
@startuml
participant "Celery Worker\n(Delivery)" as WORKER
participant "FastAPI" as API
participant "Supabase\nPostgreSQL" as DB
participant "Supabase\nStorage" as STORAGE
participant "Resend" as EMAIL
actor Beneficiary

WORKER -> DB: SELECT release_trigger WHERE status=processing
WORKER -> DB: SELECT capsule_recipients\nJOIN capsules\nWHERE user_id = trigger.user_id
WORKER -> DB: SELECT encryption_keys WHERE user_id = trigger.user_id
WORKER -> STORAGE: GET encrypted_cek blob
WORKER -> WORKER: decrypt CEK using stored pbkdf2_salt + server-held password hash\n(isolated worker process, no logging)
loop for each capsule
  WORKER -> STORAGE: GET encrypted content blob
  WORKER -> WORKER: decrypt content with CEK
  WORKER -> STORAGE: GET encrypted media files
  WORKER -> WORKER: decrypt media files
  WORKER -> EMAIL: POST /emails (rendered HTML email\nwith inline images + video link)
  EMAIL --> WORKER: { message_id }
  WORKER -> DB: INSERT delivery_event { status: sent, resend_message_id }
  WORKER -> WORKER: discard plaintext immediately
end
WORKER -> DB: UPDATE release_trigger.status = completed
WORKER -> DB: UPDATE users.status = memorialized
WORKER -> WORKER: enqueue content_purge task (72h delay)

== 72 hours later ==
WORKER -> STORAGE: DELETE all objects under {user_id}/
WORKER -> DB: UPDATE capsules.status = deleted
WORKER -> DB: audit_log: content_purged

@enduml
```

---

### 3.5 Authentication & Token Flow

```plantuml
@startuml
actor User
participant "PWA" as PWA
participant "FastAPI" as API
participant "Redis\n(token store)" as REDIS
participant "Supabase\nPostgreSQL" as DB

== Login ==
User -> PWA: enter email + password
PWA -> API: POST /auth/login { email, password }
API -> DB: SELECT user WHERE email = ?
API -> API: verify bcrypt(password, password_hash)
API -> PWA: 200 { access_token (15min), refresh_token (7d) }
PWA -> PWA: derive wrapping key from password via PBKDF2
PWA -> API: GET /auth/me/encryption-key
API -> DB: SELECT encryption_keys WHERE user_id = ?
API --> PWA: { encrypted_cek, cek_iv, pbkdf2_salt }
PWA -> PWA: decrypt CEK with wrapping key\nhold CEK in memory (never persisted to localStorage)

== Token refresh ==
PWA -> API: POST /auth/refresh { refresh_token }
API -> REDIS: check token not blacklisted
API -> PWA: 200 { new_access_token }

== Logout ==
PWA -> API: POST /auth/logout { refresh_token }
API -> REDIS: blacklist refresh_token until expiry
PWA -> PWA: clear CEK from memory
API --> PWA: 200 OK

@enduml
```

---

## 4. User Journey Flowcharts

### 4.1 Primary User Journey

```
[Install PWA / open app]
        ↓
[Onboarding carousel (3 screens, skippable)]
        ↓
[Create account → email OTP verification]
        ↓
[Setup wizard]
  Step 1: Configure check-in interval + grace period
  Step 2: Add first beneficiary
  Step 3: Create first capsule (skippable)
  Step 4: Display + confirm BIP-39 backup phrase
        ↓
[Dashboard — active status]
        ↓
[Periodic check-in email received]
  → Click confirm → timer resets
  → Click snooze → timer extends
  → No action → grace period begins
        ↓ (grace period expires)
[Release trigger fires]
        ↓
[Delivery pipeline runs]
        ↓
[Beneficiaries receive emails]
        ↓
[Account enters memorial state]
        ↓
[Content purged after 72h]
```

### 4.2 Secondary Journey: Edit Capsule

```
[Capsules tab]
        ↓
[Select beneficiary → view capsule list]
        ↓
[Tap capsule → editor opens]
        ↓
[Edit text / add/remove photos]
        ↓
[Auto-save every 30s (local draft)]
        ↓
[Tap Save → re-encrypt with CEK → upload to Supabase Storage]
        ↓
[Old encrypted blob replaced → metadata updated]
```

### 4.3 Secondary Journey: Emergency Contact Pause

```
[Grace period expires with no check-in]
        ↓
[Celery worker emails emergency contact]
  "We haven't heard from [Name]. Click to pause delivery for 7 days."
        ↓
[Emergency contact clicks pause link]
        ↓
[API: GET /emergency/pause?token=...]
        ↓
[Validate token → check pause_count < 2]
        ↓
[UPDATE checkin_schedule: is_paused=true, pause_count++]
[UPDATE release_trigger: verification_state=cancelled]
        ↓
[User has 7 days to confirm they are OK]
  → User confirms → trigger cancelled, schedule resets
  → No confirm, 2nd pause available → emergency contact can pause again
  → Both pauses used, still no confirm → delivery proceeds
```

---

## 5. Deployment Diagram

```plantuml
@startuml
node "Production Server\n(Any Linux host / Railway / Render)" {
  component "Nginx\n:443" as NGINX
  component "FastAPI\n(Uvicorn :8000)" as API
  component "Celery Worker" as WORKER
  component "Celery Beat" as BEAT
  component "Redis :6379" as REDIS

  NGINX --> API
  API --> REDIS
  BEAT --> REDIS
  REDIS --> WORKER
}

cloud "Supabase Cloud" {
  component "PostgreSQL" as PG
  component "Supabase Storage" as STORAGE
  component "Supabase Auth" as AUTH
}

cloud "Resend" {
  component "Email API" as EMAIL
}

node "Vercel / Netlify\n(Static hosting)" {
  component "React PWA\n(static build)" as PWA
}

node "User Device" {
  component "Browser / Installed PWA\n/ Capacitor App" as CLIENT
}

CLIENT --> NGINX : HTTPS
CLIENT --> PWA : served from CDN
WORKER --> PG
WORKER --> STORAGE
WORKER --> EMAIL
API --> PG
API --> STORAGE
API --> AUTH

@enduml
```

---

## 6. CI/CD & Software Lifecycle Diagram

```plantuml
@startuml
|Developer|
start
:commit to feature branch;
:open pull request;

|GitHub Actions (CI)|
:run linting (ESLint + Ruff);
:run unit tests (Pytest + Vitest);
:run integration tests;
:build Docker image;
:run Trivy security scan on image;

if (all checks pass?) then (yes)
  |Developer|
  :PR approved + merged to main;
else (no)
  |Developer|
  :fix issues;
  stop
endif

|GitHub Actions (CD)|
:tag release (semver: vMAJOR.MINOR.PATCH);
:push Docker image to registry;
:deploy to staging (Railway);
:run smoke tests on staging;

if (smoke tests pass?) then (yes)
  :deploy to production (Railway);
  :run Alembic DB migrations;
  :deploy PWA build to Vercel;
  :notify team on Slack;
else (no)
  :rollback to previous image;
  :alert engineering team;
endif
stop

@enduml
```

---

## 7. Security Architecture Overview

### 7.1 Trust Boundaries

| Zone | Components | Can access plaintext? |
|------|-----------|----------------------|
| User device | PWA, Capacitor shell, Web Crypto API, CEK in memory | Yes — only here |
| Backend API | FastAPI, token validation, metadata ops | No |
| Delivery worker | Isolated Celery process, decrypts at send time | Temporarily — discards immediately |
| Supabase | PostgreSQL, Storage | No — encrypted at rest + client-side encrypted |
| Redis | Token blacklist, task queue | No content |

### 7.2 Key Points
- CEK is **never stored in localStorage, sessionStorage, or any persistent browser store**. It is held in memory only for the duration of the session.
- The server stores only the **encrypted CEK blob** — it cannot decrypt content without the user's password.
- The delivery worker is the only component that ever holds plaintext — in memory only, never written to disk or logs.
- All tokens (check-in confirm, snooze, emergency pause) are **single-use** and stored in PostgreSQL. Used tokens are marked immediately. Redis blacklist provides a second layer for JWT revocation.
- Supabase Row Level Security ensures no user can query another user's rows even with a valid JWT.

---

## 8. API Endpoint Summary (Swagger at `/docs`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/signup` | None | Create account |
| POST | `/auth/verify-email` | None | Verify OTP |
| POST | `/auth/login` | None | Login, get tokens |
| POST | `/auth/refresh` | Refresh token | Rotate access token |
| POST | `/auth/logout` | Access token | Blacklist refresh token |
| GET | `/auth/me` | Access token | Get current user |
| GET | `/auth/me/encryption-key` | Access token | Get encrypted CEK blob |
| GET | `/checkin/confirm` | Token param | Confirm check-in (no login) |
| GET | `/checkin/snooze` | Token param | Snooze check-in (no login) |
| GET | `/emergency/pause` | Token param | Emergency contact pause (no login) |
| GET | `/capsules` | Access token | List user's capsules |
| POST | `/capsules` | Access token | Create capsule metadata |
| GET | `/capsules/{id}` | Access token | Get capsule metadata |
| PATCH | `/capsules/{id}` | Access token | Update capsule |
| DELETE | `/capsules/{id}` | Access token | Delete capsule |
| GET | `/beneficiaries` | Access token | List beneficiaries |
| POST | `/beneficiaries` | Access token | Add beneficiary |
| PATCH | `/beneficiaries/{id}` | Access token | Update beneficiary |
| DELETE | `/beneficiaries/{id}` | Access token | Remove beneficiary |
| GET | `/settings/checkin` | Access token | Get check-in schedule |
| PATCH | `/settings/checkin` | Access token | Update check-in schedule |
| GET | `/settings/storage` | Access token | Get storage usage |
| DELETE | `/users/me` | Access token | Delete account (GDPR erasure) |

---

## 9. TODO / Next Steps

- Render PlantUML diagrams to SVG/PNG for report appendices (`plantuml legate_uml_diagrams_v2.md`)
- Add BPMN diagram for delivery pipeline trigger-to-send flow for report Chapter 4
- Define full OpenAPI schema (request/response bodies) in `/docs` — FastAPI generates this automatically from Pydantic models
- Write Alembic migration scripts once models are finalised
- Add activity diagram for offline sync behaviour (PWA draft cache → reconnect → upload)
