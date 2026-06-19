export const uploadEncryptedBlob = async (
  uploadUrl: string,
  blob: Blob
): Promise<void> => {
  const res = await fetch(uploadUrl, {
    method: 'PUT',
    body: blob,
    headers: { 'Content-Type': 'application/octet-stream' },
  })
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
}

// T5: download the encrypted content blob from a Supabase signed URL for
// in-app decryption (capsule edit/view).
export const downloadEncryptedBlob = async (url: string): Promise<ArrayBuffer> => {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Download failed: ${res.status}`)
  return res.arrayBuffer()
}
