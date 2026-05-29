import { useRef, useState } from 'react'
import { Upload, X } from 'lucide-react'

interface MediaUploaderProps {
  files: File[]
  onFilesChange: (files: File[]) => void
  maxFiles?: number
  maxSizeMB?: number
}

export default function MediaUploader({ files, onFilesChange, maxFiles = 20, maxSizeMB = 10 }: MediaUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const addFiles = (newFiles: File[]) => {
    setError(null)
    const valid: File[] = []
    for (const f of newFiles) {
      if (f.size > maxSizeMB * 1024 * 1024) {
        setError(`"${f.name}" exceeds ${maxSizeMB}MB limit`)
        continue
      }
      valid.push(f)
    }
    const combined = [...files, ...valid].slice(0, maxFiles)
    if (files.length + valid.length > maxFiles) {
      setError(`Maximum ${maxFiles} files allowed`)
    }
    onFilesChange(combined)
  }

  const removeFile = (index: number) => {
    onFilesChange(files.filter((_, i) => i !== index))
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    addFiles(Array.from(e.dataTransfer.files))
  }

  return (
    <div className="space-y-3">
      <div
        className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${dragOver ? 'border-[#3D4F6B] bg-blue-50' : 'border-gray-200 hover:border-gray-300'}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
        <p className="text-sm text-[#6B7280]">
          Drag & drop photos/videos or <span className="text-[#3D4F6B] font-medium">browse</span>
        </p>
        <p className="text-xs text-gray-400 mt-1">Max {maxSizeMB}MB per file, up to {maxFiles} files</p>
        <input
          ref={inputRef}
          type="file"
          accept="image/*,video/*"
          multiple
          className="hidden"
          onChange={(e) => { if (e.target.files) addFiles(Array.from(e.target.files)) }}
        />
      </div>

      {error && <p className="text-xs text-red-600">{error}</p>}

      {files.length > 0 && (
        <div className="grid grid-cols-3 gap-2">
          {files.map((file, i) => (
            <div key={i} className="relative group">
              {file.type.startsWith('image/') ? (
                <img
                  src={URL.createObjectURL(file)}
                  alt={file.name}
                  className="w-full h-24 object-cover rounded-lg"
                />
              ) : (
                <div className="w-full h-24 bg-gray-100 rounded-lg flex items-center justify-center">
                  <p className="text-xs text-[#6B7280] truncate px-1">{file.name}</p>
                </div>
              )}
              <button
                onClick={(e) => { e.stopPropagation(); removeFile(i) }}
                className="absolute top-1 right-1 w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                aria-label="Remove file"
              >
                <X className="w-3 h-3" />
              </button>
              <p className="text-xs text-[#6B7280] truncate mt-1">
                {(file.size / 1024).toFixed(0)}KB
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
