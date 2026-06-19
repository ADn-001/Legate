export const capsuleEncryption = {
  encrypt: async (plaintext: string, cek: CryptoKey): Promise<{ ciphertext: Uint8Array<ArrayBuffer>; iv: Uint8Array<ArrayBuffer> }> => {
    const iv = crypto.getRandomValues(new Uint8Array(12))
    const enc = new TextEncoder()
    const encrypted = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, cek, enc.encode(plaintext))
    return { ciphertext: new Uint8Array(encrypted), iv }
  },

  decrypt: async (ciphertext: Uint8Array<ArrayBuffer>, cek: CryptoKey, iv: Uint8Array<ArrayBuffer>): Promise<string> => {
    const decrypted = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, cek, ciphertext)
    return new TextDecoder().decode(decrypted)
  },
}

// T5: cipher_iv is exchanged with the backend as a lowercase hex string
// (stored as raw bytes / LargeBinary in Postgres).
export const bytesToHex = (bytes: Uint8Array): string =>
  Array.from(bytes).map(b => b.toString(16).padStart(2, '0')).join('')

export const hexToBytes = (hex: string): Uint8Array<ArrayBuffer> =>
  new Uint8Array((hex.match(/.{1,2}/g) ?? []).map(b => parseInt(b, 16)))
