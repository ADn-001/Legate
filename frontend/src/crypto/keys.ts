export const keysModule = {
  deriveWrappingKey: async (password: string, salt: Uint8Array<ArrayBuffer>): Promise<CryptoKey> => {
    const enc = new TextEncoder()
    const keyMaterial = await crypto.subtle.importKey('raw', enc.encode(password), 'PBKDF2', false, ['deriveKey'])
    return crypto.subtle.deriveKey(
      { name: 'PBKDF2', salt, iterations: 100000, hash: 'SHA-256' },
      keyMaterial,
      { name: 'AES-GCM', length: 256 },
      false,
      ['encrypt', 'decrypt']
    )
  },

  generateCEK: async (): Promise<CryptoKey> => {
    return crypto.subtle.generateKey({ name: 'AES-GCM', length: 256 }, true, ['encrypt', 'decrypt'])
  },

  encryptCEK: async (cek: CryptoKey, wrappingKey: CryptoKey): Promise<{ encryptedCek: Uint8Array<ArrayBuffer>; iv: Uint8Array<ArrayBuffer> }> => {
    const rawCek = await crypto.subtle.exportKey('raw', cek)
    const iv = crypto.getRandomValues(new Uint8Array(12))
    const encrypted = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, wrappingKey, rawCek)
    return { encryptedCek: new Uint8Array(encrypted), iv }
  },

  decryptCEK: async (encryptedCek: Uint8Array<ArrayBuffer>, wrappingKey: CryptoKey, iv: Uint8Array<ArrayBuffer>): Promise<CryptoKey> => {
    const rawCek = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, wrappingKey, encryptedCek)
    return crypto.subtle.importKey('raw', rawCek, { name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt'])
  },

  importHexKey: async (hex: string): Promise<CryptoKey> => {
    const bytes = new Uint8Array(hex.match(/.{1,2}/g)!.map(b => parseInt(b, 16)))
    return crypto.subtle.importKey('raw', bytes, { name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt'])
  },
}

export const toBase64 = (buf: Uint8Array): string =>
  btoa(String.fromCharCode(...buf))

export const fromBase64 = (b64: string): Uint8Array<ArrayBuffer> =>
  new Uint8Array(atob(b64).split('').map(c => c.charCodeAt(0)))
