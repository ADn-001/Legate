/**
 * Crypto-related Types
 */

export interface KeyDerivationParams {
  password: string
  salt: Uint8Array
  iterations: number
}

export interface EncryptedCEK {
  encryptedCek: Uint8Array
  cekIv: Uint8Array
  pbkdf2Salt: Uint8Array
}

export interface EncryptedContent {
  ciphertext: Uint8Array
  iv: Uint8Array
}
