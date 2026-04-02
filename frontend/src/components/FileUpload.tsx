import { useCallback, useRef, useState } from "react";

interface FileUploadProps {
  onUpload: (file: File) => void;
  isUploading: boolean;
}

const ACCEPTED = ".csv,.xlsx,.txt,.xml";
const FORMATS = ["csv", "xlsx", "txt", "xml"];

export function FileUpload({ onUpload, isUploading }: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFile = useCallback(
    (file: File) => {
      onUpload(file);
    },
    [onUpload]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
      if (inputRef.current) inputRef.current.value = "";
    },
    [handleFile]
  );

  return (
    <div className="empty-state">
      <div
        className={`file-upload ${isDragging ? "dragging" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED}
          onChange={handleChange}
          hidden
        />
        {isUploading ? (
          <div className="upload-loading">
            <div className="upload-spinner" />
            <p className="upload-title">Processing file...</p>
          </div>
        ) : (
          <>
            <div className="upload-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <p className="upload-title">Drop your file here</p>
            <p className="upload-subtitle">or click to browse</p>
            <div className="upload-formats">
              {FORMATS.map((f) => (
                <span key={f} className="upload-format-tag">.{f}</span>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
