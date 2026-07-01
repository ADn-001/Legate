# Legate — Security Architecture & Documented Deviations

This document consolidates Legate's security architecture, approved deviations from
ideal security practices, and operational guidance for secret management.  It is the
authoritative reference for Phase 5 audit items S1–S6 and NFR-09.

---

## 1. Encryption Architecture Summary

Legate uses a layered key hierarchy so the backend server **never** holds plaintext
capsule content.

```
User password
    │ PBKDF2-SHA256 (100,000 iterations)
    ▼
Wrapping Key (AES-256-GCM)
    │ wraps
    ▼
Content Encryption Key — CEK  (AES-256-GCM, 256-bit)
    │ encrypts
    ▼
Capsule plaintext  (stored ciphertext in Supabase Storage)
```

**Key material flow:**

| Material | Where it lives | Never crosses |
|---|---|---|
| CEK | Browser memory only | Server boundary |
| Wrapping key | Derived in browser from password; never serialized | Server boundary |
| `encrypted_cek` + `cek_iv` + `pbkdf2_salt` | Stored in `encryption_keys` table | In plaintext |
| Capsule ciphertext | Supabase Storage (`capsule-content` bucket) | Decrypted at rest |

**Delivery path (CEK unwrapping at delivery time):**

The delivery worker holds a separate wrapping key derived as
`HMAC-SHA256(DELIVERY_SECRET, user_id)`.  At signup the client:
1. Derives the delivery wrapping key by calling `POST /auth/me/delivery-wrapping-key`.
2. Re-encrypts the CEK under the delivery wrapping key.
3. Sends `delivery_encrypted_cek` + `delivery_cek_iv` to the server.

The server stores the delivery-wrapped blob.  At delivery time, the worker re-derives
the wrapping key from `DELIVERY_SECRET` and `user_id` (no network call to the browser
required) and decrypts the CEK in-process.

**Threat model notes (PRD §8, R-03):**

- The delivery worker never logs plaintext capsule content, CEK bytes, or wrapped keys
  (NFR-09 — see §6 below).
- Capsule ciphertext is deleted from Supabase Storage within 72 hours of delivery
  (content purge task, FR-41).
- The server cannot read historical capsule content: only the CEK-holder (the user)
  or the delivery worker (during the delivery window) can decrypt.

---

## 2. Secret Generation Instructions (S1)

Three secrets must be set in the environment.  **Never use placeholder values.**
The startup validator (`app/config.py`) rejects values shorter than 32 characters or
containing the substrings `fake`, `changeme`, `secret`, `example`, `replace`, or
`placeholder`.

| Variable | Source | How to generate |
|---|---|---|
| `SECRET_KEY` | Random | `openssl rand -base64 48` |
| `DELIVERY_SECRET` | Random | `openssl rand -base64 48` |
| `SUPABASE_JWT_SECRET` | Supabase Dashboard | Project Settings → API → JWT Secret |

**Rotating `DELIVERY_SECRET` is a destructive operation.**  Existing
`delivery_encrypted_cek` blobs were wrapped under the old key.  After rotation the
delivery worker will be unable to decrypt them and all pending deliveries will fail
permanently.  Always re-wrap existing blobs before rotating.

---

## 3. S2 — Delivery Wrapping Key Endpoint Design

**Endpoint:** `POST /auth/me/delivery-wrapping-key`

**Why POST?** GET requests may be cached by proxies, appear in browser history, and are
vulnerable to link prefetching.  POST prevents all three.

**What is returned?**  The HMAC-SHA256 hex digest of `(DELIVERY_SECRET, user_id)`.
This is a deterministic, server-side value — the client does not set it.

**Access control:** Requires a valid JWT (`get_current_verified_user`).

**Audit logging:** Every call writes an `audit_logs` row with event type
`delivery_wrapping_key_accessed`, user ID, timestamp, and client IP.

**Rate limiting:** 5 requests/minute/IP (slowapi, same Redis bucket as other auth
endpoints).  Normal client behaviour is at most one call per session (at signup and when
re-wrapping after a password change), so this limit is generous.

**Secrecy guarantee:** The wrapping key's secrecy depends entirely on `DELIVERY_SECRET`
remaining secret.  If `DELIVERY_SECRET` is compromised an attacker can derive any user's
delivery wrapping key from their `user_id` (which is a UUID stored in the DB).
This is why S1 (strong `DELIVERY_SECRET`) is a prerequisite.

