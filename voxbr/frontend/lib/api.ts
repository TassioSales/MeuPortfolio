import type { Transcription } from "./types";

const API_BASE =
  typeof window !== "undefined"
    ? "/api"
    : process.env.NEXT_PUBLIC_API_URL || "http://backend:8000";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const errorBody = await res.text().catch(() => "Unknown error");
    throw new Error(`HTTP ${res.status}: ${errorBody}`);
  }
  return res.json() as Promise<T>;
}

/**
 * Upload an audio file for transcription.
 * Returns immediately with status='processing'.
 */
export async function uploadAudio(
  file: File,
  language: string = "pt"
): Promise<Transcription> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("language", language);

  const res = await fetch(`${API_BASE}/transcribe`, {
    method: "POST",
    body: formData,
  });

  return handleResponse<Transcription>(res);
}

/**
 * Fetch all transcriptions (newest first).
 */
export async function getTranscriptions(): Promise<Transcription[]> {
  const res = await fetch(`${API_BASE}/transcriptions`, {
    cache: "no-store",
  });
  return handleResponse<Transcription[]>(res);
}

/**
 * Fetch a single transcription by ID.
 */
export async function getTranscription(id: number): Promise<Transcription> {
  const res = await fetch(`${API_BASE}/transcriptions/${id}`, {
    cache: "no-store",
  });
  return handleResponse<Transcription>(res);
}

/**
 * Delete a transcription by ID.
 */
export async function deleteTranscription(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/transcriptions/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const errorBody = await res.text().catch(() => "Unknown error");
    throw new Error(`HTTP ${res.status}: ${errorBody}`);
  }
}

/**
 * Download a transcription export. Opens a browser download.
 */
export async function exportTranscription(
  id: number,
  format: "txt" = "txt"
): Promise<void> {
  const url = `${API_BASE}/transcriptions/${id}/export?format=${format}`;
  const a = document.createElement("a");
  a.href = url;
  a.download = `transcricao_${id}.${format}`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}
