/**
 * Supabase Storage upload helpers
 */

export const uploadToStorage = async (bucket: string, path: string, file: File): Promise<string> => {
  // TODO: Implement Supabase storage upload
  // - Get pre-signed upload URL
  // - Upload file blob
  // - Return storage object path
  throw new Error('Not implemented')
}

export const getSignedUrl = async (bucket: string, path: string): Promise<string> => {
  // TODO: Implement getting signed download URL from Supabase
  throw new Error('Not implemented')
}
