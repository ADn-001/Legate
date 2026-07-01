/**
 * Media encryption/decryption utilities (T1/T2, Phase 4).
 *
 * Photo format: single AES-GCM pass, IV returned separately.
 *   cipher_iv stored as hex string.
 *
 * Video format (chunked): chunked AES-GCM for files > threshold.
 *   Wire format (concatenated bytes):
 *     [ 12 bytes IV ][ N+16 bytes ciphertext (N plaintext + 16 GCM tag) ]
 *     repeated per chunk.
 *   cipher_iv stored as JSON string: '{"scheme":"chunk-gcm","chunk_bytes":N}'
 */

const CHUNK_BYTES = 5 * 1024 * 1024  // 5 MB per chunk
const VIDEO_SIZE_THRESHOLD = 50 * 1024 * 1024  // >50 MB → use chunked path

export interface EncryptedMedia {
  encryptedBlob: Blob
  iv: Uint8Array
  cipherIvHex: string  // hex for photos; JSON metadata string for videos
}

// ── Photo encryption (single-shot AES-GCM) ─────────────────────────────────

async function encryptPhoto(file: File, cek: CryptoKey): Promise<EncryptedMedia> {
  const iv = crypto.getRandomValues(new Uint8Array(12))
  const arrayBuf = await file.arrayBuffer()
  const encrypted = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, cek, arrayBuf)
  return {
    encryptedBlob: new Blob([encrypted], { type: 'application/octet-stream' }),
    iv,
    cipherIvHex: Array.from(iv).map(b => b.toString(16).padStart(2, '0')).join(''),
  }
}

async function decryptPhoto(encryptedBlob: Blob, cek: CryptoKey, iv: Uint8Array): Promise<Blob> {
  const arrayBuf = await encryptedBlob.arrayBuffer()
  // new Uint8Array(iv) copies to a fresh ArrayBuffer so the subtle API gets a
  // concrete ArrayBuffer rather than the SharedArrayBuffer-compatible generic.
  const decrypted = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: new Uint8Array(iv) }, cek, arrayBuf)
  return new Blob([decrypted])
}

// ── Video encryption (chunked AES-GCM) ─────────────────────────────────────
// Wire format: repeated [ 12-byte IV | encrypted-chunk ] per CHUNK_BYTES slice.

interface ChunkMeta {
  scheme: 'chunk-gcm'
  chunk_bytes: number
}

async function encryptVideoChunked(file: File, cek: CryptoKey): Promise<EncryptedMedia> {
  const parts: ArrayBuffer[] = []
  let offset = 0

  while (offset < file.size) {
    const slice = file.slice(offset, offset + CHUNK_BYTES)
    const plainBuf = await slice.arrayBuffer()
    const iv = crypto.getRandomValues(new Uint8Array(12))
    const encrypted = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, cek, plainBuf)
    parts.push(iv.buffer as ArrayBuffer)
    parts.push(encrypted)
    offset += CHUNK_BYTES
  }

  const meta: ChunkMeta = { scheme: 'chunk-gcm', chunk_bytes: CHUNK_BYTES }
  // Return a dummy IV (not used for chunked — the real IVs are inline in the blob)
  const dummyIv = new Uint8Array(12)
  return {
    encryptedBlob: new Blob(parts, { type: 'application/octet-stream' }),
    iv: dummyIv,
    cipherIvHex: JSON.stringify(meta),
  }
}

async function decryptVideoChunked(
  encryptedBlob: Blob,
  cek: CryptoKey,
  chunkBytes: number,
): Promise<Blob> {
  const buf = await encryptedBlob.arrayBuffer()
  const view = new Uint8Array(buf)
  const parts: Uint8Array[] = []
  let offset = 0
  const encChunkSize = chunkBytes + 16  // AES-GCM adds 16-byte tag

  while (offset < view.byteLength) {
    const iv = view.slice(offset, offset + 12)
    offset += 12
    const encChunk = view.slice(offset, offset + encChunkSize)
    offset += encChunkSize
    const decrypted = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv },
      cek,
      encChunk,
    )
    parts.push(new Uint8Array(decrypted))
  }

  const totalLen = parts.reduce((s, p) => s + p.byteLength, 0)
  const result = new Uint8Array(totalLen)
  let pos = 0
  for (const p of parts) { result.set(p, pos); pos += p.byteLength }
  return new Blob([result])
}

