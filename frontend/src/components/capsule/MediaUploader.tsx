/**
 * Media Uploader Component
 * - Drag-and-drop upload area
 * - File input fallback
 * - Show thumbnails of uploaded files
 * - Remove button per file
 */

interface MediaUploaderProps {
  files: File[]
  onFilesChange: (files: File[]) => void
  accept?: string
}

export default function MediaUploader({ files, onFilesChange, accept = 'image/*,video/*' }: MediaUploaderProps) {
  // TODO: Implement MediaUploader component
  // - Drag-and-drop zone
  // - File input (hidden)
  // - Thumbnails of uploaded files
  // - Remove icon per file
  // - File size/type validation
  return <div>Media Uploader</div>
}
