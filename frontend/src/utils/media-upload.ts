/**
 * Shared helper for the full encrypt → upload → thumbnail → confirm pipeline.
 * Used by both MediaUploader (edit mode, immediate upload) and CapsuleEditor
 * (create mode, uploads after capsule row is created).
 */

import { capsulesApi } from '../api/capsules'
import {
  mediaEncryption,
  generateEncryptedThumbnail,
  seekVideoToFirstFrame,
} from '../crypto/media'
import type { MediaAttachment, MediaKind } from '../types/api'

export async function uploadSingleMedia(
  capsuleId: string,
  file: File,
  cek: CryptoKey,
  onProgress?: (pct: number) => void,
): Promise<MediaAttachment> {
  const kind: MediaKind = file.type.startsWith('video/') ? 'video' : 'photo'

  // Step 1: encrypt the file
  const { encryptedBlob, cipherIvHex } = await mediaEncryption.encrypt(file, cek)

  // Step 2: register row with backend
  const { data: createData } = await capsulesApi.createMedia(capsuleId, {
    filename: file.name,
    content_type: file.type,
    size_bytes: file.size,
    kind,
    cipher_iv: cipherIvHex,
  })
  const mid: string = createData.attachment_id

  // Step 3: server-side blob upload
  await capsulesApi.uploadMediaContent(capsuleId, mid, encryptedBlob, onProgress)

  // Step 4: thumbnail (best-effort, non-fatal)
  try {
    let thumbBlob: Blob
    if (kind === 'photo') {
      thumbBlob = await generateEncryptedThumbnail(file, cek)
    } else {
      // Video: load in a hidden element, seek to first frame, capture
      const video = document.createElement('video')
      const objUrl = URL.createObjectURL(file)
      video.src = objUrl
      video.muted = true
      video.playsInline = true
      await new Promise<void>((res, rej) => {
        video.addEventListener('loadeddata', () => res(), { once: true })
        video.addEventListener('error', () => rej(new Error('video load error')), { once: true })
        setTimeout(() => rej(new Error('video load timeout')), 15000)
        video.load()
      })
      await seekVideoToFirstFrame(video)
      thumbBlob = await generateEncryptedThumbnail(video, cek)
      URL.revokeObjectURL(objUrl)
    }
    await capsulesApi.uploadThumbnail(capsuleId, mid, thumbBlob)
  } catch {
    // thumbnail failure doesn't block confirm
  }

  // Step 5: confirm — backend verifies the object exists and marks ready
  const { data: confirmed } = await capsulesApi.confirmMedia(capsuleId, mid)
  return confirmed as MediaAttachment
}