---

## 4. S4 — DB Single-Use Tokens (Deviation from NFR-12 Redis Blacklist)

**NFR-12** calls for a Redis blacklist to prevent JWT replay.  Legate uses a different
but equivalent mechanism for check-in / snooze / pause tokens:

- Tokens are 64-byte URL-safe random strings stored in the `checkin_tokens` table.
- They are single-use: consuming a token mutates its `status` column to `used` in the
  same database transaction as the action it authorises.
- Tokens expire after 7 days (enforced by an `expires_at` column checked on every use).
- The token is never a JWT; it is an opaque bearer secret with no decodable payload.

**Why this is equivalent to a blacklist:**
A Redis blacklist records "this token has been used" so a replay is rejected.  The DB
`status` mutation achieves the same guarantee: a second use of the same token finds
`status = used` and returns 409.  The atomicity of the status mutation prevents a
TOCTOU race that a separate blacklist check-then-use would be vulnerable to.

**Approved deviation:** This approach was reviewed and approved during project design.
It does not apply to Supabase JWTs (access/refresh tokens), which are validated by
Supabase's own token service.

---

## 5. S6 — GET Mutations for Email-Client Links (Deviation from CSRF Best Practice)

**Affected endpoints:** `GET /checkin/confirm`, `GET /checkin/snooze`,
`GET /checkin/emergency/pause`

**Why GET?** These endpoints are accessed by clicking a link in an email.  Email clients
do not support forms or JavaScript.  A `POST` endpoint cannot be triggered by a plain
hyperlink; `GET` is the only viable mechanism.

**CSRF analysis:**  
Traditional CSRF attacks exploit the fact that browsers attach cookies to cross-origin
requests.  These endpoints do not use cookie authentication — they are authenticated
solely by possession of the token in the URL query string.

- Tokens are 64-byte URL-safe random strings (≥ 512 bits of entropy).
- They are not guessable by an attacker who does not have access to the email.
- A CSRF attack would require the attacker to know the token, at which point they also
  have the ability to click the link directly — the CSRF surface adds nothing.
- Single-use enforcement means that even if an attacker somehow replays a token URL,
  the first legitimate use has already invalidated it.

**Residual risk:** An attacker who intercepts the email (e.g. via a compromised inbox)
can click the link.  This risk is inherent to any email-link flow and is not addressable
by CSRF mitigations.

---

## 6. NFR-09 / R-03 — Worker Isolation: No Plaintext Logging

**NFR-09** forbids logging plaintext capsule content, CEK bytes, wrapped keys, or
recovery material in any log stream.

**Verification (Phase 5 T6 sweep):**

The delivery and cleanup workers (`backend/app/worker/tasks/`) were audited for logging
statements that could expose plaintext:

| File | Logger calls | Verdict |
|---|---|---|
| `delivery_tasks.py` | None | ✓ Clean |
| `cleanup_tasks.py` | `logger.warning` (bucket/prefix names, object counts) | ✓ Clean — storage paths only, no content |
| `core/email.py` | None | ✓ Clean |

**Invariants to maintain:**
1. `cek` (bytes) must never appear in a `logger.*()` call or `print()`.
2. `wrapping_key` (bytes/hex) must never be logged.
3. `plaintext` (decrypted capsule bytes) must never be logged.
4. The only identifiers that may appear in logs are: `trigger_id`, `user_id`, `capsule_id`,
   `recipient_id`, storage bucket name, object count, and exception type (not message, if
   the message could contain content).

A CI grep guard (see `backend/scripts/check_no_plaintext_log.sh`) asserts that no
delivery/cleanup Python files log variables named `cek`, `plaintext`, or `wrapping_key`.

---

## 7. Frontend Crypto Hardening

- The CEK lives in Zustand store in browser memory only.  It is never written to
  `localStorage`, `sessionStorage`, `IndexedDB`, or any other persistent storage.
- The ESLint `no-console` rule (error level, `console.error` allowed) prevents accidental
  `console.log(cek)` style leaks from reaching production builds.
- `crypto.subtle` operations are used exclusively — the Web Crypto API is non-extractable
  by default for wrapping keys derived via PBKDF2.
