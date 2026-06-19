/**
 * BIP-39 recovery phrase helpers (T4 / F4).
 *
 * Uses @scure/bip39 — pure WebCrypto/noble implementation with no Node
 * `Buffer` dependency (the old `bip39` package required Buffer and crashed
 * in the browser).
 */

import { generateMnemonic, validateMnemonic, mnemonicToSeedSync } from '@scure/bip39'
import { wordlist } from '@scure/bip39/wordlists/english'

// Canonical form used for hashing/derivation: trimmed, lowercase, single
// spaces. Applied identically when the phrase is generated and when the
// user re-enters it during recovery, so the hash/derived key match.
export const normalizeMnemonic = (phrase: string): string =>
  phrase.trim().toLowerCase().split(/\s+/).join(' ')

export const bip39Module = {
  generatePhrase: (): string[] => {
    const mnemonic = generateMnemonic(wordlist, 256) // 24 words
    return mnemonic.split(' ')
  },

  validatePhrase: (phrase: string): boolean => {
    return validateMnemonic(normalizeMnemonic(phrase), wordlist)
  },
}

// SHA-256 of the normalized mnemonic, hex-encoded. Stored server-side as
// `recovery_phrase_hash` so a later /recover attempt can be validated
// without ever storing the phrase itself.
export const hashMnemonic = async (mnemonic: string): Promise<string> => {
  const data = new TextEncoder().encode(normalizeMnemonic(mnemonic))
  const digest = await crypto.subtle.digest('SHA-256', data)
  return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, '0')).join('')
}

// Derives an AES-256-GCM key from the recovery phrase + a per-user random
// salt via the BIP-39 seed (PBKDF2-HMAC-SHA512, 2048 rounds) -> HKDF-SHA256.
// Used to wrap/unwrap the second CEK blob (`recovery_encrypted_cek`).
export const deriveRecoveryKey = async (mnemonic: string, salt: Uint8Array): Promise<CryptoKey> => {
  const seed = mnemonicToSeedSync(normalizeMnemonic(mnemonic))
  const keyMaterial = await crypto.subtle.importKey('raw', seed, 'HKDF', false, ['deriveKey'])
  return crypto.subtle.deriveKey(
    { name: 'HKDF', salt: salt as unknown as BufferSource, info: new TextEncoder().encode('legate-recovery-cek-wrap'), hash: 'SHA-256' },
    keyMaterial,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt']
  )
}
