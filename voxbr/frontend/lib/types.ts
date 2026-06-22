export interface Transcription {
  id: number;
  filename: string;
  language: string;
  transcript: string;
  summary: string;
  key_points: string[];
  duration_seconds: number;
  created_at: string;
  status: "processing" | "done" | "error";
}

export type Language = "pt" | "en" | "es";

export const LANGUAGE_LABELS: Record<Language, string> = {
  pt: "Português",
  en: "English",
  es: "Español",
};

export const SUPPORTED_FORMATS = [
  "audio/mpeg",
  "audio/mp4",
  "audio/wav",
  "audio/x-wav",
  "audio/ogg",
  "audio/flac",
  "audio/webm",
  "video/mp4",
  "video/webm",
];

export const SUPPORTED_EXTENSIONS = [
  ".mp3",
  ".mp4",
  ".wav",
  ".m4a",
  ".ogg",
  ".flac",
  ".webm",
];
