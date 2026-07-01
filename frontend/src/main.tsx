import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient } from '@tanstack/react-query'
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client'
import { openDB } from 'idb'
import App from './App'
import './index.css'

// IDB-backed persister for @tanstack/react-query-persist-client (T4/Phase 4)
// Keeps the query cache alive across page reloads so the PWA feels fast
// on revisit without a network round-trip.
const DB_NAME = 'legate-query'
const STORE   = 'cache'
const KEY     = 'v1'

async function getDB() {
  return openDB(DB_NAME, 1, {
    upgrade(db) { db.createObjectStore(STORE) },
  })
}

const idbPersister = {
  persistClient: async (client: unknown) => {
    const db = await getDB()
    await db.put(STORE, client, KEY)
  },
  restoreClient: async () => {
    const db = await getDB()
    return db.get(STORE, KEY)
  },
  removeClient: async () => {
    const db = await getDB()
    await db.delete(STORE, KEY)
  },
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30000,
      // gcTime must be ≥ maxAge for the persister to be useful
      gcTime: 1000 * 60 * 60 * 24, // 24 h
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <PersistQueryClientProvider
      client={queryClient}
      persistOptions={{ persister: idbPersister, maxAge: 1000 * 60 * 60 * 24 }}
    >
      <App />
    </PersistQueryClientProvider>
  </React.StrictMode>,
)
