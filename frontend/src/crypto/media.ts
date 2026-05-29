export const mediaEncryption = {
  encrypt: async (file: File, cek: CryptoKey): Promise<{ encryptedBlob: Blob; iv: Uint8Array }> => {
    const iv = crypto.getRandomValues(new Uint8Array(12))
    const arrayBuf = await file.arrayBuffer()
    const encrypted = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, cek, arrayBuf)
    return { encryptedBlob: new Blob([encrypted]), iv }
  },

  decrypt: async (encryptedBlob: Blob, cek: CryptoKey, iv: Uint8Array): Promise<Blob> => {
    const arrayBuf = await encryptedBlob.arrayBuffer()
    const decrypted = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, cek, arrayBuf)
    return new Blob([decrypted])
  },
}
