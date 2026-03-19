import { useCallback, useRef, useState } from "react";
import "./FileDropZone.css";

const ACCEPTED = ".pdf,.jpg,.jpeg,.png";

export function FileDropZone({ onFile, current, error = false }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  const handleFile = useCallback((file) => {
    if (file) onFile(file);
  }, [onFile]);

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    handleFile(e.dataTransfer.files[0]);
  }, [handleFile]);

  const onDragOver = useCallback((e) => { e.preventDefault(); setDragging(true); }, []);
  const onDragLeave = useCallback(() => setDragging(false), []);

  const cls = [
    "dropzone",
    dragging && "dropzone--active",
    current && "dropzone--filled",
    error && "dropzone--error",
  ].filter(Boolean).join(" ");

  return (
    <div className={cls} onDrop={onDrop} onDragOver={onDragOver} onDragLeave={onDragLeave} onClick={() => inputRef.current?.click()}>
      <input ref={inputRef} type="file" accept={ACCEPTED} className="dropzone__input" onChange={(e) => handleFile(e.target.files[0])} />
      {current ? (
        <span className="dropzone__filename">{current.name}</span>
      ) : (
        <span className="dropzone__placeholder">Glisser un fichier ou cliquer</span>
      )}
    </div>
  );
}