// ── Thumbnail generation (photos + video first frame) ──────────────────────
//
// Wire format: [ 12-byte IV ][ AES-GCM ciphertext ]
// The IV is prepended inline so decryption is self-contained — no need to
// store a separate thumbnail_cipher_iv column.

export async function generateEncryptedThumbnail(
  source: File | HTMLVideoElement,
  cek: CryptoKey,
  maxDimension = 320,
): Promise<Blob> {
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')!

  if (source instanceof File && source.type.startsWith('image/')) {
    const img = await createImageBitmap(source)
    const scale = Math.min(1, maxDimension / Math.max(img.width, img.height))
    canvas.width = Math.round(img.width * scale)
    canvas.height = Math.round(img.height * scale)
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
    img.close()
  } else if (source instanceof HTMLVideoElement) {
    const scale = Math.min(1, maxDimension / Math.max(source.videoWidth, source.videoHeight))
    canvas.width = Math.round(source.videoWidth * scale)
    canvas.height = Math.round(source.videoHeight * scale)
    ctx.drawImage(source, 0, 0, canvas.width, canvas.height)
  } else {
    throw new Error('Cannot generate thumbnail for this source type')
  }

  const jpegBlob = await new Promise<Blob>((res, rej) =>
    canvas.toBlob(b => (b ? res(b) : rej(new Error('canvas.toBlob failed'))), 'image/jpeg', 0.8),
  )
  const { encryptedBlob, iv } = await encryptPhoto(
    new File([jpegBlob], 'thumb.jpg', { type: 'image/jpeg' }),
    cek,
  )
  // Prepend IV so the blob is self-contained: [ 12 IV bytes | ciphertext ]
  return new Blob([iv.buffer as ArrayBuffer, await encryptedBlob.arrayBuffer()], {
    type: 'application/octet-stream',
  })
}

/**
 * Decrypt a thumbnail blob produced by generateEncryptedThumbnail.
 * Wire format: [ 12-byte IV ][ AES-GCM ciphertext ]
 */
export async function decryptThumbnail(encryptedBlob: Blob, cek: CryptoKey): Promise<Blob> {
  const buf = await encryptedBlob.arrayBuffer()
  const iv = new Uint8Array(buf, 0, 12)
  const ciphertext = new Uint8Array(buf, 12)
  const decrypted = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, cek, ciphertext)
  return new Blob([decrypted])
}

/** Seek a video element to the first frame and wait for it to render. */
export function seekVideoToFirstFrame(video: HTMLVideoElement): Promise<void> {
  return new Promise((resolve, reject) => {
    video.currentTime = 0.1
    video.addEventListener('seeked', () => resolve(), { once: true })
    video.addEventListener('error', () => reject(new Error('video seek error')), { once: true })
    setTimeout(() => reject(new Error('video seek timeout')), 5000)
  })
}

// ── Public API ──────────────────────────────────────────────────────────────

export const mediaEncryption = {
  /** Encrypt a photo or small video (single AES-GCM pass). */
  encrypt: async (file: File, cek: CryptoKey): Promise<EncryptedMedia> => {
    if (file.type.startsWith('video/') && file.size > VIDEO_SIZE_THRESHOLD) {
      return encryptVideoChunked(file, cek)
    }
    return encryptPhoto(file, cek)
  },

  /** Encrypt specifically as chunked video (for files > threshold or forced). */
  encryptVideo: async (file: File, cek: CryptoKey): Promise<EncryptedMedia> =>
    encryptVideoChunked(file, cek),

  /** Decrypt a blob given the cipher_iv metadata.
   * For photos: cipherIv is a hex string.
   * For chunked video: cipherIv is a JSON string with scheme/chunk_bytes.
   */
  decrypt: async (encryptedBlob: Blob, cek: CryptoKey, cipherIv: string): Promise<Blob> => {
    if (cipherIv.startsWith('{')) {
      const meta: ChunkMeta = JSON.parse(cipherIv)
      return decryptVideoChunked(encryptedBlob, cek, meta.chunk_bytes)
    }
    const iv = Uint8Array.from(cipherIv.match(/.{2}/g)!.map(h => parseInt(h, 16)))
    return decryptPhoto(encryptedBlob, cek, iv)
  },
}
