/**
 * Node-side mirror of frontend/src/crypto/bip39.ts's normalizeMnemonic +
 * hashMnemonic, used only so specs can independently verify the server-side
 * recovery_phrase_hash without re-using app code — the point of an e2e test
 * is to check the app's actual output, not call back into it.
 */
import { createHash } from 'node:crypto'

export function normalizeMnemonic(phrase: string): string {
  return phrase.trim().toLowerCase().split(/\s+/).join(' ')
}

export function hashMnemonicHex(phrase: string): string {
  return createHash('sha256').update(normalizeMnemonic(phrase)).digest('hex')
}
