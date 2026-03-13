"use client";

import { useState, useRef, useCallback } from "react";
import UserAvatar from "./UserAvatar";
import { apiFetch } from "../../lib/api";

interface AvatarUploadProps {
  username: string;
  role: string;
  currentAvatarUrl?: string | null;
  onUpdated: (newUrl: string | null) => void;
  toast: (msg: string, v?: any) => void;
}

// Resize & center-crop image to 200×200, encode as JPEG base64
function processImage(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    if (!file.type.startsWith("image/")) {
      reject(new Error("File must be an image"));
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      reject(new Error("Image must be smaller than 5 MB"));
      return;
    }

    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Failed to read file"));
    reader.onload = (e) => {
      const img = new Image();
      img.onerror = () => reject(new Error("Failed to load image"));
      img.onload = () => {
        const TARGET = 200;
        const canvas = document.createElement("canvas");
        canvas.width  = TARGET;
        canvas.height = TARGET;
        const ctx = canvas.getContext("2d")!;

        // Center-crop to square
        const size = Math.min(img.width, img.height);
        const sx   = (img.width  - size) / 2;
        const sy   = (img.height - size) / 2;
        ctx.drawImage(img, sx, sy, size, size, 0, 0, TARGET, TARGET);

        const dataUrl = canvas.toDataURL("image/jpeg", 0.85);
        resolve(dataUrl);
      };
      img.src = e.target!.result as string;
    };
    reader.readAsDataURL(file);
  });
}

export default function AvatarUpload({ username, role, currentAvatarUrl, onUpdated, toast }: AvatarUploadProps) {
  const [preview,   setPreview]   = useState<string | null>(null);
  const [dragOver,  setDragOver]  = useState(false);
  const [uploading, setUploading] = useState(false);
  const [removing,  setRemoving]  = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const displayUrl = preview ?? currentAvatarUrl;

  const handleFile = useCallback(async (file: File) => {
    try {
      const dataUrl = await processImage(file);
      setPreview(dataUrl);

      setUploading(true);
      const res = await apiFetch("/users/me/avatar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ avatar_url: dataUrl }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Upload failed");
      }
      const updated = await res.json();
      onUpdated(updated.avatar_url);
      toast("Avatar updated", "success");
    } catch (err: any) {
      setPreview(null);
      toast(err.message || "Failed to upload avatar", "error");
    } finally {
      setUploading(false);
    }
  }, [onUpdated, toast]);

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    e.target.value = ""; // reset so same file can be re-selected
  }

  async function handleRemove() {
    setRemoving(true);
    try {
      const res = await apiFetch("/users/me/avatar", { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to remove avatar");
      setPreview(null);
      onUpdated(null);
      toast("Avatar removed", "success");
    } catch (err: any) {
      toast(err.message || "Failed to remove avatar", "error");
    } finally {
      setRemoving(false);
    }
  }

  return (
    <div className="flex items-center gap-5">
      {/* Current avatar preview */}
      <div className="relative shrink-0">
        <UserAvatar username={username} role={role} avatarUrl={displayUrl} size="lg" />
        {uploading && (
          <div className="absolute inset-0 flex items-center justify-center rounded-full bg-black/40">
            <svg className="h-5 w-5 animate-spin text-white" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          </div>
        )}
      </div>

      {/* Drop zone */}
      <div className="flex-1">
        <div
          onDragOver={e => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={`flex cursor-pointer flex-col items-center justify-center gap-1.5 rounded-2xl border-2 border-dashed px-4 py-5 text-center transition-colors ${
            dragOver
              ? "border-blue-500 bg-blue-50 dark:border-blue-400 dark:bg-blue-500/10"
              : "border-gray-200 bg-gray-50 hover:border-blue-400 hover:bg-blue-50/50 dark:border-gray-700 dark:bg-gray-800/50 dark:hover:border-blue-500 dark:hover:bg-blue-500/5"
          }`}
        >
          <svg className={`h-7 w-7 ${dragOver ? "text-blue-500" : "text-gray-400"}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
          </svg>
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {dragOver ? "Drop to upload" : "Drag & drop or click to choose"}
          </p>
          <p className="text-xs text-gray-400">JPEG, PNG, WebP — max 5 MB · cropped to 200×200</p>
        </div>

        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={handleInputChange}
        />

        {/* Remove button */}
        {(currentAvatarUrl || preview) && (
          <button
            onClick={handleRemove}
            disabled={removing || uploading}
            className="mt-2 text-xs text-red-500 hover:underline disabled:opacity-50 dark:text-red-400"
          >
            {removing ? "Removing…" : "Remove avatar"}
          </button>
        )}
      </div>
    </div>
  );
}
