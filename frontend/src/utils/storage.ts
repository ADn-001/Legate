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
