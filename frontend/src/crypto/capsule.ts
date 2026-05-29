export const capsuleEncryption = {
  encrypt: async (plaintext: string, cek: CryptoKey): Promise<{ ciphertext: Uint8Array; iv: Uint8Array }> => {
    const iv = crypto.getRandomValues(new Uint8Array(12))
    const enc = new TextEncoder()
    const encrypted = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, cek, enc.encode(plaintext))
    return { ciphertext: new Uint8Array(encrypted), iv }
  },

  decrypt: async (ciphertext: Uint8Array, cek: CryptoKey, iv: Uint8Array): Promise<string> => {
    const decrypted = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, cek, ciphertext)
    return new TextDecoder().decode(decrypted)
  },
}
