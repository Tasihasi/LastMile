import { useCallback, useRef, useState } from "react";

interface FileUploadProps {
  onUpload: (file: File) => void;
  isUploading: boolean;
}

const ACCEPTED = ".csv,.xlsx,.txt,.xml";

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
        <p>Uploading...</p>
      ) : (
        <>
          <p className="upload-icon">+</p>
          <p>Drop a file here or click to upload</p>
          <p className="upload-hint">CSV, Excel, TXT, or XML</p>
        </>
      )}
    </div>
  );
}
