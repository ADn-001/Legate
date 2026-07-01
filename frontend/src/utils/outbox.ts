/**
 * Offline outbox — T4 (Phase 4)
 *
 * Stores failed mutation requests in IndexedDB when the user is offline,
 * then flushes them when the browser comes back online.
 *
 * Only lightweight check-in confirms are outboxed here. Large blob uploads
 * (capsule content, media) are too big to queue and must be retried manually.
 *
 * Schema:
 *   store: "outbox"
 *   keyPath: "id" (auto-increment)
 *   { method, url, body, createdAt }
 */

import { openDB, type DBSchema, type IDBPDatabase } from 'idb'

interface OutboxEntry {
  id?: number
  method: string
  url: string
  body: string  // JSON-serialized body
  createdAt: number
}

interface LegateDB extends DBSchema {
  outbox: {
    key: number
    value: OutboxEntry
    indexes: { 'by-created': number }
  }
}

let _db: IDBPDatabase<LegateDB> | null = null

async function getDb(): Promise<IDBPDatabase<LegateDB>> {
  if (_db) return _db
  _db = await openDB<LegateDB>('legate', 1, {
    upgrade(db) {
      const store = db.createObjectStore('outbox', { keyPath: 'id', autoIncrement: true })
      store.createIndex('by-created', 'createdAt')
    },
  })
  return _db
}

export async function enqueueOutbox(method: string, url: string, body: unknown): Promise<void> {
  const db = await getDb()
  await db.add('outbox', { method, url, body: JSON.stringify(body), createdAt: Date.now() })
}

export async function flushOutbox(
  accessToken: string | null,
  apiBaseUrl: string,
): Promise<void> {
  const db = await getDb()
  const all = await db.getAllFromIndex('outbox', 'by-created')
  for (const entry of all) {
    try {
      const res = await fetch(`${apiBaseUrl}${entry.url}`, {
        method: entry.method,
        headers: {
          'Content-Type': 'application/json',
          ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        },
        body: entry.body,
      })
      if (res.ok || res.status < 500) {
        // Remove from queue on success or permanent failure (4xx)
        if (entry.id != null) await db.delete('outbox', entry.id)
      }
      // 5xx: leave in queue, retry on next flush
    } catch {
      // Network still down — leave in queue
    }
  }
}

export async function getOutboxCount(): Promise<number> {
  const db = await getDb()
  return db.count('outbox')
}
